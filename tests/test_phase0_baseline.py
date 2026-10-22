"""Pre-migration baseline checks; do not mistake them for target-design acceptance.

These checks intentionally avoid a real terminal and the external kitty binary.
Known defects are documented in STATUS.md and docs/phase0-evidence.md.
"""

from __future__ import annotations

from importlib import import_module, metadata
from io import BytesIO

import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from wskr.protocol.base import ImageProtocol
from wskr.protocol.noop import NoOpProtocol
from wskr.protocol.registry import get_image_protocol


def test_registered_backend_names_point_to_existing_modules():
    entries = {
        entry.name: entry.value
        for entry in metadata.entry_points(group="matplotlib.backend")
        if entry.name.startswith("wskr")
    }
    assert entries["wskr"] == "wskr.render.matplotlib.core"
    assert entries["wskr_kitty"] == "wskr.render.matplotlib.kitty"
    # Registered names are *not* proof that a graphics transport is functional.
    for name in ("wskr", "wskr_kitty"):
        import_module(entries[name])


def test_backend_imports_without_initializing_kitty():
    # Importing the class must be possible even without a terminal executable.
    import wskr.render.matplotlib.kitty as backend

    assert backend._BackendKittyAgg.FigureManager is backend.KittyFigureManager
    assert backend._BackendKittyAgg.FigureCanvas is backend.KittyFigureCanvas


def test_agg_export_png_svg_without_tty_or_kitty():
    fig = Figure(figsize=(4, 2), dpi=110)
    FigureCanvasAgg(fig)
    fig.subplots().plot([0, 1, 2], [3, 2, 5])
    before = tuple(fig.get_size_inches()), fig.dpi
    png = BytesIO()
    svg = BytesIO()
    fig.savefig(png, format="png")
    fig.savefig(svg, format="svg")
    assert png.getvalue().startswith(b"\x89PNG\r\n\x1a\n")
    assert b"<svg" in svg.getvalue()
    assert tuple(fig.get_size_inches()) == before[0]
    assert fig.dpi == pytest.approx(before[1])


def test_registry_default_is_explicit_noop_when_no_protocol_is_selected(monkeypatch):
    monkeypatch.delenv("WSKR_PROTOCOL", raising=False)
    transport = get_image_protocol()
    assert isinstance(transport, NoOpProtocol)
    transport.close()


def test_renderer_preserves_explicit_figure_size():
    """Phase 3: display does not mutate caller-owned geometry."""
    from wskr.render.matplotlib.core import render_figure_to_terminal

    class FakeTransport(ImageProtocol):
        png: bytes | None = None

        def get_window_size_px(self):
            return (240, 120)

        def send_image(self, png_bytes: bytes) -> None:
            self.png = png_bytes

        def init_image(self, png_bytes: bytes) -> int:
            self.png = png_bytes
            return 1

    fig = Figure(figsize=(7, 3), dpi=100)
    canvas = FigureCanvasAgg(fig)
    target = FakeTransport()
    render_figure_to_terminal(canvas, target)
    assert tuple(fig.get_size_inches()) == (7.0, 3.0)
    assert target.png is not None
    assert target.png.startswith(b"\x89PNG")


def test_light_result_is_definitive(monkeypatch):
    """A valid light result cannot be overridden by a later strategy."""
    from wskr.render.matplotlib.utils import detect_dark_mode

    monkeypatch.delenv("WSKR_DARK_MODE", raising=False)

    class Light:
        def detect(self) -> bool:
            return False

    class Dark:
        def detect(self) -> bool:
            return True

    assert detect_dark_mode(strategies=[Light(), Dark()]) is False
