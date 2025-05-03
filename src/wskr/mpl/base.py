import sys
from io import BytesIO
from typing import Any

import matplotlib.pyplot as plt
from matplotlib import _api, interactive, is_interactive  # noqa: PLC2701
from matplotlib._pylab_helpers import Gcf  # noqa: PLC2701
from matplotlib.backend_bases import FigureManagerBase, _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.tty.base import ImageTransport as BaseTransport
from wskr.tty.transport import get_image_transport  # <— pluggable factory

plt.style.use("dark_background")

# heuristic for interactive repl
if sys.flags.interactive:
    interactive(True)  # noqa: FBT003


class WskrFigureManager(FigureManagerBase):
    """
    Generic terminal-image figure manager.

    If no transport is passed in, we pull one from the registry (default: kitty).
    """

    def __init__(
        self,
        canvas: FigureCanvasAgg,
        num: int = 1,
        transport: BaseTransport | None = None,
    ) -> None:
        super().__init__(canvas, num)
        # inject default transport if none supplied
        self.transport = transport or get_image_transport()

    def show(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        """Display the plot.

        1) Query the transport for the terminal's pixel-width/height
        2) Resize the Matplotlib figure (in inches) to *fill* that viewport
           (but preserve aspect ratio, and respect user-set fig sizes).
        3) Render to PNG and hand off to the transport.
        """
        # 1) window size in pixels
        width_px, height_px = self.transport.get_window_size_px()
        # 2. Compute new figure size in inches
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

        # 3. Render and send
        buffer = BytesIO()
        self.canvas.print_png(buffer)
        buffer.seek(0)
        self.transport.send_image(buffer.read())


class WskrFigureCanvas(FigureCanvasAgg):
    manager_class: Any = _api.classproperty(lambda _: WskrFigureManager)

    def draw(self) -> None:
        """Override Agg.draw so that in interactive mode we immediately show the new image in the terminal."""
        super().draw()
        # only if there's at least one axis to render…
        if is_interactive() and self.figure.get_axes():
            # self.manager was set by new_manager()
            self.manager.show()

    # ensure draw_idle (called by pyplot in interactive) also triggers draw()
    draw_idle = draw


@_Backend.export
class _BackendTermAgg(_Backend):
    """Function-based API fallback.  If someone does `module://wskr.mpl.base`."""

    FigureCanvas = WskrFigureCanvas
    FigureManager = WskrFigureManager

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


# For Matplotlib's entry-point / Canvas-based API:
FigureCanvas = WskrFigureCanvas
FigureManager = WskrFigureManager
