import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.render.matplotlib.core import (
    WskrFigureCanvas,
    WskrFigureManager,
    _BackendTermAgg,
    render_figure_to_terminal,
)
from wskr.terminal.core.base import ImageTransport


def test_canvas_class_exists_and_manager_property():
    fig = plt.figure()
    canvas = WskrFigureCanvas(fig)

    # It should be our custom canvas...
    assert isinstance(canvas, WskrFigureCanvas)
    # ...and its manager_class should point to our FigureManager
    assert canvas.manager_class is WskrFigureManager


def test_manager_init_and_show_roundtrip(dummy_transport):
    fig = plt.figure()
    canvas = FigureCanvasAgg(fig)  # use the standard Agg canvas
    transport = dummy_transport
    manager = WskrFigureManager(canvas, transport_factory=lambda: transport)

    # sanity-check our wiring
    assert manager.canvas is canvas
    assert manager.transport is transport

    # Calling show() should render & hand bytes over to our DummyTransport
    manager.show()
    assert transport.last_image is not None
    # PNG magic
    assert transport.last_image.startswith(b"\x89PNG\r\n\x1a\n")


class DummyTransport(ImageTransport):
    def __init__(self):
        self.last_image = None
        self.size_calls = []

    def get_window_size_px(self):
        self.size_calls.append(True)
        return (20, 40)

    def send_image(self, png_bytes: bytes) -> None:
        self.last_image = png_bytes

    def init_image(self, png_bytes: bytes) -> int:
        return 0


def test_render_with_invalid_scale_defaults_to_1(monkeypatch):
    monkeypatch.setenv("WSKR_SCALE", "not-a-number")
    observed = {}

    def fake_autosize(fig, w, h):
        observed["dims"] = (w, h)

    monkeypatch.setattr("wskr.render.matplotlib.core.autosize_figure", fake_autosize)

    fig = plt.figure()
    canvas = FigureCanvasAgg(fig)
    transport = DummyTransport()
    render_figure_to_terminal(canvas, transport)

    # Should use the unscaled 20x40
    assert observed["dims"] == (20, 40)
    assert transport.last_image.startswith(b"\x89PNG")  # type: ignore[possibly-unbound-attribute]


def test_terminalbackend_draw_if_interactive_and_show(monkeypatch):
    called = {}

    class FakeManager:
        canvas = type("C", (), {"figure": type("F", (), {"get_axes": lambda self: [1]})()})

        def show(self, *args, **kwargs):
            called["show"] = True

    monkeypatch.setattr("wskr.render.matplotlib.core.Gcf.get_active", FakeManager)

    # When not interactive, draw_if_interactive is a no-op
    monkeypatch.setattr("matplotlib.is_interactive", lambda: False)
    _BackendTermAgg.draw_if_interactive()
    assert "show" not in called

    # When interactive, it should call show()
    monkeypatch.setattr("matplotlib.is_interactive", lambda: True)
    _BackendTermAgg.draw_if_interactive()
    assert called["show"]
