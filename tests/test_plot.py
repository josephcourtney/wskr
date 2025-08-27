import pytest
import pytest

import matplotlib.pyplot as plt

from wskr.plot import (
    create_share_dict,
    check_for_overlaps,
    initialize_subplots,
)


def test_create_share_dict_true():
    share = create_share_dict(True, range(3))
    assert share == {1: 0, 2: 0}


def test_create_share_dict_sequence():
    share = create_share_dict([[0, 2], [1, 3]], range(4))
    assert share == {2: 0, 3: 1}


def test_create_share_dict_mapping():
    share = create_share_dict({0: [1, 2]}, range(3))
    assert share == {1: 0, 2: 0}


def test_create_share_dict_invalid_overlap():
    with pytest.raises(ValueError):
        create_share_dict([[0, 1], [2, 1]], range(3))


def test_create_share_dict_bad_type():
    with pytest.raises(TypeError):
        create_share_dict(5, range(2))


def test_check_for_overlaps_detects_and_passes():
    ranges = [(0, 0, 0, 0), (1, 1, 1, 1)]
    occ = check_for_overlaps(ranges, 2, 2)
    assert occ.sum() == 2
    with pytest.raises(ValueError):
        check_for_overlaps([(0, 1, 0, 1), (1, 2, 1, 2)], 3, 3)


def test_initialize_subplots_creates_axes():
    fig = plt.figure()
    gs = fig.add_gridspec(2, 2)
    ranges = [(0, 0, 0, 0), (0, 0, 1, 1)]
    axes = initialize_subplots(fig, gs, ranges, {1: 0}, {1: 0}, {}, None)
    assert len(axes) == 2


def test_initialize_subplots_shared_z():
    fig = plt.figure()
    gs = fig.add_gridspec(1, 2)
    ranges = [(0, 0, 0, 0), (0, 0, 1, 1)]
    kwargs = {0: {"projection": "3d"}, 1: {"projection": "3d"}}
    axes = initialize_subplots(fig, gs, ranges, {}, {}, {1: 0}, kwargs)
    assert hasattr(axes[1], "get_shared_z_axes")
