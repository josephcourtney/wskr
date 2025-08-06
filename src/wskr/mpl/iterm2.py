import os

import matplotlib.pyplot as plt
from matplotlib import _api, interactive  # noqa: PLC2701
from matplotlib.backend_bases import _Backend  # noqa: PLC2701
from matplotlib.backends.backend_agg import FigureCanvasAgg

from wskr.mpl.base import BaseFigureManager, TerminalBackend
from wskr.mpl.utils import detect_dark_mode

# TODO: import or implement a ITerm2Transport subclass
# from wskr.tty.iterm2 import ITerm2Transport


if os.getenv("WSKR_ENABLE_ITEMR2", "false").lower() != "true":
    msg = "iTerm2 backend is not yet implemented. Set WSKR_ENABLE_ITERM2=true to bypass."
    raise ImportError(msg)


if detect_dark_mode():
    plt.style.use("dark_background")
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
