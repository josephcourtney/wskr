"""Optional IPython event-pump integration for the terminal Matplotlib backend.

Load explicitly with `%load_ext wskr.render.matplotlib.ipython`. The host
continues to own stdin and its event loop; after each completed cell this
extension gives any registered wskr canvas a single opportunity to drain
coalesced redraw and stable-resize events. Nothing is scheduled in background.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from matplotlib._pylab_helpers import Gcf  # ruff: ignore[import-private-name]

from wskr.render.matplotlib.core import WskrFigureCanvas

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

_callbacks: WeakKeyDictionary[Any, Callable[..., None]] = WeakKeyDictionary()


def _pump_after_cell(_result: object = None) -> None:
    """Pump through one canvas; its backend event pump drains all wskr managers."""
    for manager in Gcf.get_all_fig_managers():
        canvas = manager.canvas
        if isinstance(canvas, WskrFigureCanvas):
            canvas.flush_events()
            break


def load_ipython_extension(ipython: Any) -> None:
    """Register an idempotent host-owned post-cell redraw opportunity."""
    if ipython in _callbacks:
        return
    events = getattr(ipython, "events", None)
    if events is None or not callable(getattr(events, "register", None)):
        msg = "IPython extension requires a shell with an events.register dispatcher"
        raise TypeError(msg)
    events.register("post_run_cell", _pump_after_cell)
    _callbacks[ipython] = _pump_after_cell


def unload_ipython_extension(ipython: Any) -> None:
    """Remove only the callback that wskr registered on this shell."""
    callback = _callbacks.pop(ipython, None)
    if callback is not None:
        ipython.events.unregister("post_run_cell", callback)
