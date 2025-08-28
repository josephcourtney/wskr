from __future__ import annotations

import os

from matplotlib import _api  # noqa: PLC2701
from matplotlib.backend_bases import _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.core.errors import FeatureUnavailableError

from .core import TerminalBackend

if os.getenv("WSKR_ENABLE_ITERM2", "").lower() != "true":
    msg = "iTerm2 backend is not yet implemented. Set WSKR_ENABLE_ITERM2=true to bypass."
    raise FeatureUnavailableError(msg)


class _Iterm2Canvas(FigureCanvasAgg):
    manager_class = _api.classproperty(lambda _: None)


@_Backend.export
class _BackendIterm2Agg(TerminalBackend):
    not_impl_msg = "iTerm2 backend not yet implemented"
    FigureCanvas = _Iterm2Canvas
    FigureManager = None


__all__ = ["_BackendIterm2Agg"]
