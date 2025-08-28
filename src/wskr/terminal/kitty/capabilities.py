from __future__ import annotations

import logging
import shutil

from wskr.core.config import DEFAULT_TTY_ROWS
from wskr.terminal.capabilities import TerminalCapabilities, _env_is_dark, _osc_is_dark
from wskr.terminal.core.command import CommandRunner

logger = logging.getLogger(__name__)


class KittyCapabilities(TerminalCapabilities):
    """Kitty-specific capability detector using its control helpers."""

    def __init__(self) -> None:
        kb = shutil.which("kitty")
        if not kb:
            msg = "kitty binary not found"
            raise FileNotFoundError(msg)
        self._kitty = kb
        self._runner = CommandRunner()

    def window_px(self) -> tuple[int, int]:
        try:
            proc = self._runner.run(
                [self._kitty, "+kitten", "icat", "--print-window-size"],
                capture_output=True,
                text=True,
                check=True,
            )
            w_px, h_px = map(int, proc.stdout.strip().split("x"))
        except OSError:  # fall back conservatively on exec errors
            logger.debug("KittyCapabilities.window_px failed", exc_info=True)
            return (800, 600)
        rows = DEFAULT_TTY_ROWS
        return (w_px, h_px - (3 * h_px) // rows)

    def is_dark(self) -> bool:  # noqa: PLR6301
        # Prefer OSC background query; fall back to COLORFGBG
        try:
            return _osc_is_dark()
        except Exception:  # noqa: BLE001 - best-effort
            try:
                return _env_is_dark()
            except Exception:  # noqa: BLE001 - default False
                return False


__all__ = ["KittyCapabilities"]
