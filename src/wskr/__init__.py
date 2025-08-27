import matplotlib as mpl
import matplotlib.pyplot as plt

from . import config as _config

# Make *absolutely sure* we never try to invoke TeX during draw or savefig,
# which would hang under test timeouts.
mpl.rcParams["text.usetex"] = False


def init(*, style: str | None = None, **config_overrides: object) -> None:
    """Initialise wskr and apply optional configuration."""
    if config_overrides:
        _config.configure(**config_overrides)
    if style == "auto-dark":
        from .mpl.utils import detect_dark_mode  # noqa: PLC0415

        if detect_dark_mode():
            plt.style.use("dark_background")


__all__ = ["init"]
