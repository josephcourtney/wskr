"""Deprecated shim: use :mod:`wskr.terminal.core.base`."""

from __future__ import annotations

import warnings as _w

from wskr.terminal.core.base import *  # noqa: F403

_w.warn("wskr.tty.base is deprecated; use wskr.terminal.core.base", DeprecationWarning, stacklevel=2)
