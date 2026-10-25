"""Foreground-owned live viewport: isolation, debounce and scoped cleanup."""

from __future__ import annotations

import os
from io import BytesIO

import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from wskr.protocol.base import ImageProtocol
from wskr.render.matplotlib import core, live
from wskr.terminal.profile import Geometry

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
