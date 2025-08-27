import matplotlib.pyplot as plt
from matplotlib.backend_bases import FigureManagerBase
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.mpl.base import WskrFigureCanvas, WskrFigureManager


def test_manager_resizes_figure_and_sends_image(dummy_transport):
    fig = plt.figure()
    canvas = FigureCanvasAgg(fig)
    transport = dummy_transport
    manager = WskrFigureManager(canvas=canvas, transport_factory=lambda: transport)

    manager.show()

    assert transport.last_image is not None
    assert transport.last_image.startswith(b"\x89PNG"), "Expected PNG magic header"

    new_w, new_h = fig.get_size_inches()
    assert new_w > 0
    assert new_h > 0


def test_custom_canvas_calls_manager_draw(monkeypatch):
    fig = plt.figure()
    canvas = WskrFigureCanvas(fig)

    dummy_manager = type("MockManager", (), {"show": lambda self: setattr(self, "called", True)})
    dummy_manager_instance = dummy_manager()
    canvas.manager = dummy_manager_instance

    # Simulate interactive mode and an axis
    fig.add_subplot(1, 1, 1)
    monkeypatch.setattr("wskr.mpl.base.is_interactive", lambda: True)

    canvas.draw()

    assert getattr(canvas.manager, "called", False)


def test_draw_reentrancy_is_guarded(monkeypatch):
    fig = plt.figure()
    canvas = WskrFigureCanvas(fig)
    # Avoid auto-draw during subplot creation
    monkeypatch.setattr("wskr.mpl.base.is_interactive", lambda: False)
    fig.add_subplot(1, 1, 1)
    monkeypatch.setattr("wskr.mpl.base.is_interactive", lambda: True)

    class DummyManager(FigureManagerBase):
        def __init__(self, canvas):
            super().__init__(canvas, 1)
            self.calls = 0

        def show(self):
            self.calls += 1
            # sourcery skip: no-conditionals-in-tests
            if self.calls == 1:
                canvas.draw()

    manager = DummyManager(canvas)
    canvas.draw()
    assert manager.calls == 1
