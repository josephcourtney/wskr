"""Terminal dark/light determination with explicit ownership and true fallback."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Protocol

from wskr.core.config import OSC_TIMEOUT_S
from wskr.terminal.color import parse_osc_color
from wskr.terminal.query import query_osc

try:
    import darkdetect  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional OS appearance fallback
    darkdetect = None

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

logger = logging.getLogger(__name__)
_ENV_BG_THRESHOLD = 8
_OSC_BG_QUERY = b"\033]11;?\007"


class DarkModeStrategy(Protocol):
    def detect(self) -> bool: ...


class EnvColorStrategy:
    def detect(self) -> bool:  # ruff: ignore[no-self-use] - strategy protocol method
        value = os.getenv("COLORFGBG", "")
        if ";" not in value:
            msg = "COLORFGBG not set or invalid"
            raise KeyError(msg)
        return int(value.rsplit(";", 1)[-1]) < _ENV_BG_THRESHOLD


class OscQueryStrategy:
    """Use a guarded query, or an explicitly provided test/query callback."""

    def __init__(
        self,
        timeout: float | None = None,
        *,
        owns_input: bool = False,
        on_unmatched: Callable[[bytes], None] | None = None,
        query: Callable[..., bytes] | None = None,
    ) -> None:
        self._timeout = timeout if timeout is not None else OSC_TIMEOUT_S
        self._owns_input = owns_input
        self._on_unmatched = on_unmatched
        self._query = query

    def detect(self) -> bool:
        if self._query is not None:
            response = self._query(
                _OSC_BG_QUERY,
                more=lambda data: not data.endswith((b"\x07", b"\x1b\\")),
                timeout=self._timeout,
            )
        else:
            response = query_osc(
                _OSC_BG_QUERY,
                owns_input=self._owns_input,
                on_unmatched=self._on_unmatched,
                timeout=self._timeout,
            )
        if not response:
            msg = "No ANSI background-color response"
            raise RuntimeError(msg)
        return parse_osc_color(response, 11).is_dark


class DarkDetectStrategy:
    def detect(self) -> bool:  # ruff: ignore[no-self-use] - strategy protocol method
        if darkdetect is None:
            msg = "darkdetect not available"
            raise RuntimeError(msg)
        mode = darkdetect.theme()
        if mode is None:
            msg = "darkdetect could not determine theme"
            raise RuntimeError(msg)
        return mode.lower() == "dark"


def detect_dark_mode(
    strategies: Sequence[DarkModeStrategy] | None = None,
    *,
    owns_input: bool = False,
    on_unmatched: Callable[[bytes], None] | None = None,
) -> bool:
    """First valid result is definitive, including a light/False result.

    Default probing never consumes a shared TTY: the OSC strategy raises before
    opening a terminal unless a caller explicitly owns and can forward input.
    """
    override = os.getenv("WSKR_DARK_MODE")
    if override is not None:
        return override.lower() in {"1", "true", "yes", "on"}

    candidates = (
        strategies
        if strategies is not None
        else [
            OscQueryStrategy(owns_input=owns_input, on_unmatched=on_unmatched),
            EnvColorStrategy(),
            DarkDetectStrategy(),
        ]
    )
    for strategy in candidates:
        try:
            return strategy.detect()
        except (KeyError, RuntimeError, ValueError, OSError, TimeoutError) as exc:
            logger.debug("%s failed: %s", type(strategy).__name__, exc)
    return False


__all__ = [
    "DarkDetectStrategy",
    "DarkModeStrategy",
    "EnvColorStrategy",
    "OscQueryStrategy",
    "detect_dark_mode",
]
