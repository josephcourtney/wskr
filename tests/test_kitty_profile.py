"""Pure Kitty XTGETTCAP and provenance tests, independent of a terminal."""

from __future__ import annotations

import pytest

from wskr.terminal.color import RGB
from wskr.terminal.kitty.queries import parse_query_reply, query_request
from wskr.terminal.profile import Geometry, Source, Value, probe_profile

pytestmark = pytest.mark.small


def reply(field: str, value: str, *, success: bool = True) -> bytes:
    name = f"kitty-query-{field}".encode().hex().encode()
    status = b"1" if success else b"0"
    return b"\x1bP" + status + b"+r" + name + b"=" + value.encode().hex().encode() + b"\x1b\\"


def test_request_matches_kitty_xtgettcap_naming():
    assert query_request("font_size") == b"\x1bP+q" + b"kitty-query-font_size".hex().encode() + b"\x1b\\"
    with pytest.raises(ValueError, match="disallowed"):
        query_request("clipboard_control")


def test_response_rejects_wrong_field_failure_and_invalid_frames():
    assert parse_query_reply("font_size", reply("font_size", "13.5")) == "13.5"
    for raw in (
        reply("font_family", "abc"),
        reply("font_size", "13", success=False),
        b"\x1bP1+r" + b"kitty-query-font_size".hex().encode() + b"=123",
        reply("font_size", "x" * 300),
        reply("font_size", "\x00bad"),
    ):
        assert parse_query_reply("font_size", raw) is None


def test_full_kitty_measurements_are_measured_and_osc_takes_precedence():
    values = {
        "font_family": "JetBrainsMono-Regular",
        "font_size": "13.25",
        "dpi_x": "184",
        "dpi_y": "192",
        "background_opacity": "0.72",
        "foreground": "#aabbcc",
        "background": "#101112",
    }
    profile = probe_profile(
        geometry=Geometry(30, 80, 800, 600),
        kitty_query=lambda field: reply(field, values[field]),
        color_query=lambda request: b"\x1b]11;rgb:ffff/ffff/ffff\x07" if b"]11;" in request else b"invalid",
    )
    assert profile.font_family == Value("JetBrainsMono-Regular", Source.MEASURED)
    assert profile.font_size_pt == Value(13.25, Source.MEASURED)
    assert profile.dpi_x == Value(184.0, Source.MEASURED)
    assert profile.dpi_y == Value(192.0, Source.MEASURED)
    assert profile.opacity == Value(0.72, Source.MEASURED)
    assert profile.foreground == Value(RGB(170, 187, 204), Source.MEASURED)
    assert profile.background == Value(RGB(255, 255, 255), Source.MEASURED)
    assert profile.is_dark is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("font_size", "nan"),
        ("font_size", "-1"),
        ("dpi_x", "99999"),
        ("dpi_y", "0"),
        ("background_opacity", "1.2"),
        ("background_opacity", "inf"),
        ("foreground", "red"),
        ("foreground", "#fff"),
    ],
)
def test_invalid_runtime_measurements_stay_unknown(field, value):
    profile = probe_profile(
        geometry=Geometry(24, 80),
        kitty_query=lambda requested: reply(requested, value) if requested == field else b"invalid",
    )
    selected = {
        "font_size": profile.font_size_pt,
        "dpi_x": profile.dpi_x,
        "dpi_y": profile.dpi_y,
        "background_opacity": profile.opacity,
        "foreground": profile.foreground,
    }
    assert selected[field] == Value()


def test_colors_can_be_queried_even_when_geometry_is_unavailable():
    profile = probe_profile(
        geometry=Geometry(0, 0),
        kitty_query=lambda field: reply(field, "#ffffff") if field == "foreground" else b"invalid",
    )
    assert profile.columns.value is None
    assert profile.foreground == Value(RGB(255, 255, 255), Source.MEASURED)
