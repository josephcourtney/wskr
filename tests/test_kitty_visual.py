"""Unit tests for live-Kitty screenshot content matching."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from tests.kitty_visual import assert_logo_visible

ASSETS = Path(__file__).parent


def test_saved_reference_contains_logo():
    """A known correct screenshot is the detector's positive control."""
    with (
        Image.open(ASSETS / "data/reference/cap_0001.png") as capture,
        Image.open(ASSETS / "test.png") as logo,
    ):
        detected = assert_logo_visible(capture, logo)
    assert detected["blue_pixels"] >= 200
    assert detected["yellow_pixels"] >= 200


@pytest.mark.parametrize("background", [(238, 235, 231), (15, 15, 20)])
@pytest.mark.parametrize("size", [(150, 150), (220, 220)])
def test_logo_detection_tolerates_theme_and_scale(background, size):
    with Image.open(ASSETS / "test.png") as original:
        logo = original.convert("RGBA")
    capture = Image.new("RGB", (800, 600), background)
    scaled = logo.resize(size, Image.Resampling.LANCZOS)
    capture.paste(scaled, (173, 95), scaled)
    assert_logo_visible(capture, logo)


def test_blank_capture_fails():
    with Image.open(ASSETS / "test.png") as logo:
        with pytest.raises(AssertionError, match="not detected"):
            assert_logo_visible(Image.new("RGB", (800, 600), "#ece8e1"), logo)


def test_reversed_color_geometry_fails():
    with Image.open(ASSETS / "test.png") as logo:
        capture = Image.new("RGB", (800, 600), "#ece8e1")
        draw = ImageDraw.Draw(capture)
        draw.rectangle((300, 300, 425, 425), fill="#3976a7")
        draw.rectangle((125, 120, 250, 245), fill="#ffdd55")
        with pytest.raises(AssertionError, match="do not form"):
            assert_logo_visible(capture, logo)
