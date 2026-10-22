import math
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
from matplotlib.figure import Figure
from PIL import Image

from wskr.protocol import ImageProtocol, get_image_protocol
from wskr.render.matplotlib.figure import TerminalFigure
from wskr.render.matplotlib.theme import resolve_rc_defaults
from wskr.terminal import TerminalCapabilities, probe_profile

_MAX_DISPLAY_SCALE = 8.0

if sys.flags.interactive:
    interactive(b=True)


def render_figure_to_terminal(
    canvas: FigureCanvasAgg,
    transport: ImageProtocol,
    caps: TerminalCapabilities | None = None,  # ruff: ignore[unused-function-argument] - compatibility
) -> None:
    """Rasterize the caller's figure without changing its size or DPI.

    Matplotlib owns figure and artist geometry. A window manager (including
    yabai) may change the attached terminal between figure construction and
    display; that alone is not permission to overwrite the figure's explicit
    size. Figure-creation defaults are resolved separately by TerminalBackend.

    The caps argument is retained for compatibility; viewport-driven
    placement and resize notifications belong to later Phase 3 work.
    """
    buf = BytesIO()
    canvas.print_png(buf)
    png = buf.getvalue()
    # An explicit display scale changes only the transmitted raster. In
    # particular, it must not resize artists or alter ordinary savefig output.
    try:
        scale = float(os.getenv("WSKR_SCALE", "1.0"))
    except ValueError:
        scale = 1.0
    if math.isfinite(scale) and 0 < scale <= _MAX_DISPLAY_SCALE and scale != 1:
        with Image.open(BytesIO(png)) as original:
            width, height = original.size
            new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
            image = original.resize(new_size, Image.Resampling.LANCZOS)
            result = BytesIO()
            image.save(result, format="PNG")
            png = result.getvalue()
    transport.send_image(png)


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

    def destroy(self) -> None:
        """Release this manager's transport without closing other figures."""
        self.transport.close()


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

    def destroy(self) -> None:
        """Release only the images owned by this figure's transport."""
        self.transport.close()


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
        if kwargs.get("FigureClass", Figure) is not Figure:
            # A custom Figure class may implement its own sizing/style policy.
            return super().new_figure_manager(num, *args, **kwargs)

        user_dpi = kwargs.get("dpi")
        dpi = float(mpl.rcParams["figure.dpi"] if user_dpi is None else user_dpi)
        defaults = resolve_rc_defaults(probe_profile(), dpi=dpi)
        # Iterating rcParams gives Matplotlib's statically valid configuration
        # keys. An arbitrary string returned by the resolver is not such a key.
        backend_owned = {
            key: defaults[key]
            for key in mpl.rcParams
            if key in defaults and mpl.rcParams[key] == mpl.rcParamsDefault[key]
        }

        # pyplot always supplies FigureClass=Figure and figsize=None. None
        # means unspecified; only non-None arguments are user-owned.
        for rc_key, argument in (("figure.figsize", "figsize"), ("figure.facecolor", "facecolor")):
            if kwargs.get(argument) is None and rc_key in backend_owned:
                kwargs[argument] = backend_owned[rc_key]

        # Do not replace a user-selected Figure subclass. Only the stock Figure
        # receives figure-local defaults, scoped to creation of subsequent axes.
        if kwargs.get("FigureClass", Figure) is Figure:
            artist_defaults = {
                key: value
                for key, value in backend_owned.items()
                if key not in {"figure.figsize", "figure.dpi", "figure.facecolor"}
            }
            if artist_defaults:
                kwargs["FigureClass"] = TerminalFigure
                kwargs["_wskr_defaults"] = artist_defaults
        return super().new_figure_manager(num, *args, **kwargs)

    @classmethod
    def draw_if_interactive(cls):
        manager = Gcf.get_active()
        if mpl.is_interactive() and manager and manager.canvas.figure.get_axes():
            manager.show()

    @classmethod
    def show(cls, *args: Any, **kwargs: Any) -> None:
        if cls.not_impl_msg is not None:
            raise NotImplementedError(cls.not_impl_msg)
        # Standard pyplot show presents every registered figure. Display must
        # not dispose of figures, transports, or the caller's plot state.
        for manager in Gcf.get_all_fig_managers():
            manager.show(*args, **kwargs)


FigureCanvas = WskrFigureCanvas
FigureManager = WskrFigureManager


@_Backend.export
class _BackendTermAgg(TerminalBackend):
    FigureCanvas = WskrFigureCanvas
    FigureManager = WskrFigureManager
