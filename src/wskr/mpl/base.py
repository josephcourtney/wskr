import os
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from io import BytesIO
from typing import Any

import matplotlib as mpl
from matplotlib import _api, interactive, is_interactive  # noqa: PLC2701
from matplotlib._pylab_helpers import Gcf  # noqa: PLC2701
from matplotlib.backend_bases import FigureManagerBase, _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.mpl.size import autosize_figure
from wskr.tty.base import ImageTransport
from wskr.tty.registry import get_image_transport

if sys.flags.interactive:
    interactive(b=True)


def render_figure_to_terminal(canvas: FigureCanvasAgg, transport: ImageTransport) -> None:
    """Resize and render a Matplotlib figure to the terminal using a given transport."""
    width_px, height_px = transport.get_window_size_px()
    try:
        scale = float(os.getenv("WSKR_SCALE", "1.0"))
    except ValueError:
        scale = 1.0
    width_px = int(width_px * scale)
    height_px = int(height_px * scale)

    autosize_figure(canvas.figure, width_px, height_px)

    buf = BytesIO()
    canvas.print_png(buf)
    buf.seek(0)
    transport.send_image(buf.read())


class WskrFigureManager(FigureManagerBase):
    def __init__(
        self,
        canvas: FigureCanvasAgg,
        num: int = 1,
        transport_factory: Callable[[], ImageTransport] | None = None,
    ) -> None:
        super().__init__(canvas, num)
        factory = transport_factory or get_image_transport
        self.transport = factory()

    def show(self, *_args: Any, **_kwargs: Any) -> None:
        render_figure_to_terminal(self.canvas, self.transport)


class WskrFigureCanvas(FigureCanvasAgg):
    manager_class: Any = _api.classproperty(lambda _: WskrFigureManager)

    @contextmanager
    def _guard_draw(self) -> Iterator[bool]:
        """Context manager preventing re-entrant ``draw`` calls.

        Matplotlib can trigger recursive ``draw`` invocations via stale
        callbacks.  Guarding with a context manager keeps the logic
        contained and ensures the flag is always reset even if ``draw``
        raises an exception.
        """
        if getattr(self, "_in_draw", False):
            yield False
            return
        self._in_draw = True
        try:
            yield True
        finally:
            self._in_draw = False

    def draw(self) -> None:
        """Render the figure and display it if interactive.

        ``_guard_draw`` ensures we do not recurse if ``draw`` is invoked
        again while already active.
        """
        with self._guard_draw() as do_draw:
            if not do_draw:
                return
            super().draw()
            if is_interactive() and self.figure.get_axes():
                self.manager.show()

    draw_idle = draw


class BaseFigureManager(FigureManagerBase):
    """Minimal backend manager parameterized by transport class."""

    def __init__(
        self,
        canvas: FigureCanvasAgg,
        num: int,
        transport_cls: type[ImageTransport],
    ) -> None:
        super().__init__(canvas, num)
        self.transport = transport_cls()

    def show(self, *_args: Any, **_kwargs: Any) -> None:
        render_figure_to_terminal(self.canvas, self.transport)


class TerminalBackend(_Backend):
    """Generic Matplotlib backend for terminal-image protocols."""

    not_impl_msg: str | None = None

    @classmethod
    def draw_if_interactive(cls):
        manager = Gcf.get_active()
        if mpl.is_interactive() and manager and manager.canvas.figure.get_axes():
            cls.show()

    @classmethod
    def show(cls, *args: Any, **kwargs: Any) -> None:
        if cls.not_impl_msg is not None:
            raise NotImplementedError(cls.not_impl_msg)
        manager = Gcf.get_active()
        if manager:
            manager.show(*args, **kwargs)
            Gcf.destroy_all()


FigureCanvas = WskrFigureCanvas
FigureManager = WskrFigureManager


@_Backend.export
class _BackendTermAgg(TerminalBackend):
    FigureCanvas = WskrFigureCanvas
    FigureManager = WskrFigureManager
