"""Deprecated shim: use :mod:`wskr.protocol.kgp.kgp`."""

from __future__ import annotations

import warnings as _w

from wskr.protocol.kgp.kgp import KittyPyTransport, KittyTransport

_w.warn("wskr.kitty.transport is deprecated; use wskr.protocol.kgp.kgp", DeprecationWarning, stacklevel=2)

__all__ = ["KittyPyTransport", "KittyTransport"]
