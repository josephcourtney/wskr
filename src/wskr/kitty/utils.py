"""Deprecated shim: use :mod:`wskr.terminal.kitty.kitty_utils`."""

from __future__ import annotations

import warnings as _w

from wskr.terminal.kitty.kitty_utils import *  # noqa: F403

_w.warn(
    "wskr.kitty.utils is deprecated; use wskr.terminal.kitty.kitty_utils", DeprecationWarning, stacklevel=2
)
