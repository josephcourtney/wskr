"""Deprecated shim: use :mod:`wskr.terminal.core.command`."""

from __future__ import annotations

import warnings as _w

from wskr.terminal.core.command import *  # noqa: F403

_w.warn("wskr.tty.command is deprecated; use wskr.terminal.core.command", DeprecationWarning, stacklevel=2)
