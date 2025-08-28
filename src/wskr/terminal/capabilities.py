from __future__ import annotations

import os
import re
from typing import Protocol

from wskr.terminal.osc import query_tty

_OSC_BG_QUERY = b"\033]11;?\007"
_OSC_BG_RESP_RE = re.compile(rb"\]11;rgb:([0-9A-Fa-f]{4})/([0-9A-Fa-f]{4})/([0-9A-Fa-f]{4})")
_ENV_BG_THRESHOLD = 8


class TerminalCapabilities(Protocol):
    def window_px(self) -> tuple[int, int]: ...
    def is_dark(self) -> bool: ...


def _env_is_dark() -> bool:
    val = os.getenv("COLORFGBG", "")
    if ";" not in val:
        msg = "COLORFGBG not set or invalid"
        raise KeyError(msg)
    _, bg = val.split(";", 1)
    return int(bg) < _ENV_BG_THRESHOLD


def _osc_is_dark(timeout: float | None = None) -> bool:
    resp = query_tty(_OSC_BG_QUERY, more=lambda data: not data.endswith(b"\007"), timeout=timeout)
    if not resp:
        msg = "No ANSI background-color response"
        raise RuntimeError(msg)
    m = _OSC_BG_RESP_RE.search(resp)
    if not m:
        msg = f"Unexpected response: {resp!r}"
        raise ValueError(msg)
    rgb = [int(g, 16) / 0xFFFF for g in m.groups()]
    lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    dark_luminance_threshold = 0.5
    return lum < dark_luminance_threshold


__all__ = ["TerminalCapabilities", "_env_is_dark", "_osc_is_dark"]
