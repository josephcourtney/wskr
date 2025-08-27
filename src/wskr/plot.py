from types import MethodType

import numpy as np


def _add_share_group(share_dic: dict[int, int], leader: int, followers: list[int], n: int) -> None:
    for f in followers:
        if not 0 <= f < n:
            msg = f"subplot index {f} out of range"
            raise ValueError(msg)
        if f == leader or f in share_dic:
            msg = "duplicate subplot index in share groups"
            raise ValueError(msg)
        share_dic[f] = leader


def create_share_dict(share_param, ranges):
    """Build a mapping describing which subplots share axes.

    Parameters
    ----------
    share_param:
        ``True`` to share all subplots with the first, an iterable of
        iterables ``[(lead, follower1, ...), ...]`` or a mapping
        ``{lead: [followers]}``.
    ranges:
        Sequence describing the subplot layout.  Only the length is used
        to validate indices.

    Returns
    -------
    dict
        Mapping of subplot index to the index it shares with.

    Examples
    --------
    >>> create_share_dict(True, range(3))
    {1: 0, 2: 0}
    >>> create_share_dict([[0, 2], [1, 3]], range(4))
    {2: 0, 3: 1}
    >>> create_share_dict({0: [1, 2]}, range(3))
    {1: 0, 2: 0}
    """
    share_dic: dict[int, int] = {}
    n = len(ranges)
    if not share_param:
        return share_dic

    if share_param is True:
        _add_share_group(share_dic, 0, list(range(1, n)), n)
    elif isinstance(share_param, dict):
        for leader, group in share_param.items():
            _add_share_group(share_dic, int(leader), list(group), n)
    else:
        try:
            for group in share_param:
                leader, *followers = group
                _add_share_group(share_dic, int(leader), list(followers), n)
        except TypeError as e:  # pragma: no cover - invalid iteration type
            msg = "share_param must be True, a dict, or an iterable of groups"
            raise TypeError(msg) from e
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
