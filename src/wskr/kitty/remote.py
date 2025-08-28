"""Deprecated shim: use :mod:`wskr.terminal.kitty.kitty_remote`."""

from __future__ import annotations

import warnings as _w

from wskr.terminal.kitty.kitty_remote import *  # noqa: F403

_w.warn(
    "wskr.kitty.remote is deprecated; use wskr.terminal.kitty.kitty_remote", DeprecationWarning, stacklevel=2
)
