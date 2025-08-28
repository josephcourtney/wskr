"""Deprecated shim: use :mod:`wskr.terminal.core.registry`."""

from __future__ import annotations

import warnings as _w

from wskr.terminal.core.registry import *  # noqa: F403

_w.warn("wskr.tty.registry is deprecated; use wskr.terminal.core.registry", DeprecationWarning, stacklevel=2)
