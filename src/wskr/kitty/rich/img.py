"""Deprecated shim: use :mod:`wskr.render.rich.img`."""

from __future__ import annotations

import warnings as _w

from wskr.render.rich.img import *  # noqa: F403

_w.warn("wskr.kitty.rich.img is deprecated; use wskr.render.rich.img", DeprecationWarning, stacklevel=2)
