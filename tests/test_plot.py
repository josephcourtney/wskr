import numpy as np
import pytest

from wskr.plot import make_plot_grid

rng = np.random.default_rng()


def test_make_plot_grid_overlapping_range_raises():
    ranges = [(0, 1, 0, 0), (1, 2, 0, 0)]  # overlaps at row 1, col 0
    with pytest.raises(ValueError, match="overlapping subplots"):
        make_plot_grid(3, 3, ranges=ranges)


@pytest.mark.parametrize(
    ("sharex", "sharey"),
    [
        (True, False),
        (False, True),
        ([(0, 1)], [(1, 2)]),
    ],
)
def test_make_plot_grid_with_shared_axes(sharex, sharey):
    ranges = [(0, 0, 0, 0), (0, 0, 1, 1), (1, 1, 0, 0)]
    _fig, ax = make_plot_grid(3, 3, ranges=ranges, sharex=sharex, sharey=sharey)
    assert len(ax) == 3


def test_subplot_kwargs_and_sharez():
    # Two subplots, the second is 3D and shares its Z-axis with the first
    ranges = [(0, 0, 0, 1), (1, 1, 0, 1)]
    _fig, ax = make_plot_grid(
        2,
        2,
        ranges=ranges,
        sharez=[(0, 1)],
        subplot_kwargs={1: {"projection": "3d"}},
    )
    assert len(ax) == 2
    # First axis is 2D, second is 3D
    assert hasattr(ax[1], "get_zlim")
    # They should share the same z-axis group
    shared = ax[1].get_shared_z_axes()
    assert shared.joined(ax[0], ax[1])


def test_subplot_kwargs_override_default_facecolor():
    # subplot_kwargs should override default facecolor
    ranges = [(0, 0, 0, 0)]
    _fig, ax = make_plot_grid(
        1,
        1,
        ranges=ranges,
        subplot_kwargs={0: {"facecolor": "red"}},
    )
    facecolor = ax[0].get_facecolor()
    # RGBA for red should be (1.0, 0.0, 0.0, 1.0)
    assert pytest.approx(facecolor) == (1.0, 0.0, 0.0, 1.0)
