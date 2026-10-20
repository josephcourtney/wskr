import sys

from matplotlib import _api, interactive  # ruff: ignore[import-private-name]
from matplotlib.backend_bases import _Backend  # ruff: ignore[import-private-name]
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.protocol.kitty import KittyTransport
from wskr.render.matplotlib.core import BaseFigureManager, TerminalBackend
from wskr.terminal.kitty.capabilities import KittyCapabilities

if sys.flags.interactive:
    interactive(b=True)


class KittyFigureManager(BaseFigureManager):
    def __init__(self, canvas: FigureCanvasAgg, num: int = 1):
        super().__init__(canvas, num, KittyTransport, caps=KittyCapabilities())


class KittyFigureCanvas(FigureCanvasAgg):
    manager_class = _api.classproperty(lambda _: KittyFigureManager)


@_Backend.export
class _BackendKittyAgg(TerminalBackend):
    FigureCanvas = KittyFigureCanvas
    FigureManager = KittyFigureManager
