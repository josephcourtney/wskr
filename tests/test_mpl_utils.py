import matplotlib.pyplot as plt
import pytest

from wskr.mpl.utils import autosize_figure


def test_autosize_figure_preserves_aspect_ratio():
    fig = plt.figure(figsize=(2, 4))  # 2:1 aspect
    autosize_figure(fig, width_px=800, height_px=400)
    w, h = fig.get_size_inches()
    assert round(h / w, 1) == 2.0


def test_autosize_figure_skips_zero_dimensions():
    # Start with a known figure size
    fig = plt.figure(figsize=(2, 4))
    orig = fig.get_size_inches().copy()

    # Zero width
    autosize_figure(fig, width_px=0, height_px=400)
    assert fig.get_size_inches() == pytest.approx(orig)

    # Zero height
    autosize_figure(fig, width_px=800, height_px=0)
    assert fig.get_size_inches() == pytest.approx(orig)

    # Negative dimension
    autosize_figure(fig, width_px=-100, height_px=200)
    assert fig.get_size_inches() == pytest.approx(orig)
