"""Deprecated shim: use :mod:`wskr.render.matplotlib.utils`."""

from __future__ import annotations

import warnings as _w

from wskr.render.matplotlib.utils import *  # noqa: F403

_w.warn("wskr.mpl.utils is deprecated; use wskr.render.matplotlib.utils", DeprecationWarning, stacklevel=2)
