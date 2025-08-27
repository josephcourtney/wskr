import matplotlib.pyplot as plt
import pytest

from wskr.mpl.size import TerminalMetrics, autosize_figure, compute_terminal_figure_size


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


def test_compute_terminal_figure_size_uses_metrics():
    metrics = TerminalMetrics(w_px=10, h_px=20, n_col=100, n_row=50, dpi=100, zoom=2.0)
    w_in, h_in = compute_terminal_figure_size(50, 25, metrics)
    assert w_in == pytest.approx((50 * 10) / (100 * 100 * 2.0))
    assert h_in == pytest.approx((25 * 20) / (50 * 100 * 2.0))
