"""Centralised configuration for :mod:`wskr`.

Environment variables provide the initial values.  Calling :func:`configure`
at runtime allows tests or applications to override those values with keyword
arguments which take precedence over the environment and built-in defaults.
"""

from __future__ import annotations

import os
from typing import Any

# Bytes per chunk when streaming images over the Kitty protocol.
IMAGE_CHUNK_SIZE: int = 4096

# Typical number of terminal rows; used to subtract the status bar height when
# computing drawable area.  Terminals are often 24 rows tall.
DEFAULT_TTY_ROWS: int = 24

# Time-to-live for cached window size values in ``KittyTransport``.
CACHE_TTL_S: float = float(os.getenv("WSKR_CACHE_TTL_S", "1.0"))

# Generic timeout for subprocess or TTY operations.
TIMEOUT_S: float = float(os.getenv("WSKR_TIMEOUT_S", "1.0"))

# Timeout for OSC 11 colour queries.
OSC_TIMEOUT_S: float = float(os.getenv("WSKR_OSC_TIMEOUT_S", "0.1"))

# Fallback policy when transports are unavailable.
FALLBACK: str = os.getenv("WSKR_FALLBACK", "noop")

# Dark mode policy override: ``force-on``, ``force-off`` or ``auto``.
DARK_MODE_POLICY: str = os.getenv("WSKR_DARK_MODE_POLICY", "auto")


def configure(**overrides: Any) -> dict[str, Any]:
    """Override configuration values with keyword arguments.

    Parameters are matched case-insensitively against known configuration
    fields.  Unknown keys are ignored to keep behaviour predictable.
    """
    globals_dict = globals()
    for key, value in overrides.items():
        name = key.upper()
        if name in globals_dict:
            globals_dict[name] = value
    return {
        "CACHE_TTL_S": CACHE_TTL_S,
        "TIMEOUT_S": TIMEOUT_S,
        "OSC_TIMEOUT_S": OSC_TIMEOUT_S,
        "FALLBACK": FALLBACK,
        "DARK_MODE_POLICY": DARK_MODE_POLICY,
    }


__all__ = [
    "CACHE_TTL_S",
    "DARK_MODE_POLICY",
    "DEFAULT_TTY_ROWS",
    "FALLBACK",
    "IMAGE_CHUNK_SIZE",
    "OSC_TIMEOUT_S",
    "TIMEOUT_S",
    "configure",
]
