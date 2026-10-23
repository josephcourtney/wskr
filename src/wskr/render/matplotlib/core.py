from __future__ import annotations

import atexit
import math
import os
import select
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from io import BytesIO
from time import monotonic
from typing import Any

import matplotlib as mpl
from matplotlib import _api, interactive, is_interactive  # ruff: ignore[import-private-name]
from matplotlib._pylab_helpers import Gcf  # ruff: ignore[import-private-name]
from matplotlib.backend_bases import FigureManagerBase, _Backend  # ruff: ignore[import-private-name]
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from wskr.core.errors import TransportUnavailableError
from wskr.protocol import ImageProtocol, get_image_protocol
from wskr.render.matplotlib.figure import TerminalFigure
from wskr.render.matplotlib.sheet import SheetPages, contact_sheet, plan_sheet_pages
from wskr.render.matplotlib.theme import resolve_rc_defaults
from wskr.terminal import TerminalCapabilities, probe_profile
from wskr.terminal.profile import Geometry, read_geometry

_MAX_DISPLAY_SCALE = 8.0
_RESIZE_POLL_SECONDS = 0.1
_RESIZE_QUIET_SECONDS = 0.2
_BLOCKING_PROMPT = "wskr: press Enter to close displayed figures: "
_MIN_SHEET_MANAGERS = 2
_LONG_PAGE_PROMPT_COLS = 51
_EXIT_STATE = {"exiting": False}


def _mark_process_exit() -> None:
    """Distinguish Matplotlib's atexit cleanup from an explicit plt.close."""
    _EXIT_STATE["exiting"] = True


# Matplotlib registers Gcf.destroy_all when _pylab_helpers is imported above.
# Exit callbacks execute in reverse order, so mark the shutdown first.
atexit.register(_mark_process_exit)


def _close_owned_transport(transport: ImageProtocol, *, static_output: bool) -> None:
    """On shutdown, retain static output; explicit close always deletes it."""
    if _EXIT_STATE["exiting"] and static_output:
        transport.retain_display()
    transport.close()


if sys.flags.interactive:
    interactive(b=True)


def _owns_foreground_terminal_input() -> bool:
    """Allow an explicit blocking show only with foreground TTY input.

    In REPLs, notebooks, pipes, and background jobs, terminal input may be
    managed by another component. Never consume its bytes opportunistically.
    """
    if sys.stdin is None or sys.stdout is None:
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    try:
        input_fd = sys.stdin.fileno()
        output_fd = sys.stdout.fileno()
        return os.ttyname(input_fd) == os.ttyname(output_fd) and os.tcgetpgrp(input_fd) == os.getpgrp()
    except (OSError, ValueError):
        return False


@contextmanager
def _temporary_terminal_screen() -> Generator[None]:
    """Isolate explicitly blocking graphics from the shell's scrollback.

    Kitty's alternate-screen buffer is restored on exit. Deleting a graphics
    placement alone removes its pixels, but cannot retract the terminal rows
    underneath it; the alternate screen avoids leaving those empty rows in
    the shell's primary screen. Never use this for nonblocking output.
    """
    output = sys.stdout
    if output is None:
        msg = "Cannot enter temporary screen without TTY stdout"
        raise RuntimeError(msg)
    output.flush()
    fd = output.fileno()
    os.write(fd, b"\x1b[?1049h")
    try:
        yield
    finally:
        try:
            output.flush()
        finally:
            # Even a failed buffered-output flush must not trap the caller
            # inside Kitty's alternate screen.
            os.write(fd, b"\x1b[?1049l")


def _display_scale() -> float:
    """Read the existing finite/bounded display-scale override."""
    try:
        scale = float(os.getenv("WSKR_SCALE", "1.0"))
    except ValueError:
        return 1.0
    return scale if math.isfinite(scale) and 0 < scale <= _MAX_DISPLAY_SCALE else 1.0


