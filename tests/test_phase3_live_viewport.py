"""Foreground-owned live viewport: isolation, debounce and scoped cleanup."""

from __future__ import annotations

import os
from io import BytesIO

import matplotlib as mpl
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from wskr.protocol.base import ImageProtocol
from wskr.render.matplotlib import core, live
from wskr.render.matplotlib.figure import TerminalFigure
from wskr.terminal.profile import Geometry, probe_profile

pytestmark = pytest.mark.medium


class _Transport(ImageProtocol):
    def __init__(self, geometry: list[Geometry]) -> None:
        self.geometry = geometry
        self.frames: list[bytes] = []
        self.closed = 0

    def get_window_size_px(self) -> tuple[int, int]:
        current = self.geometry[0]
        return current.width_px, current.height_px

    def send_image(self, png_bytes: bytes) -> None:
        if self.closed:
            msg = "sent after close"
            raise AssertionError(msg)
        self.frames.append(png_bytes)

    def init_image(self, png_bytes: bytes) -> int:
        self.send_image(png_bytes)
        return len(self.frames)

    def close(self) -> None:
        self.closed += 1


def _figure() -> Figure:
    fig = Figure(figsize=(9, 2), dpi=100)
    FigureCanvasAgg(fig)
    fig.subplots().bar([1, 2], [3, 4], color=("red", "blue"))
    return fig


