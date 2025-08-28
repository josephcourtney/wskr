"""Deprecated shim: use :mod:`wskr.render.matplotlib.kitty`."""

from __future__ import annotations

import warnings as _w

from wskr.render.matplotlib.kitty import *  # noqa: F403

_w.warn("wskr.kitty.mpl is deprecated; use wskr.render.matplotlib.kitty", DeprecationWarning, stacklevel=2)
