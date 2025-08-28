"""Deprecated shim: use :mod:`wskr.render.matplotlib.size`."""

from __future__ import annotations

import warnings as _w

from wskr.render.matplotlib.size import *  # noqa: F403

_w.warn("wskr.mpl.size is deprecated; use wskr.render.matplotlib.size", DeprecationWarning, stacklevel=2)
