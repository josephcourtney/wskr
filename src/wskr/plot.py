from types import MethodType

import numpy as np


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
