import os

import matplotlib.pyplot as plt
from matplotlib import (
    _api,  # noqa: PLC2701
    interactive,
)
from matplotlib.backend_bases import _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.mpl.base import BaseFigureManager, TerminalBackend

# from wskr.tty.sixel import SixelTransport
from wskr.mpl.utils import detect_dark_mode

if os.getenv("WSKR_ENABLE_SIXEL", "false").lower() != "true":
    msg = "Sixel backend is not yet implemented. Set WSKR_ENABLE_SIXEL=true to bypass."
    raise ImportError(msg)

# TODO: import or implement a SixelTransport subclass
# from wskr.tty.sixel import SixelTransport

if detect_dark_mode():
    plt.style.use("dark_background")

interactive(True)  # noqa: FBT003


class StubManager(BaseFigureManager):
    pass  # Backend.show will handle the not-implemented error


class StubCanvas(FigureCanvasAgg):
    manager_class = _api.classproperty(lambda _: StubManager)


@_Backend.export
class _BackendSixelAgg(TerminalBackend):
    FigureCanvas = StubCanvas
    FigureManager = StubManager
    not_impl_msg = "Sixel backend not yet implemented"
