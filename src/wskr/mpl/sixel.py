import os

from matplotlib import (
    _api,  # noqa: PLC2701
    interactive,
)
from matplotlib.backend_bases import _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.errors import FeatureUnavailableError
from wskr.mpl.base import BaseFigureManager, TerminalBackend

# from wskr.tty.sixel import SixelTransport

if os.getenv("WSKR_ENABLE_SIXEL", "false").lower() != "true":
    msg = "Sixel backend is not yet implemented. Set WSKR_ENABLE_SIXEL=true to bypass."
    raise FeatureUnavailableError(msg)

# TODO: import or implement a SixelTransport subclass  # noqa: FIX002, TD002, TD003
# from wskr.tty.sixel import SixelTransport

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
