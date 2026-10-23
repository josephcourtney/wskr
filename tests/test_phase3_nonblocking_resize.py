"""Phase 3 opportunistic nonblocking viewport refresh via Matplotlib event pumps."""

from __future__ import annotations

from io import BytesIO

import pytest
from matplotlib.figure import Figure
from PIL import Image

from wskr.protocol.base import ImageProtocol
from wskr.render.matplotlib import core
from wskr.terminal.profile import Geometry

pytestmark = pytest.mark.medium


class _Transport(ImageProtocol):
    def __init__(self, current: list[Geometry | None]) -> None:
        self.current = current
        self.frames: list[bytes] = []
        self.closed = False

    def get_window_size_px(self) -> tuple[int, int]:
        geometry = self.current[0]
        return (geometry.width_px, geometry.height_px) if geometry is not None else (0, 0)

    def send_image(self, png_bytes: bytes) -> None:
        assert not self.closed
        self.frames.append(png_bytes)

    def init_image(self, png_bytes: bytes) -> int:
        self.send_image(png_bytes)
        return len(self.frames)

    def close(self) -> None:
        self.closed = True


def _setup(monkeypatch):
    current: list[Geometry | None] = [Geometry(30, 80, 800, 600)]
    clock = [0.0]
    monkeypatch.setattr(core, "read_geometry", lambda: current[0])
    monkeypatch.setattr(core, "monotonic", lambda: clock[0])
    monkeypatch.setattr(core, "is_interactive", lambda: False)
    transport = _Transport(current)
    figure = Figure(figsize=(4, 3), dpi=100)
    figure.subplots().plot([0, 1], [1, 2])
    canvas = core.WskrFigureCanvas(figure)
    manager = core.WskrFigureManager(canvas, 8110, transport_factory=lambda: transport)
    return current, clock, figure, canvas, manager, transport


def _pixels(data: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as img:
        return img.size


def test_nonblocking_flush_debounces_and_rescales_without_mutating_source(monkeypatch) -> None:
    monkeypatch.setenv("WSKR_FIT", "contain")
    current, clock, figure, canvas, manager, transport = _setup(monkeypatch)
    size = tuple(figure.get_size_inches()), figure.dpi
    original = BytesIO()
    figure.savefig(original, format="png")
    try:
        manager.show()
        assert len(transport.frames) == 1
        assert _pixels(transport.frames[0]) == (400, 300)

        current[0] = Geometry(20, 50, 200, 120)
        canvas.flush_events()  # first observation starts debounce
        assert len(transport.frames) == 1
        clock[0] = 0.19
        canvas.flush_events()
        assert len(transport.frames) == 1
        clock[0] = 0.21
        canvas.flush_events()
        assert len(transport.frames) == 2
        assert _pixels(transport.frames[-1]) == (160, 120)
        canvas.flush_events()
        assert len(transport.frames) == 2
        assert (tuple(figure.get_size_inches()), figure.dpi) == size
        saved = BytesIO()
        figure.savefig(saved, format="png")
        assert saved.getvalue() == original.getvalue()
    finally:
        manager.destroy()


def test_resize_requires_observable_stable_geometry(monkeypatch) -> None:
    monkeypatch.setenv("WSKR_FIT", "contain")
    current, clock, _, canvas, manager, transport = _setup(monkeypatch)
    try:
        manager.show()
        current[0] = Geometry(25, 65, 350, 250)
        canvas.flush_events()
        clock[0] = 0.3
        current[0] = None
        canvas.flush_events()
        current[0] = Geometry(25, 65, 350, 250)
        canvas.flush_events()  # cannot reuse stale pending observation
        assert len(transport.frames) == 1
        clock[0] = 0.51
        canvas.flush_events()
        assert len(transport.frames) == 2
        current[0] = Geometry(30, 80, 800, 600)
        canvas.flush_events()
        clock[0] = 0.8
        canvas.flush_events()
        assert len(transport.frames) == 3
    finally:
        manager.destroy()


def test_flush_does_not_render_unshown_unfitted_or_closed_figures(monkeypatch) -> None:
    monkeypatch.delenv("WSKR_FIT", raising=False)
    current, clock, _, canvas, manager, transport = _setup(monkeypatch)
    try:
        canvas.flush_events()
        assert transport.frames == []
        manager.show()
        assert len(transport.frames) == 1
        current[0] = Geometry(20, 50, 200, 120)
        clock[0] = 1.0
        canvas.flush_events()
        assert len(transport.frames) == 1
        monkeypatch.setenv("WSKR_FIT", "contain")
        canvas.flush_events()  # no fitted display has been recorded
        assert len(transport.frames) == 1
        manager.show()
        assert len(transport.frames) == 2
    finally:
        manager.destroy()
    current[0] = Geometry(25, 60, 400, 250)
    clock[0] = 2.0
    canvas.flush_events()
    clock[0] = 2.5
    canvas.flush_events()
    assert len(transport.frames) == 2


def test_interactive_flush_uses_guarded_draw_idle_once(monkeypatch) -> None:
    monkeypatch.setenv("WSKR_FIT", "contain")
    current, clock, _, canvas, manager, transport = _setup(monkeypatch)
    try:
        manager.show()
        monkeypatch.setattr(core, "is_interactive", lambda: True)
        current[0] = Geometry(20, 50, 200, 120)
        canvas.flush_events()
        clock[0] = 0.25
        canvas.flush_events()
        assert len(transport.frames) == 2  # not two uploads via re-entrant show
        assert _pixels(transport.frames[-1]) == (160, 120)
    finally:
        manager.destroy()


def test_no_input_or_signal_ownership_during_event_pump(monkeypatch) -> None:
    monkeypatch.setenv("WSKR_FIT", "contain")
    current, clock, _, canvas, manager, transport = _setup(monkeypatch)
    monkeypatch.setattr(core, "_owns_foreground_terminal_input", lambda: pytest.fail("input claimed"))
    monkeypatch.setattr("builtins.input", lambda *_args: pytest.fail("input consumed"))
    try:
        manager.show()
        current[0] = Geometry(20, 50, 200, 120)
        canvas.flush_events()
        clock[0] = 0.25
        canvas.flush_events()
        assert len(transport.frames) == 2
    finally:
        manager.destroy()
