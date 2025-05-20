import sys

import matplotlib.pyplot as plt
from matplotlib import _api, interactive  # noqa: PLC2701
from matplotlib.backend_bases import _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.mpl.base import BaseFigureManager, TerminalBackend
from wskr.mpl.utils import detect_dark_mode
from wskr.tty.kitty import KittyTransport

if detect_dark_mode():
    plt.style.use("dark_background")


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
