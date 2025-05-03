import sys
from io import BytesIO
from typing import Any

import matplotlib.pyplot as plt
from matplotlib import _api, interactive, is_interactive  # noqa: PLC2701
from matplotlib._pylab_helpers import Gcf  # noqa: PLC2701
from matplotlib.backend_bases import FigureManagerBase, _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.tty.base import ImageTransport as BaseTransport
from wskr.tty.transport import KittyTransport

plt.style.use("dark_background")

# heuristic for interactive repl
if sys.flags.interactive:
    interactive(True)  # noqa: FBT003


class KittyFigureManager(FigureManagerBase):
    """Kitty-protocol figure manager."""

    def __init__(
        self,
        canvas: FigureCanvasAgg,
        num: int = 1,
        transport: BaseTransport | None = None,
    ) -> None:
        super().__init__(canvas, num)
        self.transport = transport or KittyTransport()

    def show(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        width_px, height_px = self.transport.get_window_size_px()
        dpi = self.canvas.figure.dpi
        orig_w, orig_h = self.canvas.figure.get_size_inches()
        aspect = orig_h / orig_w if orig_w else 1.0

        if aspect > 1:
            new_h = height_px / dpi
            new_w = new_h / aspect
        else:
            new_w = width_px / dpi
            new_h = new_w * aspect

        self.canvas.figure.set_size_inches(new_w, new_h)

        buf = BytesIO()
        self.canvas.print_png(buf)
        buf.seek(0)
        self.transport.send_image(buf.read())


class KittyFigureCanvas(FigureCanvasAgg):
    manager_class = _api.classproperty(lambda _: KittyFigureManager)


@_Backend.export
class _BackendKittyAgg(_Backend):
    """Matplotlib backend entry-point for kitty protocol."""

    FigureCanvas = KittyFigureCanvas
    FigureManager = KittyFigureManager

    @classmethod
    def draw_if_interactive(cls):
        manager = Gcf.get_active()
        if is_interactive() and manager and manager.canvas.figure.get_axes():
            cls.show()

    @classmethod
    def show(cls, *args, **kwargs):
        manager = Gcf.get_active()
        if manager:
            manager.show(*args, **kwargs)
            Gcf.destroy_all()
