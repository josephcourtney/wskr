import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.mpl.base import BaseTransport, WskrFigureCanvas, WskrFigureManager


class DummyTransport(BaseTransport):
    """A no-op transport for testing."""

    def __init__(self):
        self.last_image: bytes | None = None

    def get_window_size_px(self) -> tuple[int, int]:  # noqa: PLR6301
        # simulate a 800x600 px viewport
        return 800, 600

    def send_image(self, png_bytes: bytes) -> None:
        # capture the bytes so we know show() actually rendered something
        self.last_image = png_bytes

    def init_image(self, png_bytes: bytes) -> int:
        # simulate assigning an image ID
        self.last_image = png_bytes
        return 1


def test_canvas_class_exists_and_manager_property():
    fig = plt.figure()
    canvas = WskrFigureCanvas(fig)

    # It should be our custom canvas...
    assert isinstance(canvas, WskrFigureCanvas)
    # ...and its manager_class should point to our FigureManager
    assert canvas.manager_class is WskrFigureManager


def test_manager_init_and_show_roundtrip():
    fig = plt.figure()
    canvas = FigureCanvasAgg(fig)  # use the standard Agg canvas
    transport = DummyTransport()
    manager = WskrFigureManager(canvas, transport=transport)

    # sanity-check our wiring
    assert manager.canvas is canvas
    assert manager.transport is transport

    # Calling show() should render & hand bytes over to our DummyTransport
    manager.show()
    assert transport.last_image is not None
    assert transport.last_image.startswith(b"\x89PNG\r\n\x1a\n")  # PNG magic
