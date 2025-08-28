"""Deprecated shim: use :mod:`wskr.render.rich.plt`."""

from __future__ import annotations

import warnings as _w

from wskr.render.rich.plt import *  # noqa: F403

_w.warn("wskr.kitty.rich.plt is deprecated; use wskr.render.rich.plt", DeprecationWarning, stacklevel=2)
