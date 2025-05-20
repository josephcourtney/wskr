from types import MethodType

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cbook import Grouper


def create_share_dict(share_param, ranges):
    """Create a dictionary to manage shared axes for subplots."""
    share_dic = {}
    if share_param:
        if share_param is True:
            for i in range(1, len(ranges)):
                share_dic[i] = 0
        else:
            for group in share_param:
                for subplot_index in group[1:]:
                    share_dic[subplot_index] = group[0]
    return share_dic


def check_for_overlaps(ranges, nrows, ncols):
    """Check for overlapping ranges in subplot configuration."""
    occupancy = np.zeros((nrows, ncols))
    for rng in ranges:
        occupancy[rng[0] : rng[1] + 1, rng[2] : rng[3] + 1] += 1
    if np.max(occupancy) > 1:
        msg = "Provided ranges cause overlapping subplots"
        raise ValueError(msg)
    return occupancy  # Return for potential future use


def initialize_subplots(
    fig, gs, ranges, sharex_dict, sharey_dict, sharez_dict, subplot_kwargs, *args, **kwargs
):
    """Initialize subplots within the figure."""
    ax = np.empty(len(ranges), dtype=object)
    for i, rng in enumerate(ranges):
        # merge base kwargs with any per-subplot overrides
        overrides = subplot_kwargs.get(i, {}) if subplot_kwargs else {}
        kwargs_ = {**kwargs, **overrides}

        share_x = ax[sharex_dict[i]] if i in sharex_dict else None
        share_y = ax[sharey_dict[i]] if i in sharey_dict else None
        if kwargs_.get("projection") == "3d" and i in sharez_dict:
            kwargs_["sharez"] = ax[sharez_dict[i]]
        axis = fig.add_subplot(
            gs[rng[0] : rng[1] + 1, rng[2] : rng[3] + 1],
            *args,
            sharex=share_x,
            sharey=share_y,
            **kwargs_,
        )

        # If this is a 3D subplot, give it get_shared_z_axes()
        if kwargs_.get("projection") == "3d":

            def get_shared_z_axes(self):
                return self._shared_z_axes

            axis.get_shared_z_axes = MethodType(get_shared_z_axes, axis)
        ax[i] = axis

    return ax


def make_plot_grid(
    nrows,
    ncols,
    *args,
    ranges=None,
    sharex=None,
    sharey=None,
    sharez=None,
    gs_kwargs=None,
    subplot_kwargs=None,
    figure_kwargs=None,
    return_gridspec=False,
    **kwargs,
):
    """Create a Matplotlib Figure and list of Axis objects with a given grid layout.

    Parameters
    ----------
    nrows, ncols: int, int
        Number of rows and columns for the subplot grid.

    ranges: list of tuples of ints (optional)
        A list of grid spaces for a given subplot to span. Grid spaces cannot
        be used more than once (no overlapping subplots) but do not have to be
        used at all. The index of each subplot in the returned list is given
        by its location in this list. By default, all grid spaces are separate
        subplots in left-right, top-down order.

    sharex: bool or list of tuples of ints [default: True]
        A list of groups of subplots that should share their x-axis, listed
        by the subplot's index. True causes all subplots to share their x-axis.
        By default, all x-axes are independent.

    sharey: bool or list of tuples of ints [default: True]
        A list of groups of subplots that should share their y-axis, listed
        by the subplot's index. True causes all subplots to share their y-axis.
        By default, all y-axes are independent.

    sharez: bool or list of tuples of ints (optional)
        A list of groups of subplots that should share their z-axis, listed
        by the subplot's index. This is applicable only for 3D subplots.

    gs_kwargs: dict
        Dictionary of keyword arguments to be passed to GridSpec when building
        subplot grid. Notable options are width_ratios and height_ratios.

    subplot_kwargs: dict
        Dictionary of keyword arguments to be passed to fig.add_subplot when
        initializing a new subplot. Note: any unrecognized arguments and
        keyword arguments passed to make_plot_grid are forwarded to
        fig.add_subplot.

    figure_kwargs: dict
        Dictionary of keyword arguments to be passed to plt.figure when
        initializing Figure object.

    return_gridspec: bool [default False]
        Whether to return the GridSpec object used in creation of the figure

    Returns
    -------
    fig: matplotlib.Figure
        Figure containing the subplots.

    ax: list of matplotlib.Axes
        List of Axis objects for each subplot, in the order specified in
        the ranges argument.

    gs: matplotlib.gridspec.GridSpec (optional)
        GridSpec instance used to create the subplots.

    """
    if sharez and sharez is not True:
        subplot_kwargs = subplot_kwargs or {}
        for group in sharez:
            for idx in group:
                subplot_kwargs.setdefault(idx, {}).setdefault("projection", "3d")

    gs_kwargs = gs_kwargs or {}
    figure_kwargs = figure_kwargs or {}

    if ranges is None:
        ranges = [(i, i, j, j) for i in range(nrows) for j in range(ncols)]

    check_for_overlaps(ranges, nrows, ncols)

    fig = plt.figure(**figure_kwargs)
    gs = fig.add_gridspec(nrows, ncols, **gs_kwargs)

    sharex_dict = create_share_dict(sharex, ranges)
    sharey_dict = create_share_dict(sharey, ranges)
    sharez_dict = create_share_dict(sharez, ranges)

    ax = initialize_subplots(
        fig,
        gs,
        ranges,
        sharex_dict,
        sharey_dict,
        sharez_dict,
        subplot_kwargs,
        *args,
        **kwargs,
    )

    # Handle 3D Z-axis sharing
    if sharez and sharez is not True:

        def _get_shared_z_axes(self):
            return self._shared_z_axes

        for group in sharez:
            g = Grouper()
            base_ax = ax[group[0]]
            for idx in group:
                g.join(base_ax, ax[idx])
                axis = ax[idx]
                axis._shared_z_axes = g  # noqa: SLF001
                axis.get_shared_z_axes = MethodType(_get_shared_z_axes, axis)

    return (fig, ax, gs) if return_gridspec else (fig, ax)
