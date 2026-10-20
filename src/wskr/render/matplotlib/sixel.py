from __future__ import annotations

import os

from matplotlib import _api  # ruff: ignore[import-private-name]
from matplotlib.backend_bases import FigureManagerBase, _Backend  # ruff: ignore[import-private-name]
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.core.errors import FeatureUnavailableError

from .core import TerminalBackend

if os.getenv("WSKR_ENABLE_SIXEL", "").lower() != "true":
    msg = "Sixel backend is not yet implemented. Set WSKR_ENABLE_SIXEL=true to bypass."
    raise FeatureUnavailableError(msg)


class _SixelCanvas(FigureCanvasAgg):
    manager_class = _api.classproperty(lambda _: None)


@_Backend.export
class _BackendSixelAgg(TerminalBackend):
    not_impl_msg = "Sixel backend not yet implemented"
    FigureCanvas = _SixelCanvas
    FigureManager = FigureManagerBase


__all__ = ["_BackendSixelAgg"]