def _sheet_for_managers(
    managers: list[FigureManagerBase], geometry: Geometry | None
) -> tuple[list[WskrFigureManager | BaseFigureManager], list[FigureCanvasAgg], SheetPages] | None:
    """Identify the bounded contact-sheet case without claiming other figures."""
    if (
        len(managers) < _MIN_SHEET_MANAGERS
        or geometry is None
        or os.getenv("WSKR_FIT", "").lower() != "contain"
        or is_interactive()
    ):
        return None
    owned = [manager for manager in managers if isinstance(manager, (WskrFigureManager, BaseFigureManager))]
    if len(owned) != len(managers):
        return None
    canvases = [canvas for manager in owned if isinstance(canvas := manager.canvas, FigureCanvasAgg)]
    if len(canvases) != len(owned):
        return None
    try:
        plan = plan_sheet_pages(len(canvases), geometry)
    except ValueError:
        return None
    return owned, canvases, plan


def _show_blocking_managers(
    managers: list[FigureManagerBase], geometry: Geometry | None, *, page_index: int = 0
) -> SheetPages | None:
    """Render one fitted page as a single scoped image, or use legacy show."""
    selection = _sheet_for_managers(managers, geometry)
    if selection is not None and geometry is not None:
        owned, canvases, plan = selection
        subset = canvases[plan.page_slice(page_index)]
        try:
            png = contact_sheet(subset, geometry, scale=_display_scale(), columns=plan.columns)
        except ValueError:
            pass  # No usable measured pixels: preserve the original fallback.
        else:
            owned[0].transport.send_image(png)
            output = sys.stdout
            if output is not None:
                output.flush()
                os.write(output.fileno(), f"\x1b[{geometry.rows};1H".encode())
            return plan
    for manager in managers:
        manager.show()
    return None


def _page_prompt(plan: SheetPages | None, index: int, geometry: Geometry | None) -> str:
    if plan is None or plan.total_pages <= 1:
        return _BLOCKING_PROMPT
    page = min(index, plan.total_pages - 1) + 1
    width = geometry.columns if geometry is not None else 80
    choices = (
        f"Page {page}/{plan.total_pages}: n/p + Enter, blank closes: "
        if width >= _LONG_PAGE_PROMPT_COLS
        else f"{page}/{plan.total_pages} n/p, Enter closes: "
    )
    return choices if len(choices) < width else f"{page}/{plan.total_pages}> "


def _redraw_foreground_figures(managers: list[FigureManagerBase], *, page_index: int = 0) -> SheetPages | None:
    """Repaint the owned alternate screen and its selected page after resize."""
    output = sys.stdout
    if output is None:
        msg = "Blocking resize redraw requires TTY stdout"
        raise RuntimeError(msg)
    output.flush()
    os.write(output.fileno(), b"\x1b[H\x1b[2J")
    geometry = read_geometry()
    plan = _show_blocking_managers(managers, geometry, page_index=page_index)
    print(_page_prompt(plan, page_index, geometry), end="", flush=True)
    return plan


