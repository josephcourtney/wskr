import matplotlib.pyplot as plt
from matplotlib import interactive, is_interactive
from matplotlib._pylab_helpers import Gcf  # noqa: PLC2701
from matplotlib.backend_bases import _Backend  # noqa: PLC2701

# TODO: import or implement a SixelTransport subclass
# from wskr.tty.sixel import SixelTransport

plt.style.use("dark_background")

# heuristic for interactive
if hasattr(__import__("sys"), "flags") and __import__("sys").flags.interactive:
    interactive(True)  # noqa: FBT003


@_Backend.export
class _BackendSixelAgg(_Backend):
    """Stub for Sixel-protocol backend."""

    FigureCanvas = None
    FigureManager = None

    @classmethod
    def draw_if_interactive(cls):
        manager = Gcf.get_active()
        if is_interactive() and manager and getattr(manager.canvas.figure, "get_axes", list)():
            cls.show()

    @classmethod
    def show(cls, *args, **kwargs):
        msg = "Sixel backend not yet implemented"
        raise NotImplementedError(msg)
