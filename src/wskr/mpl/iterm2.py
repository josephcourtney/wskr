import os

from matplotlib import _api, interactive  # noqa: PLC2701
from matplotlib.backend_bases import _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.errors import FeatureUnavailableError
from wskr.mpl.base import BaseFigureManager, TerminalBackend

# TODO: import or implement a ITerm2Transport subclass  # noqa: FIX002, TD002, TD003
# from wskr.tty.iterm2 import ITerm2Transport


if os.getenv("WSKR_ENABLE_ITERM2", "false").lower() != "true":
    msg = "iTerm2 backend is not yet implemented. Set WSKR_ENABLE_ITERM2=true to bypass."
    raise FeatureUnavailableError(msg)

interactive(True)  # noqa: FBT003


class StubManager(BaseFigureManager):
    # We rely on TerminalBackend.show to raise, but override here if manager.show invoked directly
    def show(self, *args, **kwargs):
        msg = "iTerm2 backend not yet implemented"
        raise NotImplementedError(msg)


class StubCanvas(FigureCanvasAgg):
    manager_class = _api.classproperty(lambda _: StubManager)


@_Backend.export
class _BackendIterm2Agg(TerminalBackend):
    FigureCanvas = StubCanvas
    FigureManager = StubManager
    not_impl_msg = "iTerm2 backend not yet implemented"
