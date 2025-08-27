import logging
import os
import re

from wskr.ttyools import query_tty

logger = logging.getLogger(__name__)

# Threshold for deciding “dark” in $COLORFGBG (0-15 scale)
_ENV_BG_THRESHOLD = 8
# Luminance threshold below which we consider the background dark
_LUMINANCE_THRESHOLD = 0.5

# OSC sequence to query the terminal's background color.
# We send BEL-terminated “11;?” and expect back e.g.
#   '\x1b]11;rgb:hhhh/hhhh/hhhh\x07'
# where each 'hhhh' is a 16-bit hex channel.
_OSC_BG_QUERY = b"\033]11;?\007"
_OSC_BG_RESP_RE = re.compile(rb"\]11;rgb:([0-9A-Fa-f]{4})/" rb"([0-9A-Fa-f]{4})/" rb"([0-9A-Fa-f]{4})")


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
    override = os.getenv("WSKR_DARK_MODE")
    if override is not None:
        return override.lower() in {"1", "true", "yes", "on"}
    for fn in (is_dark_mode_env, is_dark_mode_osc):
        try:
            if fn():
                return True
        except (KeyError, RuntimeError, ValueError, OSError) as e:
            logger.debug("%s failed: %s", fn.__name__, e)
    return False
