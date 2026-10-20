"""OSC response parsing and perceptual RGB tests."""

import pytest

pytestmark = pytest.mark.small

from wskr.terminal.color import RGB, parse_osc_color


@pytest.mark.parametrize("ending", [b"\x07", b"\x1b\\"])
def test_osc_11_accepts_bel_and_st(ending):
    value = parse_osc_color(b"\x1b]11;rgb:ffff/0000/8000" + ending, 11)
    assert value == RGB(255, 0, 128)


def test_channel_depth_scales_to_eight_bits():
    assert parse_osc_color(b"\x1b]10;rgb:f/8/0\x07", 10) == RGB(255, 136, 0)
    assert parse_osc_color(b"\x1b]10;rgb:ff/80/00\x07", 10) == RGB(255, 128, 0)


def test_osc_palette_index_is_checked():
    response = b"\x1b]4;3;rgb:ffff/1111/0000\x1b\\"
    assert parse_osc_color(response, 4, 3) == RGB(255, 17, 0)
    with pytest.raises(ValueError, match="index"):
        parse_osc_color(response, 4, 4)


@pytest.mark.parametrize(
    "bad",
    [
        b"",
        b"garbage\x1b]11;rgb:ffff/ffff/ffff\x07",
        b"\x1b]11;rgb:ffff/0000/0000",
        b"\x1b]11;rgb:ffff/0000/0000\x07garbage",
        b"\x1b]11;rgb:ffff/0000/gggg\x07",
        b"\x1b]11;rgb:ffff/0000/0000\x07" + b"A" * 200,
    ],
)
def test_malformed_osc_replies_fail_closed(bad):
    with pytest.raises(ValueError, match="Unexpected|Oversized"):
        parse_osc_color(bad, 11)


def test_osc_response_selector_is_validated():
    with pytest.raises(ValueError, match="selector"):
        parse_osc_color(b"\x1b]10;rgb:ffff/ffff/ffff\x07", 11)


def test_luminance_uses_linearized_rgb():
    assert RGB(0, 0, 0).is_dark is True
    assert RGB(255, 255, 255).is_dark is False
    assert RGB(255, 255, 255).luminance == pytest.approx(1)
    assert RGB(0, 0, 0).to_hex() == "#000000"


def test_color_channels_validate_range():
    with pytest.raises(ValueError, match="RGB"):
        RGB(-1, 10, 255)