def _wait_for_foreground_resize(managers: list[FigureManagerBase], start: Geometry | None) -> None:
    """Own canonical input; navigate fitted pages and debounce resize changes.

    A navigation command is a *completed line* (n/p followed by Enter);
    bare Enter closes. No raw keyboard mode, signal handlers, or foreign
    REPL input are touched. Resizing can change page capacity and clamps
    the selection to the last valid page before repainting.
    """
    input_stream = sys.stdin
    if input_stream is None:
        msg = "Blocking resize session requires TTY stdin"
        raise RuntimeError(msg)
    fd = input_stream.fileno()
    current = start
    pending: Geometry | None = None
    pending_since = 0.0
    index = 0
    selection = _sheet_for_managers(managers, start)
    plan = selection[2] if selection is not None else None
    print(_page_prompt(plan, index, current), end="", flush=True)

    while True:
        readable, _, _ = select.select([fd], [], [], _RESIZE_POLL_SECONDS)
        if readable:
            line = input()
            command = line.strip().lower() if isinstance(line, str) else ""
            if command in {"", "q"}:
                return
            if plan is not None and plan.total_pages > 1 and command in {"n", "p"}:
                offset = 1 if command == "n" else -1
                index = (index + offset) % plan.total_pages
                _redraw_foreground_figures(managers, page_index=index)
            else:
                print(_page_prompt(plan, index, current), end="", flush=True)
            continue

        observed = read_geometry()
        if observed is None or observed == current:
            pending = None
            continue
        if observed != pending:
            pending = observed
            pending_since = monotonic()
            continue
        if monotonic() - pending_since < _RESIZE_QUIET_SECONDS:
            continue

        selection = _sheet_for_managers(managers, observed)
        plan = selection[2] if selection is not None else None
        index = min(index, plan.total_pages - 1) if plan is not None else 0
        if plan is None:
            _redraw_foreground_figures(managers)
        else:
            _redraw_foreground_figures(managers, page_index=index)
        current = observed
        pending = None


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

    An explicit WSKR_FIT=contain opt-in reads pixel geometry at each display
    to contain the transmitted PNG without changing the figure. Automatic
    resize-triggered redraw and placement changes belong to later Phase 3 work.
    The caps argument is retained for compatibility.
    """
    buf = BytesIO()
    canvas.print_png(buf)
    png = buf.getvalue()
    # The display-only controls never touch Figure geometry, axes or savefig.
    # Explicit WSKR_SCALE is applied before optional containment; WSKR_FIT
    # requires actual attached-terminal pixel measurements, never guessed DPI.
    scale = _display_scale()

    if os.getenv("WSKR_FIT", "").lower() == "contain":
        try:
            viewport_w, viewport_h = transport.get_window_size_px()
        except (OSError, TransportUnavailableError):
            viewport_w, viewport_h = 0, 0
        if viewport_w > 0 and viewport_h > 0:
            source_w, source_h = canvas.get_width_height()
            if source_w > 0 and source_h > 0:
                scale = min(scale, viewport_w / source_w, viewport_h / source_h)

    if scale != 1:
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
        self._last_output_static = False

    def show(self, *_args: Any, **_kwargs: Any) -> None:
        canvas = self.canvas
        if not isinstance(canvas, FigureCanvasAgg):
            msg = "wskr requires an Agg canvas for terminal rendering"
            raise TypeError(msg)
        render_figure_to_terminal(canvas, self.transport, self.caps)
        self._last_output_static = not is_interactive()

    def destroy(self) -> None:
        """Retain ordinary output at exit; otherwise release owned images."""
        _close_owned_transport(self.transport, static_output=self._last_output_static)


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
        self._last_output_static = False

    def show(self, *_args: Any, **_kwargs: Any) -> None:
        canvas = self.canvas
        if not isinstance(canvas, FigureCanvasAgg):
            msg = "wskr requires an Agg canvas for terminal rendering"
            raise TypeError(msg)
        render_figure_to_terminal(canvas, self.transport, self.caps)
        self._last_output_static = not is_interactive()

    def destroy(self) -> None:
        """Retain ordinary output at exit; clean up explicit/interactively."""
        _close_owned_transport(self.transport, static_output=self._last_output_static)


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
    def show(cls, *, block: bool | None = None) -> None:
        """Display every figure; wait for Enter only if explicitly requested.

        Kitty images live in terminal history, not separate GUI windows.
        Therefore the ordinary show(block=None) is intentionally nonblocking
        so static output survives the script's exit. A caller opting into
        block=True owns its foreground input for the duration of the prompt.
        """
        if cls.not_impl_msg is not None:
            raise NotImplementedError(cls.not_impl_msg)
        managers = Gcf.get_all_fig_managers()
        if not managers:
            return
        if block is True and not _owns_foreground_terminal_input():
            msg = "Blocking terminal show requires foreground stdin and stdout on the same TTY"
            raise RuntimeError(msg)

        if block is True:
            # The entire plot session, including its cleanup, belongs to the
            # alternate screen. On return the shell regains its original text
            # and cursor instead of a hole where the image used to be.
            with _temporary_terminal_screen():
                try:
                    initial_geometry = read_geometry() if os.getenv("WSKR_FIT", "").lower() == "contain" else None
                    _show_blocking_managers(managers, initial_geometry)
                    if os.getenv("WSKR_FIT", "").lower() == "contain":
                        _wait_for_foreground_resize(managers, initial_geometry)
                    else:
                        input(_BLOCKING_PROMPT)
                finally:
                    Gcf.destroy_all()
        else:
            for manager in managers:
                manager.show()


FigureCanvas = WskrFigureCanvas
FigureManager = WskrFigureManager


@_Backend.export
class _BackendTermAgg(TerminalBackend):
    FigureCanvas = WskrFigureCanvas
    FigureManager = WskrFigureManager
