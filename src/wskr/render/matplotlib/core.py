import os
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from io import BytesIO
from typing import Any

import matplotlib as mpl
from matplotlib import _api, interactive, is_interactive  # ruff: ignore[import-private-name]
from matplotlib._pylab_helpers import Gcf  # ruff: ignore[import-private-name]
from matplotlib.backend_bases import FigureManagerBase, _Backend  # ruff: ignore[import-private-name]
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.protocol import ImageProtocol, get_image_protocol
from wskr.render.matplotlib.size import autosize_figure
from wskr.render.matplotlib.theme import resolve_rc_defaults
from wskr.terminal import TerminalCapabilities, probe_profile

if sys.flags.interactive:
    interactive(b=True)


def render_figure_to_terminal(
    canvas: FigureCanvasAgg,
    transport: ImageProtocol,
    caps: TerminalCapabilities | None = None,
) -> None:
    """Resize and render a Matplotlib figure to the terminal using a given transport.

    If ``caps`` is provided, use it to determine the drawable viewport; otherwise
    ask the transport for the window size.
    """
    if caps is not None:
        width_px, height_px = caps.window_px()
    else:
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
        transport_factory: Callable[[], ImageProtocol] | None = None,
        caps_factory: Callable[[], TerminalCapabilities] | None = None,
    ) -> None:
        super().__init__(canvas, num)
        factory = transport_factory or get_image_protocol
        self.transport = factory()
        self.caps = caps_factory() if caps_factory is not None else None

    def show(self, *_args: Any, **_kwargs: Any) -> None:
        canvas = self.canvas
        if not isinstance(canvas, FigureCanvasAgg):
            msg = "wskr requires an Agg canvas for terminal rendering"
            raise TypeError(msg)
        render_figure_to_terminal(canvas, self.transport, self.caps)


class WskrFigureCanvas(FigureCanvasAgg):
    manager_class: Any = _api.classproperty(lambda _: WskrFigureManager)

    @contextmanager
    def _guard_draw(self) -> Generator[bool]:
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
            if is_interactive() and self.figure.get_axes() and self.manager is not None:
                self.manager.show()

    draw_idle = draw


class BaseFigureManager(FigureManagerBase):
    """Minimal backend manager parameterized by transport class."""

    def __init__(
        self,
        canvas: FigureCanvasAgg,
        num: int,
        transport_cls: type[ImageProtocol],
        caps: TerminalCapabilities | None = None,
    ) -> None:
        super().__init__(canvas, num)
        self.transport = transport_cls()
        self.caps = caps

    def show(self, *_args: Any, **_kwargs: Any) -> None:
        canvas = self.canvas
        if not isinstance(canvas, FigureCanvasAgg):
            msg = "wskr requires an Agg canvas for terminal rendering"
            raise TypeError(msg)
        render_figure_to_terminal(canvas, self.transport, self.caps)


class TerminalBackend(_Backend):
    """Generic Matplotlib backend for terminal-image protocols."""

    not_impl_msg: str | None = None

    @classmethod
    def new_figure_manager(cls, num: int, *args: Any, **kwargs: Any) -> FigureManagerBase:
        """Choose backend-owned new-figure defaults without changing global rcParams.

        An explicit figsize/facecolor or nondefault rcParams value wins. Kernel
        geometry is non-interactive; colors remain unknown without safe, owned
        terminal interrogation.
        """
        kwargs = dict(kwargs)
        if "figsize" not in kwargs or "facecolor" not in kwargs:
            user_dpi = kwargs.get("dpi")
            dpi = float(mpl.rcParams["figure.dpi"] if user_dpi is None else user_dpi)
            defaults = resolve_rc_defaults(probe_profile(), dpi=dpi)
            for rc_key, argument in (("figure.figsize", "figsize"), ("figure.facecolor", "facecolor")):
                if argument in kwargs:
                    continue
                if mpl.rcParams[rc_key] != mpl.rcParamsDefault[rc_key]:
                    continue
                if rc_key in defaults:
                    kwargs[argument] = defaults[rc_key]
        return super().new_figure_manager(num, *args, **kwargs)

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
