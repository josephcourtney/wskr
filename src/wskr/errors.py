"""Deprecated shim: use :mod:`wskr.core.errors`."""

import warnings as _w

from wskr.core.errors import *  # noqa: F403

_w.warn("wskr.errors is deprecated; import from wskr.core.errors", DeprecationWarning, stacklevel=2)
