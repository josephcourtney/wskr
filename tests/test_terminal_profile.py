"""Provenance-aware terminal profile tests without any terminal I/O."""

import struct
from dataclasses import FrozenInstanceError

import pytest

from wskr.terminal import profile
from wskr.terminal.color import RGB
from wskr.terminal.profile import Geometry, Source, Value, probe_profile

pytestmark = pytest.mark.small


def test_geometry_is_measured_and_cell_pixels_are_inferred():
    result = probe_profile(geometry=Geometry(30, 100, 900, 600))
    assert result.rows == Value(30, Source.MEASURED)
    assert result.columns == Value(100, Source.MEASURED)
    assert result.width_px == Value(900, Source.MEASURED)
    assert result.cell_width_px == Value(9.0, Source.INFERRED)
    assert result.cell_height_px == Value(20.0, Source.INFERRED)
    assert result.background.source == Source.UNKNOWN
    assert result.font_family.value is None
    assert result.dpi_x.value is None
    assert result.is_dark is None


def test_unavailable_pixel_geometry_is_not_fabricated():
    result = probe_profile(geometry=Geometry(24, 80))
    assert result.rows.source == Source.MEASURED
    assert result.width_px.value is None
    assert result.cell_width_px.source == Source.UNKNOWN


def test_invalid_geometry_has_no_fabricated_measurements():
    result = probe_profile(geometry=Geometry(0, 80))
    assert result.rows.value is None
    assert result.foreground.value is None


def test_immutable_value_and_provenance_invariants():
    with pytest.raises(ValueError, match="unknown provenance"):
        Value(None, Source.MEASURED)
    with pytest.raises(ValueError, match="unknown provenance"):
        Value(5, Source.UNKNOWN)
    item = Value(5, Source.INFERRED)
    name = "value"
    with pytest.raises(FrozenInstanceError):
        setattr(item, name, 8)


def test_opt_in_color_probe_recognizes_light_background_and_palette():
    requests = []

    def query(request: bytes) -> bytes:
        requests.append(request)
        if request.startswith(b"\x1b]10;"):
            return b"\x1b]10;rgb:0000/0000/0000\x07"
        if request.startswith(b"\x1b]11;"):
            return b"\x1b]11;rgb:ffff/ffff/ffff\x1b\\"
        index = int(request.split(b";")[1])
        return f"\x1b]4;{index};rgb:ffff/0000/0000\x07".encode()

    result = probe_profile(geometry=Geometry(24, 80, 800, 480), color_query=query, palette=True)
    assert len(requests) == 18
    assert result.foreground.value == RGB(0, 0, 0)
    assert result.background.value == RGB(255, 255, 255)
    assert result.is_dark is False
    assert result.ansi_palette.source == Source.MEASURED
    assert result.ansi_palette.value is not None
    assert result.ansi_palette.value[0] == RGB(255, 0, 0)


def test_color_probe_failures_remain_unknown():
    result = probe_profile(
        geometry=Geometry(24, 80, 800, 480),
        color_query=lambda _request: b"oops",
    )
    assert result.background.source == Source.UNKNOWN
    assert result.foreground.source == Source.UNKNOWN


def test_read_geometry_refuses_redirected_output(monkeypatch):
    class Redirected:
        def isatty(self):
            return False

    monkeypatch.setattr(profile.sys, "stdout", Redirected())
    assert profile.read_geometry() is None


def test_read_geometry_reads_kernel_winsize(monkeypatch):
    class Tty:
        def isatty(self):
            return True

        def fileno(self):
            return 19

    monkeypatch.setattr(profile.sys, "stdout", Tty())
    monkeypatch.setattr(
        profile.fcntl,
        "ioctl",
        lambda fd, op, buf: struct.pack("HHHH", 24, 80, 720, 480),
    )
    assert profile.read_geometry() == Geometry(24, 80, 720, 480)


def test_read_geometry_handles_kernel_failure(monkeypatch):
    class Tty:
        def isatty(self):
            return True

        def fileno(self):
            return 19

    monkeypatch.setattr(profile.sys, "stdout", Tty())

    def failing(*_args):
        msg = "no controlling terminal"
        raise OSError(msg)

    monkeypatch.setattr(profile.fcntl, "ioctl", failing)
    assert profile.read_geometry() is None


def test_owned_csi_queries_supply_measurements_when_ioctl_pixels_missing():
    requests = []

    def reply(request: bytes) -> bytes:
        requests.append(request)
        return {
            b"\x1b[14t": b"\x1b[4;720;1280t",
            b"\x1b[16t": b"\x1b[6;24;16t",
        }[request]

    result = probe_profile(geometry=Geometry(30, 80), geometry_query=reply)
    assert requests == [b"\x1b[14t", b"\x1b[16t"]
    assert result.width_px == Value(1280, Source.MEASURED)
    assert result.height_px == Value(720, Source.MEASURED)
    assert result.cell_width_px == Value(16.0, Source.MEASURED)
    assert result.cell_height_px == Value(24.0, Source.MEASURED)


def test_kernel_pixels_win_over_conflicting_terminal_queries():
    requests = []

    def reply(request: bytes) -> bytes:
        requests.append(request)
        return b"\x1b[6;20;11t"

    result = probe_profile(geometry=Geometry(30, 80, 1000, 600), geometry_query=reply)
    assert requests == [b"\x1b[16t"]
    assert result.width_px == Value(1000, Source.MEASURED)
    assert result.height_px == Value(600, Source.MEASURED)
    assert result.cell_width_px == Value(11.0, Source.MEASURED)
    assert result.cell_height_px == Value(20.0, Source.MEASURED)


def test_owned_csi_cell_query_can_infer_unavailable_window_pixels():
    def reply(request: bytes) -> bytes:
        if request == b"\x1b[14t":
            return b"\x1b[6;20;10t"  # wrong reply type; never claim it as window data
        return b"\x1b[6;20;10t"

    result = probe_profile(geometry=Geometry(25, 80), geometry_query=reply)
    assert result.width_px == Value(800, Source.INFERRED)
    assert result.height_px == Value(500, Source.INFERRED)
    assert result.cell_width_px == Value(10.0, Source.MEASURED)
    assert result.cell_height_px == Value(20.0, Source.MEASURED)


@pytest.mark.parametrize("bad", [
    b"",
    b"\x1b[4;0;800t",
    b"\x1b[4;300;-10t",
    b"\x1b[4;300;800tgarbage",
    b"\x1b[6;20;10t",
])
def test_malformed_or_unrelated_window_replies_do_not_create_measurements(bad):
    def reply(request: bytes) -> bytes:
        return bad if request == b"\x1b[14t" else b"invalid"

    result = probe_profile(geometry=Geometry(25, 80), geometry_query=reply)
    assert result.width_px == Value()
    assert result.height_px == Value()
    assert result.cell_width_px == Value()
    assert result.cell_height_px == Value()
