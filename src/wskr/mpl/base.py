"""Deprecated shim: use :mod:`wskr.render.matplotlib.core`."""

from __future__ import annotations

import warnings as _w

from wskr.render.matplotlib.core import (
    BaseFigureManager,
    FigureCanvas,
    FigureManager,
    TerminalBackend,
    WskrFigureCanvas,
    WskrFigureManager,
    _BackendTermAgg,
    render_figure_to_terminal,
)

_w.warn("wskr.mpl.base is deprecated; use wskr.render.matplotlib.core", DeprecationWarning, stacklevel=2)

__all__ = [
    "BaseFigureManager",
    "FigureCanvas",
    "FigureManager",
    "TerminalBackend",
    "WskrFigureCanvas",
    "WskrFigureManager",
    "_BackendTermAgg",
    "render_figure_to_terminal",
]
