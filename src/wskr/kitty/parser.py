"""Deprecated shim: use :mod:`wskr.protocol.kgp.parser`."""

from __future__ import annotations

import warnings as _w

from wskr.protocol.kgp.parser import KittyChunkParser

_w.warn("wskr.kitty.parser is deprecated; use wskr.protocol.kgp.parser", DeprecationWarning, stacklevel=2)

__all__ = ["KittyChunkParser"]
