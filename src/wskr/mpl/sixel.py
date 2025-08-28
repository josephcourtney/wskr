from __future__ import annotations

from matplotlib import _api
from matplotlib.backend_bases import _Backend
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.mpl.base import TerminalBackend


class _SixelCanvas(FigureCanvasAgg):
    manager_class = _api.classproperty(lambda _: None)


@_Backend.export
class _BackendSixelAgg(TerminalBackend):
    not_impl_msg = "Sixel backend not implemented in this release"
    FigureCanvas = _SixelCanvas
    FigureManager = None
