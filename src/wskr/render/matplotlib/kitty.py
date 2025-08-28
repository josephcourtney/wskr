import sys

from matplotlib import _api, interactive  # noqa: PLC2701
from matplotlib.backend_bases import _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.protocol.kgp.kgp import KittyTransport
from wskr.render.matplotlib.core import BaseFigureManager, TerminalBackend

if sys.flags.interactive:
    interactive(b=True)


class KittyFigureManager(BaseFigureManager):
    def __init__(self, canvas: FigureCanvasAgg, num: int = 1):
        super().__init__(canvas, num, KittyTransport)


class KittyFigureCanvas(FigureCanvasAgg):
    manager_class = _api.classproperty(lambda _: KittyFigureManager)


@_Backend.export
class _BackendKittyAgg(TerminalBackend):
    FigureCanvas = KittyFigureCanvas
    FigureManager = KittyFigureManager
