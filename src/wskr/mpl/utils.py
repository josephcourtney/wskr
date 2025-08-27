"""Dark mode detection utilities for Matplotlib backends.

The detection logic is implemented as a chain of strategies.  Each strategy
attempts to determine whether the terminal is using a dark colour scheme.  The
default order is environment-variable detection followed by an OSC 11 query.
"""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Protocol

from wskr.config import OSC_TIMEOUT_S
from wskr.ttyools import query_tty

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

# Threshold for deciding “dark” in $COLORFGBG (0-15 scale)
_ENV_BG_THRESHOLD = 8
# Luminance threshold below which we consider the background dark
_LUMINANCE_THRESHOLD = 0.5

# OSC sequence to query the terminal's background color.
_OSC_BG_QUERY = b"\033]11;?\007"
_OSC_BG_RESP_RE = re.compile(rb"\]11;rgb:([0-9A-Fa-f]{4})/([0-9A-Fa-f]{4})/([0-9A-Fa-f]{4})")


class DarkModeStrategy(Protocol):
    """Protocol for dark-mode detection strategies."""

    def detect(self) -> bool:
        """Return ``True`` if the strategy determines the background is dark."""


class EnvColorStrategy:
    """Detect dark mode using the ``COLORFGBG`` environment variable."""

    def detect(self) -> bool:  # noqa: PLR6301 - simple protocol implementation
        val = os.getenv("COLORFGBG", "")
        if ";" not in val:
            msg = "COLORFGBG not set or invalid"
            raise KeyError(msg)
        _, bg = val.split(";", 1)
        return int(bg) < _ENV_BG_THRESHOLD


class OscQueryStrategy:
    """Detect dark mode by querying the terminal via OSC 11."""

    def __init__(self, timeout: float | None = None) -> None:
        self._timeout = timeout if timeout is not None else OSC_TIMEOUT_S

    def detect(self) -> bool:
        resp = query_tty(
            _OSC_BG_QUERY,
            more=lambda data: not data.endswith(b"\007"),
            timeout=self._timeout,
        )
        if not resp:
            msg = "No ANSI background-color response"
            raise RuntimeError(msg)
        m = _OSC_BG_RESP_RE.search(resp)
        if not m:
            msg = f"Unexpected response: {resp!r}"
            raise ValueError(msg)
        rgb = [int(g, 16) / 0xFFFF for g in m.groups()]
        lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
        return lum < _LUMINANCE_THRESHOLD


DEFAULT_STRATEGIES: list[DarkModeStrategy] = [
    EnvColorStrategy(),
    OscQueryStrategy(),
]


def detect_dark_mode(
    strategies: Sequence[DarkModeStrategy] | None = None,
) -> bool:
    """Return ``True`` when any strategy reports a dark background.

    ``WSKR_DARK_MODE`` acts as an override.  If unset, the configured
    strategies are tried in order until one succeeds.
    """
    override = os.getenv("WSKR_DARK_MODE")
    if override is not None:
        return override.lower() in {"1", "true", "yes", "on"}
    for strat in strategies or DEFAULT_STRATEGIES:
        try:
            if strat.detect():
                return True
        except (KeyError, RuntimeError, ValueError, OSError) as e:
            logger.debug("%s failed: %s", strat.__class__.__name__, e)
    return False


__all__ = [
    "DarkModeStrategy",
    "EnvColorStrategy",
    "OscQueryStrategy",
    "detect_dark_mode",
]
