"""Phase 3 figure ownership and deterministic terminal-geometry regression tests.

A Kitty window may be reshaped by yabai between displays. That observation
alone must not be treated as permission to mutate Matplotlib's Figure.
"""

from __future__ import annotations

from io import BytesIO

import matplotlib as mpl
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from wskr.protocol.kitty_native import NativeKittyTransport
from wskr.render.matplotlib import core

pytestmark = pytest.mark.medium


class CapturedTransport:
    def __init__(self) -> None:
        self.viewport = (1800, 1200)
        self.frames: list[bytes] = []
        self.closed = 0

    def get_window_size_px(self) -> tuple[int, int]:
        return self.viewport

    def send_image(self, png_bytes: bytes) -> None:
        self.frames.append(png_bytes)

    def close(self) -> None:
        self.closed += 1


def test_display_preserves_explicit_size_dpi_and_export_across_window_changes() -> None:
    fig = Figure(figsize=(6, 6), dpi=300, facecolor="none")
    canvas = FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.plot([0, 1, 2], [2, 3, 1], color="purple")
    ax.set_title("Caller-owned style", color="black")
    source = BytesIO()
    fig.savefig(source, format="png", transparent=True)
    original = source.getvalue()
    start = tuple(fig.get_size_inches()), fig.dpi, fig.get_facecolor()

    transport = CapturedTransport()
    for viewport in ((1800, 1200), (1664, 952), (720, 460), (1600, 1080)):
        transport.viewport = viewport
        core.render_figure_to_terminal(canvas, transport)
        assert tuple(fig.get_size_inches()) == start[0]
        assert fig.dpi == start[1]
        assert fig.get_facecolor() == start[2]
        with Image.open(BytesIO(transport.frames[-1])) as image:
            assert image.size == (1800, 1800)

    saved = BytesIO()
    fig.savefig(saved, format="png", transparent=True)
    assert saved.getvalue() == original
    svg = BytesIO()
    fig.savefig(svg, format="svg")
    assert b"<svg" in svg.getvalue()


def test_backend_owned_creation_size_is_not_overwritten_during_display(monkeypatch) -> None:
    from wskr.terminal.profile import Geometry, probe_profile

    monkeypatch.setattr(core, "probe_profile", lambda: probe_profile(geometry=Geometry(30, 100, 1000, 600)))
    monkeypatch.setitem(mpl.rcParams, "figure.figsize", mpl.rcParamsDefault["figure.figsize"])
    manager = core._BackendTermAgg.new_figure_manager(3901)
    transport = CapturedTransport()
    try:
        figure = manager.canvas.figure
        creation = tuple(figure.get_size_inches()), figure.dpi
        core.render_figure_to_terminal(manager.canvas, transport)
        assert tuple(figure.get_size_inches()) == creation[0]
        assert figure.dpi == creation[1]
    finally:
        manager.destroy()


def test_backend_show_visits_all_figures_without_destroying_them(monkeypatch) -> None:
    calls: list[str] = []

    class Manager:
        def __init__(self, tag: str) -> None:
            self.tag = tag

        def show(self, **_kwargs) -> None:
            calls.append(self.tag)

    a, b = Manager("A"), Manager("B")
    monkeypatch.setattr(core.Gcf, "get_all_fig_managers", lambda: [a, b])

    def forbidden_destroy() -> None:
        pytest.fail("show() must not destroy registered figures")

    monkeypatch.setattr(core.Gcf, "destroy_all", forbidden_destroy)
    core._BackendTermAgg.show(block=False)
    core._BackendTermAgg.show(block=False)
    assert calls == ["A", "B", "A", "B"]


def test_manager_destruction_releases_only_owned_transport() -> None:
    first, second = CapturedTransport(), CapturedTransport()
    fig_a, fig_b = Figure(), Figure()
    a = core.WskrFigureManager(FigureCanvasAgg(fig_a), 3902, transport_factory=lambda: first)
    b = core.WskrFigureManager(FigureCanvasAgg(fig_b), 3903, transport_factory=lambda: second)
    a.show()
    b.show()
    a.destroy()
    assert first.closed == 1
    assert second.closed == 0
    b.show()
    b.destroy()
    assert second.closed == 1


def test_native_display_replaces_previous_owned_image_without_global_delete(monkeypatch) -> None:
    ids = iter((100, 201, 101, 202))
    monkeypatch.setattr("wskr.protocol.kitty_native.secrets.randbelow", lambda _bound: next(ids) - 1)
    packets: list[bytes] = []
    transport = NativeKittyTransport(writer=packets.extend)
    # Valid PNG magic is sufficient for byte-protocol framing.
    png = b"\x89PNG\r\n\x1a\n" + b"binary payload"
    transport.send_image(png)
    transport.send_image(png)
    assert set(transport.manager._images) == {101}
    assert any(b"a=d,d=I,i=100" in packet for packet in packets)
    assert not any(b"a=d,d=a" in packet for packet in packets)
    transport.close()
    assert transport.manager._images == {}
