"""Deprecated shim: use :mod:`wskr.terminal.core.transport`."""

from __future__ import annotations

import warnings as _w

from wskr.terminal.core.base import ImageTransport
from wskr.terminal.core.transport import NoOpTransport

_w.warn(
    "wskr.tty.transport is deprecated; use wskr.terminal.core.transport", DeprecationWarning, stacklevel=2
)

__all__ = ["ImageTransport", "NoOpTransport"]
