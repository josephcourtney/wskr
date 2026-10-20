# ruff: file-ignore[non-empty-init-module]  # explicit configuration API only
from .core import config as _config


def init(*, style: str | None = None, **config_overrides: object) -> None:
    """Initialise wskr and apply optional configuration."""
    if config_overrides:
        _config.configure(**config_overrides)
    if style == "auto-dark":
        import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]
        from .render.matplotlib.utils import detect_dark_mode  # ruff: ignore[import-outside-top-level]

        if detect_dark_mode():
            plt.style.use("dark_background")


__all__ = ["init"]