def _size(data: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as img:
        return img.size


def _session(monkeypatch: pytest.MonkeyPatch):
    geometry = [Geometry(40, 100, 1000, 700)]
    transport = _Transport(geometry)
    writes: list[bytes] = []

    class Output:
        def flush(self) -> None:
            pass

        def fileno(self) -> int:
            return 12

    monkeypatch.setattr(core, "_owns_foreground_terminal_input", lambda: True)
    monkeypatch.setattr(core.sys, "stdout", Output())
    monkeypatch.setattr(os, "write", lambda _fd, data: writes.append(data) or len(data))
    monkeypatch.setattr(core, "read_geometry", lambda: geometry[0])
    monkeypatch.setattr(live, "read_geometry", lambda: geometry[0])
    monkeypatch.setenv("WSKR_FIT", "contain")
    return geometry, transport, writes


def test_live_owned_session_refreshes_at_top_and_restores_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    geometry, transport, writes = _session(monkeypatch)
    fig = _figure()
    original = tuple(fig.get_size_inches()), fig.dpi
    try:
        with live.owned_viewport(fig, transport_factory=lambda: transport) as view:
            assert writes == [b"\x1b[?1049h", b"\x1b[H\x1b[2J"]
            assert [_size(png) for png in transport.frames] == [(900, 200)]
            geometry[0] = Geometry(20, 50, 500, 340)
            view.refresh()
            assert [_size(png) for png in transport.frames] == [(900, 200), (500, 111)]
            assert (tuple(fig.get_size_inches()), fig.dpi) == original
            assert not view.poll_resize()
        assert transport.closed == 1
        assert writes[-1] == b"\x1b[?1049l"
        with pytest.raises(RuntimeError, match="ended"):
            view.refresh()
    finally:
        assert not core._BLOCKING_RENDER.get()


def test_resize_poll_waits_for_measured_stability(monkeypatch: pytest.MonkeyPatch) -> None:
    geometry, transport, _writes = _session(monkeypatch)
    time = [0.0]
    monkeypatch.setattr(live, "monotonic", lambda: time[0])
    with live.owned_viewport(_figure(), transport_factory=lambda: transport) as view:
        geometry[0] = Geometry(24, 60, 600, 420)
        assert not view.poll_resize()
        time[0] = 0.1
        assert not view.poll_resize()
        assert len(transport.frames) == 1
        time[0] = 0.21
        assert view.poll_resize()
        assert len(transport.frames) == 2
        assert _size(transport.frames[-1]) == (600, 133)
        assert not view.poll_resize()


def test_owned_live_rejects_unowned_or_unfitted_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    _geometry, transport, writes = _session(monkeypatch)
    monkeypatch.setattr(core, "_owns_foreground_terminal_input", lambda: False)
    with (
        pytest.raises(RuntimeError, match="foreground"),
        live.owned_viewport(_figure(), transport_factory=lambda: transport),
    ):
        pytest.fail("unowned session was entered")
    monkeypatch.setattr(core, "_owns_foreground_terminal_input", lambda: True)
    monkeypatch.delenv("WSKR_FIT")
    with (
        pytest.raises(RuntimeError, match="WSKR_FIT"),
        live.owned_viewport(_figure(), transport_factory=lambda: transport),
    ):
        pytest.fail("unfitted session was entered")
    assert not writes
    assert transport.closed == 0


def test_nested_owned_session_is_rejected_without_clobbering_screen(monkeypatch: pytest.MonkeyPatch) -> None:
    _geometry, transport, writes = _session(monkeypatch)

    def attempt_nested_owner() -> None:
        with (
            pytest.raises(RuntimeError, match="already owns"),
            live.owned_viewport(_figure(), transport_factory=lambda: pytest.fail("nested created transport")),
        ):
            pytest.fail("nested session entered")

    with live.owned_viewport(_figure(), transport_factory=lambda: transport):
        attempt_nested_owner()
    assert writes.count(b"\x1b[?1049h") == 1
    assert writes.count(b"\x1b[?1049l") == 1


@pytest.mark.parametrize("exc", [ValueError, KeyboardInterrupt])
def test_failure_restores_alt_screen_and_disposes_scoped_transport(monkeypatch: pytest.MonkeyPatch, exc) -> None:
    _geometry, transport, writes = _session(monkeypatch)
    with pytest.raises(exc), live.owned_viewport(_figure(), transport_factory=lambda: transport):
        raise exc
    assert transport.closed == 1
    assert writes[-1] == b"\x1b[?1049l"
    assert not core._BLOCKING_RENDER.get()


def test_screen_entry_failure_still_closes_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    _geometry, transport, _writes = _session(monkeypatch)

    def fail(_fd: int, _data: bytes) -> int:
        msg = "broken terminal"
        raise OSError(msg)

    monkeypatch.setattr(os, "write", fail)
    with (
        pytest.raises(OSError, match="broken terminal"),
        live.owned_viewport(_figure(), transport_factory=lambda: transport),
    ):
        pytest.fail("no screen acquired")
    assert transport.closed == 1
    assert not core._BLOCKING_RENDER.get()


def test_owned_render_suppresses_normal_interactive_manager_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    _geometry, transport, _writes = _session(monkeypatch)
    fig = Figure(figsize=(3, 2), dpi=100)
    canvas = core.WskrFigureCanvas(fig)
    fig.subplots().plot([0, 1], [1, 0])

    class Manager:
        def show(self) -> None:
            pytest.fail("regular pyplot manager leaked a history placement")

        _nonblocking_resize = object()

    monkeypatch.setattr(core, "is_interactive", lambda: True)
    monkeypatch.setattr(canvas, "manager", Manager(), raising=False)
    with live.owned_viewport(fig, transport_factory=lambda: transport) as view:
        view.refresh()
        canvas.flush_events()
    assert len(transport.frames) == 2
    assert transport.closed == 1


def test_live_session_does_not_claim_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    _geometry, transport, _writes = _session(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda *_args: pytest.fail("live viewport read stdin"))
    with live.owned_viewport(_figure(), transport_factory=lambda: transport) as view:
        view.poll_resize()
        view.refresh()
    assert len(transport.frames) == 2


def test_owned_images_are_closed_before_alternate_screen_restores(monkeypatch: pytest.MonkeyPatch) -> None:
    _geometry, transport, writes = _session(monkeypatch)
    original_close = transport.close

    def close_inside_screen() -> None:
        assert writes[-1] != b"\x1b[?1049l", "Kitty placements deleted after restoring shell"
        original_close()

    monkeypatch.setattr(transport, "close", close_inside_screen)
    with live.owned_viewport(_figure(), transport_factory=lambda: transport):
        pass
    assert transport.closed == 1
    assert writes[-1] == b"\x1b[?1049l"


def test_initial_render_failure_restores_screen_and_releases_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    _geometry, transport, writes = _session(monkeypatch)

    def fail_send(_png: bytes) -> None:
        msg = "broken PNG upload"
        raise OSError(msg)

    monkeypatch.setattr(transport, "send_image", fail_send)
    with (
        pytest.raises(OSError, match="broken PNG upload"),
        live.owned_viewport(_figure(), transport_factory=lambda: transport),
    ):
        pytest.fail("entry rendered despite failed upload")
    assert transport.closed == 1
    assert writes[-1] == b"\x1b[?1049l"


def _theme(background: str, foreground: str):
    def query(request: bytes) -> bytes:
        code = 10 if request.startswith(b"\x1b]10;") else 11
        color = foreground if code == 10 else background
        return f"\x1b]{code};rgb:{color}/{color}/{color}\x07".encode()

    return probe_profile(geometry=Geometry(30, 100, 1000, 600), color_query=query)


def test_owned_live_theme_updates_only_backend_owned_surfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit measured theme change cannot recolor user plot/data art."""
    _geometry, transport, _writes = _session(monkeypatch)
    old_style = {
        "axes.facecolor": "#000000",
        "axes.labelcolor": "#ffffff",
        "text.color": "#ffffff",
    }
    with mpl.rc_context():
        mpl.rcdefaults()
        fig = TerminalFigure(
            figsize=(3, 2),
            dpi=100,
            facecolor="#000000",
            _wskr_defaults=old_style,
            _wskr_bg_owned=True,
        )
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        line = ax.plot([0, 1], [1, 2], color="orange")[0]
        ax.set_title("automatic")
        ax.set_xlabel("automatic")
        ax.set_ylabel("explicit", color="cyan")
        original_size = tuple(fig.get_size_inches()), fig.dpi
        with live.owned_viewport(fig, transport_factory=lambda: transport) as view:
            assert view.refresh_theme(_theme("ffff", "0000"))
            assert len(transport.frames) == 2
            assert fig.get_facecolor() == mpl.colors.to_rgba("#ffffff")
            assert ax.get_facecolor() == mpl.colors.to_rgba("#ffffff")
            assert ax.title.get_color() == "#000000"
            assert ax.xaxis.label.get_color() == "#000000"
            assert ax.yaxis.label.get_color() == "cyan"
            assert line.get_color() == "orange"
            assert (tuple(fig.get_size_inches()), fig.dpi) == original_size
            assert not view.refresh_theme(_theme("ffff", "0000"))
            assert not view.refresh_theme(probe_profile(geometry=Geometry(30, 100, 1000, 600)))
            assert len(transport.frames) == 2
            fig.set_facecolor("#123456")  # Explicit late caller edit owns this.
            ax.set_facecolor("#334455")
            assert view.refresh_theme(_theme("0000", "ffff"))
            assert fig.get_facecolor() == mpl.colors.to_rgba("#123456")
            assert ax.get_facecolor() == mpl.colors.to_rgba("#334455")
            assert ax.yaxis.label.get_color() == "cyan"
            assert line.get_color() == "orange"
            assert len(transport.frames) == 3


def test_unowned_custom_matplotlib_figure_is_not_theme_modified(monkeypatch: pytest.MonkeyPatch) -> None:
    _geometry, transport, _writes = _session(monkeypatch)
    fig = _figure()
    initial = fig.get_facecolor()
    with live.owned_viewport(fig, transport_factory=lambda: transport) as view:
        assert not view.refresh_theme(_theme("0000", "ffff"))
    assert fig.get_facecolor() == initial
    assert len(transport.frames) == 1


def test_owned_theme_refresh_covers_tick_spine_and_grid_decorations() -> None:
    """Owned decorations follow contrast changes; explicit artist edits survive."""
    old = {
        "xtick.color": "#ffffff",
        "ytick.color": "#ffffff",
        "axes.edgecolor": "#ffffff",
        "grid.color": "#404040",
        "axes.grid": True,
    }
    new = {
        "xtick.color": "#000000",
        "ytick.color": "#000000",
        "axes.edgecolor": "#000000",
        "grid.color": "#bfbfbf",
    }

    def rgba(color):
        return mpl.colors.to_rgba(color)

    with mpl.rc_context():
        mpl.rcdefaults()
        fig = TerminalFigure(figsize=(3, 2), dpi=100, _wskr_defaults=old)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        ax.plot([0, 1], [1, 0], color="lime")
        canvas.draw()

        x_ticks = ax.xaxis.get_major_ticks()
        y_ticks = ax.yaxis.get_major_ticks()
        assert len(x_ticks) >= 2
        assert len(y_ticks) >= 2
        x_ticks[0].label1.set_color("magenta")
        ax.spines["left"].set_edgecolor("orange")
        gridlines = ax.xaxis.get_gridlines()
        assert len(gridlines) >= 2
        gridlines[0].set_color("cyan")

        assert ax.refresh_owned_colors(old, new)
        assert rgba(x_ticks[0].label1.get_color()) == rgba("magenta")
        assert rgba(x_ticks[1].label1.get_color()) == rgba("#000000")
        assert rgba(y_ticks[0].label1.get_color()) == rgba("#000000")
        assert rgba(ax.spines["left"].get_edgecolor()) == rgba("orange")
        assert rgba(ax.spines["right"].get_edgecolor()) == rgba("#000000")
        assert rgba(gridlines[0].get_color()) == rgba("cyan")
        assert rgba(gridlines[1].get_color()) == rgba("#bfbfbf")
        assert ax.lines[0].get_color() == "lime"
        assert not ax.refresh_owned_colors(new, new)
