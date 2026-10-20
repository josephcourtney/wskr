"""Content-focused visual assertion for the existing Python-logo Kitty test."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy import ndimage

if TYPE_CHECKING:
    from PIL import Image


@dataclass(frozen=True)
class ColorRegion:
    pixels: int
    center_x: float
    center_y: float
    bounds: tuple[int, int, int, int]


def _source_colors(logo: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    rgba = np.asarray(logo.convert("RGBA"), dtype=np.int16)
    red, green, blue, alpha = (rgba[..., i] for i in range(4))
    opaque = alpha >= 220
    blue_mask = opaque & (blue > red + 40) & (blue > green + 15)
    yellow_mask = opaque & (red > blue + 70) & (green > blue + 50)
    if min(np.count_nonzero(blue_mask), np.count_nonzero(yellow_mask)) < 100:
        msg = "Test logo must contain sizeable blue and yellow regions"
        raise AssertionError(msg)
    return np.median(rgba[blue_mask, :3], axis=0), np.median(rgba[yellow_mask, :3], axis=0)


def _largest_region(rgb: np.ndarray, color: np.ndarray) -> ColorRegion:
    matching = np.all(np.abs(rgb.astype(np.int16) - color) <= 52, axis=2)
    labels, count = ndimage.label(matching)
    if count == 0:
        return ColorRegion(0, 0, 0, (0, 0, 0, 0))
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    yy, xx = np.nonzero(labels == int(counts.argmax()))
    return ColorRegion(
        pixels=int(counts.max()),
        center_x=float(xx.mean()),
        center_y=float(yy.mean()),
        bounds=(int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())),
    )


def _logo_bounds(blue: ColorRegion, yellow: ColorRegion) -> tuple[int, int, int, int]:
    """Check the relative region geometry and return the combined image bounds."""
    left = min(blue.bounds[0], yellow.bounds[0])
    top = min(blue.bounds[1], yellow.bounds[1])
    right = max(blue.bounds[2], yellow.bounds[2])
    bottom = max(blue.bounds[3], yellow.bounds[3])
    width, height = right - left + 1, bottom - top + 1
    overlap_x = min(blue.bounds[2], yellow.bounds[2]) - max(blue.bounds[0], yellow.bounds[0])
    overlap_y = min(blue.bounds[3], yellow.bounds[3]) - max(blue.bounds[1], yellow.bounds[1])
    proper_order = blue.center_x < yellow.center_x and blue.center_y < yellow.center_y
    plausible_shape = 0.6 <= width / height <= 1.7 and overlap_x > width * 0.05 and overlap_y > height * 0.05
    if not proper_order or not plausible_shape:
        msg = f"Colors do not form the Python logo: blue={blue}; yellow={yellow}; extent={width}x{height}"
        raise AssertionError(msg)
    return left, top, right, bottom


def assert_logo_visible(capture: Image.Image, logo: Image.Image) -> dict[str, object]:
    """Verify that the expected logo, not merely terminal UI, is visible.

    The test tolerates background/theme, translation, and reasonable scaling
    changes. It is not a pixel-accurate reproduction or style validation.
    """
    rgb = np.asarray(capture.convert("RGB"))
    blue_ref, yellow_ref = _source_colors(logo)
    blue = _largest_region(rgb, blue_ref)
    yellow = _largest_region(rgb, yellow_ref)
    minimum = max(200, int(rgb.shape[0] * rgb.shape[1] * 0.0004))
    if blue.pixels < minimum or yellow.pixels < minimum:
        msg = (
            "Expected logo colors not detected as large contiguous regions: "
            f"blue={blue.pixels}, yellow={yellow.pixels}, minimum={minimum}"
        )
        raise AssertionError(msg)

    return {
        "bounds": _logo_bounds(blue, yellow),
        "blue_pixels": blue.pixels,
        "yellow_pixels": yellow.pixels,
    }
