"""Configuration constants for wskr.

This module centralizes small tunables that were previously hard coded.
Values may be overridden with environment variables where noted.
"""

from __future__ import annotations

import os

# Bytes per chunk when streaming images over the Kitty protocol.
IMAGE_CHUNK_SIZE: int = 4096

# Typical number of terminal rows; used to subtract the status bar height
# when computing drawable area.  Terminals are often 24 rows tall.
DEFAULT_TTY_ROWS: int = 24

# Time-to-live for cached window size values in KittyTransport.  Setting the
# ``WSKR_CACHE_TTL_S`` environment variable allows tests or users to tune this
# behaviour.
CACHE_TTL_S: float = float(os.getenv("WSKR_CACHE_TTL_S", "1.0"))

__all__ = ["CACHE_TTL_S", "DEFAULT_TTY_ROWS", "IMAGE_CHUNK_SIZE"]
