"""Deprecated shim: use :mod:`wskr.terminal.core.ttyools`."""

from __future__ import annotations

import warnings as _w

from wskr.terminal.core.ttyools import *  # noqa: F403

_w.warn("wskr.ttyools is deprecated; use wskr.terminal.core.ttyools", DeprecationWarning, stacklevel=2)
