from __future__ import annotations

from .capabilities import TerminalCapabilities, _env_is_dark


class GenericCapabilities(TerminalCapabilities):
    """Conservative, portable capability detector."""

    def window_px(self) -> tuple[int, int]:  # ruff: ignore[no-self-use]
        return (800, 600)

    def is_dark(self) -> bool:  # ruff: ignore[no-self-use]
        try:
            return _env_is_dark()
        except Exception:  # ruff: ignore[blind-except] - best-effort, default to False
            return False


__all__ = ["GenericCapabilities"]
