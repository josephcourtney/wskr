import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from jkit.kitty_backend import FigureCanvasICat, FigureManagerICat


def test_figure_manager_implementation():
    fig = plt.figure()
    canvas = FigureCanvasAgg(fig)
    manager = FigureManagerICat(canvas, 1)
    assert manager is not None


def test_figure_canvas_implementation():
    fig = plt.figure()
    canvas = FigureCanvasICat(fig)
    assert canvas is not None
