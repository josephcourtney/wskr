"""Phase 3 opt-in viewport containment without Matplotlib figure mutation."""

from __future__ import annotations

from io import BytesIO

import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from wskr.core.errors import TransportUnavailableError
from wskr.protocol.base import ImageProtocol
from wskr.render.matplotlib.core import render_figure_to_terminal

pytestmark = pytest.mark.medium


class ViewportTransport(ImageProtocol):
    def __init__(self, viewport: tuple[int, int]) -> None:
        self.viewport = viewport
        self.frames: list[bytes] = []
        self.probes = 0
        self.failure = False

    def get_window_size_px(self) -> tuple[int, int]:
        self.probes += 1
        if self.failure:
            msg = "pixels unavailable"
            raise TransportUnavailableError(msg)
        return self.viewport

    def send_image(self, png_bytes: bytes) -> None:
        self.frames.append(png_bytes)

    def init_image(self, png_bytes: bytes) -> int:
        self.frames.append(png_bytes)
        return len(self.frames)


def _image_size(png: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(png)) as image:
        return image.size


def test_fit_uses_current_pixel_viewport_on_each_display(monkeypatch) -> None:
    monkeypatch.delenv("WSKR_SCALE", raising=False)
    monkeypatch.setenv("WSKR_FIT", "contain")
    fig = Figure(figsize=(8, 4), dpi=100)
    canvas = FigureCanvasAgg(fig)
    fig.subplots().plot([0, 1, 2], [2, 3, 1])
    before = BytesIO()
    fig.savefig(before, format="png")
    original = tuple(fig.get_size_inches()), fig.dpi

    transport = ViewportTransport((1200, 700))
    expected = (
        ((1200, 700), (800, 400)),
        ((400, 500), (400, 200)),
        ((900, 150), (300, 150)),
        ((320, 100), (200, 100)),
        ((1600, 1200), (800, 400)),
    )
    for viewport, output in expected:
        transport.viewport = viewport
        render_figure_to_terminal(canvas, transport)
        assert _image_size(transport.frames[-1]) == output
        assert tuple(fig.get_size_inches()) == original[0]
        assert fig.dpi == original[1]

    assert transport.probes == len(expected)
    after = BytesIO()
    fig.savefig(after, format="png")
    assert after.getvalue() == before.getvalue()


def test_fitting_default_off_requires_no_geometry_probe(monkeypatch) -> None:
    monkeypatch.delenv("WSKR_SCALE", raising=False)
    monkeypatch.delenv("WSKR_FIT", raising=False)
    transport = ViewportTransport((100, 100))
    fig = Figure(figsize=(4, 2), dpi=100)
    render_figure_to_terminal(FigureCanvasAgg(fig), transport)
    assert transport.probes == 0
    assert _image_size(transport.frames[-1]) == (400, 200)


@pytest.mark.parametrize("viewport", [(0, 0), (0, 100), (-1, 300)])
def test_fit_refuses_unmeasured_or_invalid_pixels(monkeypatch, viewport) -> None:
    monkeypatch.setenv("WSKR_FIT", "contain")
    monkeypatch.delenv("WSKR_SCALE", raising=False)
    transport = ViewportTransport(viewport)
    render_figure_to_terminal(FigureCanvasAgg(Figure(figsize=(4, 2), dpi=100)), transport)
    assert _image_size(transport.frames[-1]) == (400, 200)
    assert transport.probes == 1


def test_fit_falls_back_when_transport_pixels_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("WSKR_FIT", "contain")
    monkeypatch.delenv("WSKR_SCALE", raising=False)
    transport = ViewportTransport((300, 200))
    transport.failure = True
    render_figure_to_terminal(FigureCanvasAgg(Figure(figsize=(4, 2), dpi=100)), transport)
    assert _image_size(transport.frames[-1]) == (400, 200)


def test_explicit_scale_composes_with_containment(monkeypatch) -> None:
    monkeypatch.setenv("WSKR_FIT", "contain")
    monkeypatch.setenv("WSKR_SCALE", "2")
    fig = Figure(figsize=(4, 2), dpi=100)
    canvas = FigureCanvasAgg(fig)
    transport = ViewportTransport((500, 500))
    render_figure_to_terminal(canvas, transport)
    assert _image_size(transport.frames[-1]) == (500, 250)
    assert tuple(fig.get_size_inches()) == (4, 2)
    assert fig.dpi == 100


def test_invalid_scale_defaults_to_one_then_applies_fit(monkeypatch) -> None:
    monkeypatch.setenv("WSKR_FIT", "contain")
    monkeypatch.setenv("WSKR_SCALE", "nan")
    transport = ViewportTransport((200, 160))
    render_figure_to_terminal(FigureCanvasAgg(Figure(figsize=(4, 2), dpi=100)), transport)
    assert _image_size(transport.frames[-1]) == (200, 100)
