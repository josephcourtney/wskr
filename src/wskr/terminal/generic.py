from __future__ import annotations

from .capabilities import TerminalCapabilities, _env_is_dark


class GenericCapabilities(TerminalCapabilities):
    """Conservative, portable capability detector."""

    def window_px(self) -> tuple[int, int]:  # noqa: PLR6301
        return (800, 600)

    def is_dark(self) -> bool:  # noqa: PLR6301
        try:
            return _env_is_dark()
        except Exception:  # noqa: BLE001 - best-effort, default to False
            return False


__all__ = ["GenericCapabilities"]
