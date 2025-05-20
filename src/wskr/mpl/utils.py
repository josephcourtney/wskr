import logging
import os
import re

from matplotlib.figure import Figure

from wskr.ttyools import query_tty

logger = logging.getLogger(__name__)

# Threshold for deciding “dark” in $COLORFGBG (0-15 scale)
_ENV_BG_THRESHOLD = 8
# Luminance threshold below which we consider the background dark
_LUMINANCE_THRESHOLD = 0.5


def autosize_figure(figure: Figure, width_px: int, height_px: int) -> None:
    """Resize the figure to fit the terminal window, preserving aspect ratio."""
    # Skip resizing if we got non-positive dimensions
    if width_px <= 0 or height_px <= 0:
        logger.warning(
            "autosize_figure: received non-positive dimensions (%d, %d), skipping resize",
            width_px,
            height_px,
        )
        return

    dpi = figure.dpi
    orig_w, orig_h = figure.get_size_inches()
    aspect = orig_h / orig_w if orig_w else 1.0

    if aspect > 1:
        new_h = height_px / dpi
        new_w = new_h / aspect
    else:
        new_w = width_px / dpi
        new_h = new_w * aspect

    figure.set_size_inches(new_w, new_h)


# OSC sequence to query the terminal's background color.
# We send BEL-terminated “11;?” and expect back e.g.
#   '\x1b]11;rgb:hhhh/hhhh/hhhh\x07'
# where each 'hhhh' is a 16-bit hex channel.
_OSC_BG_QUERY = b"\033]11;?\007"
_OSC_BG_RESP_RE = re.compile(
    rb"\]11;rgb:([0-9A-Fa-f]{4})/"
    rb"([0-9A-Fa-f]{4})/"
    rb"([0-9A-Fa-f]{4})"
)


def is_dark_mode_env() -> bool:
    """Detect via $COLORFGBG (e.g. '15;0' for white on black)."""
    val = os.getenv("COLORFGBG", "")
    if ";" not in val:
        msg = "COLORFGBG not set or invalid"
        raise KeyError(msg)
    _, bg = val.split(";", 1)
    return int(bg) < _ENV_BG_THRESHOLD


def is_dark_mode_osc(timeout: float = 0.1) -> bool:
    """Query terminal with OSC 11;? BEL → parse 'rgb:xxxx/xxxx/xxxx'."""
    resp = query_tty(
        _OSC_BG_QUERY,
        more=lambda data: not data.endswith(b"\007"),
        timeout=timeout,
    )
    if not resp:
        msg = "No ANSI background-color response"
        raise RuntimeError(msg)
    m = _OSC_BG_RESP_RE.search(resp)
    if not m:
        msg = f"Unexpected response: {resp!r}"
        raise ValueError(msg)
    # convert from 16-bit hex to float [0.0-1.0]
    rgb = [int(g, 16) / 0xFFFF for g in m.groups()]
    # Rec. 709 luminance
    lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return lum < _LUMINANCE_THRESHOLD


def detect_dark_mode() -> bool:
    """Try env-var first, then OSC; default to False (light)."""
    for fn in (is_dark_mode_env, is_dark_mode_osc):
        try:
            if fn():
                return True
        except (KeyError, RuntimeError, ValueError, OSError):
            # Couldn't detect via env-var or OSC (no TTY, etc.) → default to light
            continue
    return False
