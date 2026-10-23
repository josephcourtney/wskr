"""Viewport-contained multi-figure composition and scoped Kitty placement."""

from __future__ import annotations

import os
from io import BytesIO

import pytest
from matplotlib.backend_bases import FigureManagerBase
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from wskr.protocol.base import ImageProtocol
from wskr.render.matplotlib import core
from wskr.render.matplotlib.sheet import contact_sheet
from wskr.terminal.profile import Geometry

pytestmark = pytest.mark.medium


def _canvas(color: str) -> FigureCanvasAgg:
    return FigureCanvasAgg(Figure(figsize=(3, 2), dpi=90, facecolor=color))


def _matches_color(red: int, green: int, blue: int, color: str) -> bool:
    if color == "red":
        return red > 220 and green < 70
    return blue > 220 and red < 70


def _color_count(image: Image.Image, color: str, *, start: int, end: int) -> int:
    pixels = image.convert("RGB")
    raw = pixels.tobytes()
    selected = 0
    for x in range(start, end, 3):
        for y in range(0, pixels.height, 3):
            offset = (y * pixels.width + x) * 3
            red, green, blue = raw[offset : offset + 3]
            if _matches_color(red, green, blue, color):
                selected += 1
    return selected


def test_contact_sheet_preserves_two_distinct_figures_without_overlap() -> None:
    first, second = _canvas("red"), _canvas("blue")
    before = tuple(first.figure.get_size_inches()), first.figure.dpi
    saved = BytesIO()
    first.figure.savefig(saved, format="png")

    png = contact_sheet([first, second], Geometry(25, 80, 800, 480))
    with Image.open(BytesIO(png)) as rendered:
        assert rendered.size == (800, 441)
        assert _color_count(rendered, "red", start=0, end=400) > 300
        assert _color_count(rendered, "blue", start=400, end=800) > 300
        assert _color_count(rendered, "blue", start=0, end=400) == 0
        assert _color_count(rendered, "red", start=400, end=800) == 0

    assert tuple(first.figure.get_size_inches()) == before[0]
    assert first.figure.dpi == before[1]
    after = BytesIO()
    first.figure.savefig(after, format="png")
    assert after.getvalue() == saved.getvalue()


def test_tall_terminal_stacks_figures_vertically() -> None:
    png = contact_sheet([_canvas("red"), _canvas("blue")], Geometry(40, 50, 480, 800))
    with Image.open(BytesIO(png)) as rendered:
        assert rendered.size == (480, 760)
        left_half = rendered.crop((0, 0, 480, 380))
        right_half = rendered.crop((0, 380, 480, 760))
        assert _color_count(left_half, "red", start=0, end=480) > 250
        assert _color_count(right_half, "blue", start=0, end=480) > 250


@pytest.mark.parametrize("geometry", [Geometry(3, 80, 800, 400), Geometry(30, 80), Geometry(25, 80, 5, 5)])
def test_contact_sheet_rejects_unknown_or_insufficient_terminal_space(geometry) -> None:
    with pytest.raises(ValueError, match=r"terminal|Contact sheet"):
        contact_sheet([_canvas("red"), _canvas("blue")], geometry)


class _CapturedTransport(ImageProtocol):
    def __init__(self) -> None:
        self.frames: list[bytes] = []
        self.closed = False

    def get_window_size_px(self) -> tuple[int, int]:
        return 800, 480

    def send_image(self, png_bytes: bytes) -> None:
        self.frames.append(png_bytes)

    def init_image(self, png_bytes: bytes) -> int:
        self.frames.append(png_bytes)
        return len(self.frames)

    def close(self) -> None:
        self.closed = True


def test_blocking_managers_send_one_image_and_move_prompt_to_last_row(monkeypatch) -> None:
    monkeypatch.setenv("WSKR_FIT", "contain")
    monkeypatch.setattr(core, "is_interactive", lambda: False)
    master, slave = os.openpty()

    class Output:
        def fileno(self) -> int:
            return slave

        def flush(self) -> None:
            pass

    one, two = _CapturedTransport(), _CapturedTransport()
    first = core.WskrFigureManager(_canvas("red"), 751, transport_factory=lambda: one)
    second = core.WskrFigureManager(_canvas("blue"), 752, transport_factory=lambda: two)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(core.sys, "stdout", Output())
            core._show_blocking_managers([first, second], Geometry(25, 80, 800, 480))
        assert len(one.frames) == 1
        assert two.frames == []
        assert os.read(master, 128) == b"\x1b[25;1H"
    finally:
        first.destroy()
        second.destroy()
        os.close(master)
        os.close(slave)
    assert one.closed
    assert two.closed


def test_unfitted_blocking_session_uses_individual_manager_show(monkeypatch) -> None:
    monkeypatch.delenv("WSKR_FIT", raising=False)
    calls: list[int] = []

    class Manager(FigureManagerBase):
        def show(self) -> None:
            calls.append(int(self.num))

    core._show_blocking_managers([Manager(_canvas("red"), 1), Manager(_canvas("blue"), 2)], Geometry(25, 80, 800, 480))
    assert calls == [1, 2]
