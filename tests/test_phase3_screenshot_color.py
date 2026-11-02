"""ICC provenance and sRGB normalization regression for native screenshot evidence."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import numpy as np
import pytest
from PIL import Image, ImageCms

from scripts.phase3_native_macos_paging import _COLORS, _color_pixels_with_metadata
from scripts.phase3_screenshot_color import read_screenshot_srgb

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.medium


def _srgb_icc() -> bytes:
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def test_tagged_capture_is_normalized_and_records_icc_provenance(tmp_path: Path) -> None:
    path = tmp_path / "tagged.png"
    icc = _srgb_icc()
    Image.new("RGB", (100, 100), _COLORS[0][1]).save(path, icc_profile=icc)
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    pixels, metadata = read_screenshot_srgb(path)
    assert tuple(int(value) for value in pixels[50, 50]) == _COLORS[0][1]
    assert metadata["conversion"] == "icc_to_srgb"
    assert metadata["icc_sha256"] == hashlib.sha256(icc).hexdigest()
    assert "sRGB" in str(metadata["icc_description"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_untagged_capture_is_explicit_fallback(tmp_path: Path) -> None:
    path = tmp_path / "untagged.png"
    Image.new("RGB", (100, 100), _COLORS[0][1]).save(path)
    pixels, metadata = read_screenshot_srgb(path)
    assert np.all(pixels[0, 0] == _COLORS[0][1])
    assert metadata == {
        "conversion": "untagged_assumed_srgb",
        "icc_sha256": None,
        "icc_description": None,
    }


def test_corrupt_embedded_profile_does_not_silently_assume_srgb(tmp_path: Path) -> None:
    path = tmp_path / "invalid-icc.png"
    Image.new("RGB", (30, 30), _COLORS[0][1]).save(path, icc_profile=b"not-an-icc-profile")
    with pytest.raises(ValueError, match="Cannot interpret embedded screenshot ICC"):
        read_screenshot_srgb(path)


def test_tagged_paging_uses_tight_srgb_tolerance_and_exclusive_tile_counts(tmp_path: Path) -> None:
    """A slightly wrong tagged color must not be accepted by broad fallback."""
    path = tmp_path / "tags.png"
    pixels = np.zeros((100, 220, 3), dtype=np.uint8)
    pixels[:, :100] = _COLORS[0][1]
    pixels[:, 110:210] = (237, 54, 68)  # Too far from exact red for the tagged path.
    Image.fromarray(pixels).save(path, icc_profile=_srgb_icc())

    counts, metadata = _color_pixels_with_metadata(path)
    assert counts[0] >= 9000
    assert counts[0] < 11000
    assert counts[1:] == [0] * (len(_COLORS) - 1)
    assert metadata["conversion"] == "icc_to_srgb"


def test_untagged_paging_keeps_color_shift_fallback(tmp_path: Path) -> None:
    path = tmp_path / "transformed-but-untagged.png"
    Image.new("RGB", (120, 120), (218, 60, 74)).save(path)
    counts, metadata = _color_pixels_with_metadata(path)
    assert counts[0] >= 12000
    assert counts[1:] == [0] * (len(_COLORS) - 1)
    assert metadata["conversion"] == "untagged_assumed_srgb"
