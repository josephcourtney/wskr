"""Base terminal capability interfaces and safe appearance fallback."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

from wskr.terminal.color import parse_osc_color
from wskr.terminal.query import query_osc

_OSC_BG_QUERY = b"\033]11;?\007"
_ENV_BG_THRESHOLD = 8


class TerminalCapabilities(Protocol):
    def window_px(self) -> tuple[int, int]: ...
    def is_dark(self) -> bool: ...


def _env_is_dark() -> bool:
    value = os.getenv("COLORFGBG", "")
    if ";" not in value:
        msg = "COLORFGBG not set or invalid"
        raise KeyError(msg)
    return int(value.rsplit(";", 1)[-1]) < _ENV_BG_THRESHOLD


def _osc_is_dark(
    timeout: float | None = None,
    *,
    owns_input: bool = False,
    on_unmatched: Callable[[bytes], None] | None = None,
) -> bool:
    response = query_osc(
        _OSC_BG_QUERY,
        owns_input=owns_input,
        on_unmatched=on_unmatched,
        timeout=0.15 if timeout is None else timeout,
    )
    return parse_osc_color(response, 11).is_dark


__all__ = ["TerminalCapabilities", "_env_is_dark", "_osc_is_dark"]
