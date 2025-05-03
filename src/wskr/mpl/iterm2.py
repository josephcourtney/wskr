import matplotlib.pyplot as plt
from matplotlib import interactive, is_interactive
from matplotlib._pylab_helpers import Gcf  # noqa: PLC2701
from matplotlib.backend_bases import _Backend  # noqa: PLC2701

# TODO: import or implement an Iterm2Transport subclass
# from wskr.tty.iterm2 import Iterm2Transport

plt.style.use("dark_background")

if hasattr(__import__("sys"), "flags") and __import__("sys").flags.interactive:
    interactive(True)  # noqa: FBT003


@_Backend.export
class _BackendIterm2Agg(_Backend):
    """Stub for iTerm2 inline-image protocol backend."""

    FigureCanvas = None
    FigureManager = None

    @classmethod
    def draw_if_interactive(cls):
        manager = Gcf.get_active()
        if is_interactive() and manager and getattr(manager.canvas.figure, "get_axes", list)():
            cls.show()

    @classmethod
    def show(cls, *args, **kwargs):
        msg = "iTerm2 backend not yet implemented"
        raise NotImplementedError(msg)
