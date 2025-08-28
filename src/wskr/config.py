"""Deprecated shim: use :mod:`wskr.core.config`."""

from __future__ import annotations

import warnings as _w

from wskr.core.config import *  # noqa: F403

_w.warn("wskr.config is deprecated; import from wskr.core.config", DeprecationWarning, stacklevel=2)
