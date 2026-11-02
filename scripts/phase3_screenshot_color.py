"""Normalize native screenshot pixel colors before acceptance comparisons.

Only screenshots are color-managed. The rendering backend continues to
transmit unchanged PNG bytes to Kitty; ICC metadata is diagnostic evidence.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms


@lru_cache(maxsize=1)
def _srgb_profile() -> ImageCms.ImageCmsProfile:
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))


def read_screenshot_srgb(path: Path) -> tuple[np.ndarray, dict[str, str | None]]:
    """Return RGB pixels in sRGB and provenance of the screenshot transform.

    Apple window captures commonly embed a display ICC profile. Their raw
    channel values are in that profile, not the source PNG's sRGB space.
    Untagged captures are assumed to be sRGB and marked as unverified.
    Invalid embedded profiles fail explicitly rather than silently causing
    acceptance from arbitrarily transformed pixels.
    """
    with Image.open(path) as screenshot:
        embedded = screenshot.info.get("icc_profile")
        rgb = screenshot.convert("RGB")
        if not embedded:
            return np.asarray(rgb), {
                "conversion": "untagged_assumed_srgb",
                "icc_sha256": None,
                "icc_description": None,
            }
        try:
            profile = ImageCms.ImageCmsProfile(BytesIO(embedded))
            converted = ImageCms.profileToProfile(rgb, profile, _srgb_profile(), outputMode="RGB")
            description = ImageCms.getProfileDescription(profile)
        except (ImageCms.PyCMSError, OSError, ValueError) as exc:
            msg = f"Cannot interpret embedded screenshot ICC profile in {path}"
            raise ValueError(msg) from exc
        return np.asarray(converted), {
            "conversion": "icc_to_srgb",
            "icc_sha256": hashlib.sha256(embedded).hexdigest(),
            "icc_description": description,
        }
