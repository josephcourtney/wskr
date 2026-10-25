"""Explicit foreground-owned Kitty viewport for live Matplotlib updates.

Use when an application intentionally owns a terminal screen for a bounded
session. Unlike ordinary nonblocking pyplot output, this mode intentionally
enters the alternate screen and positions each frame in the visible viewport.
It must not be used from a REPL whose input/output is owned by another party.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from threading import Lock
from time import monotonic
from typing import TYPE_CHECKING

from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.protocol.kitty_native import NativeKittyTransport
from wskr.render.matplotlib import core
from wskr.terminal.profile import Geometry, read_geometry

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from matplotlib.figure import Figure

    from wskr.protocol.base import ImageProtocol


_OWNER_LOCK = Lock()
_RESIZE_QUIET_SECONDS = 0.2


class LiveViewport:
    """An active exclusive alternate-screen rendering session.

    The context manager creates and closes this object. Call `refresh()`
    after changing Figure artists and `poll_resize()` from the application's
    own event loop. Neither method reads stdin or starts background work.
    """

    def __init__(self, figure: Figure, transport: ImageProtocol) -> None:
        self._figure = figure
        self._transport = transport
        self._active = True
        self._displayed: Geometry | None = None
        self._pending: Geometry | None = None
        self._pending_since = 0.0

    def _require_active(self) -> None:
        if not self._active:
            msg = "Live viewport session has ended"
            raise RuntimeError(msg)

    def refresh(self) -> None:
        """Redraw at the viewport origin without changing Figure geometry."""
        self._require_active()
        output = sys.stdout
        if output is None:
            msg = "Live viewport lost its terminal output"
            raise RuntimeError(msg)
        canvas = self._figure.canvas
        if not isinstance(canvas, FigureCanvasAgg):
            msg = "Live viewport requires an Agg Figure canvas"
            raise TypeError(msg)
        output.flush()
        os.write(output.fileno(), b"\x1b[H\x1b[2J")
        core.render_figure_to_terminal(canvas, self._transport)
        self._displayed = read_geometry()
        self._pending = None

    def poll_resize(self) -> bool:
        """Refresh once after a stable, measured geometry change."""
        self._require_active()
        geometry = read_geometry()
        if geometry is None or min(geometry.width_px, geometry.height_px) <= 0:
            self._pending = None
            return False
        if geometry == self._displayed:
            self._pending = None
            return False
        if geometry != self._pending:
            self._pending = geometry
            self._pending_since = monotonic()
            return False
        if monotonic() - self._pending_since < _RESIZE_QUIET_SECONDS:
            return False
        self.refresh()
        return True

    def _finish(self) -> None:
        if not self._active:
            return
        self._active = False
        self._transport.close()


@contextmanager
def owned_viewport(
    figure: Figure,
    *,
    transport_factory: Callable[[], ImageProtocol] | None = None,
) -> Generator[LiveViewport]:
    """Own Kitty's alternate screen, redraw live, then restore shell history.

    Requires foreground stdin/stdout on the *same* terminal and
    `WSKR_FIT=contain`. Fails closed for redirected/background sessions,
    concurrent owners and non-Agg Figures. Does not take over foreign REPL
    input, read stdin, change user Figure dimensions, or retain images after
    the owned session ends. Normal pyplot history output is unchanged.
    """
    if not core._owns_foreground_terminal_input():  # ruff: ignore[private-member-access] - shared ownership gate
        msg = "Live viewport requires foreground stdin and stdout on the same TTY"
        raise RuntimeError(msg)
    if os.getenv("WSKR_FIT", "").lower() != "contain":
        msg = "Live viewport requires WSKR_FIT=contain"
        raise RuntimeError(msg)
    if not isinstance(figure.canvas, FigureCanvasAgg):
        msg = "Live viewport requires an Agg Figure canvas"
        raise TypeError(msg)
    if not _OWNER_LOCK.acquire(blocking=False):
        msg = "A live viewport already owns this process's terminal graphics"
        raise RuntimeError(msg)
    token = core._BLOCKING_RENDER.set(True)  # ruff: ignore[private-member-access] - suppress history redraw
    try:
        factory = transport_factory or NativeKittyTransport
        transport = factory()
        session = LiveViewport(figure, transport)
        try:
            with core._temporary_terminal_screen():  # ruff: ignore[private-member-access] - scoped screen
                session.refresh()
                yield session
        finally:
            session._finish()  # ruff: ignore[private-member-access] - only owner closes
    finally:
        core._BLOCKING_RENDER.reset(token)  # ruff: ignore[private-member-access] - restore token
        _OWNER_LOCK.release()
