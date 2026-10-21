"""Figure-local Matplotlib style defaults, without global rcParams mutation.

A backend-created Figure captures only values whose ownership was established
at construction. Each new axes/text object receives a temporary rc context;
custom Figure subclasses and explicit artist arguments remain authoritative.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import matplotlib as mpl
from matplotlib.axes import Axes
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any


class TerminalAxes(Axes):
    """Use parent-figure styling when legends or text are created later."""

    @contextmanager
    def _owner_defaults(self) -> Generator[None]:
        """Obtain scoped defaults from the figure that owns the axes."""
        owner = getattr(self, "_parent_figure", None)
        if isinstance(owner, TerminalFigure):
            with owner._creation_defaults():  # ruff: ignore[SLF001] - closely coupled backend subclasses
                yield
        else:
            yield

    def legend(self, *args, **kwargs):
        """Create legends with the owner's currently applicable text style."""
        with self._owner_defaults():
            return super().legend(*args, **kwargs)

    def text(self, *args, **kwargs):
        """Create axes text without altering global rcParams."""
        with self._owner_defaults():
            return super().text(*args, **kwargs)

    def annotate(self, *args, **kwargs):
        """Create annotations with figure-local defaults."""
        with self._owner_defaults():
            return super().annotate(*args, **kwargs)


class TerminalFigure(Figure):
    """Stock Matplotlib figure with scoped defaults for subsequently created art."""

    def __init__(self, *args: Any, _wskr_defaults: dict[str, Any] | None = None, **kwargs: Any) -> None:
        self._wskr_defaults = dict(_wskr_defaults or {})
        with self._creation_defaults():
            super().__init__(*args, **kwargs)

    @contextmanager
    def _creation_defaults(self) -> Generator[None]:
        """Only backend-owned rc keys remain active during artist creation.

        A style changed after this figure's construction takes precedence.
        """
        active = {
            key: value for key, value in self._wskr_defaults.items() if mpl.rcParams[key] == mpl.rcParamsDefault[key]
        }
        with mpl.rc_context(rc=active):
            yield

    @staticmethod
    def _axes_options(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        """Wrap only Matplotlib's default rectilinear axes class.

        Explicit user axes classes, projections and existing Axes win.
        """
        if (
            "axes_class" not in kwargs
            and kwargs.get("projection") is None
            and not kwargs.get("polar", False)
            and not (args and isinstance(args[0], Axes))
        ):
            return {**kwargs, "axes_class": TerminalAxes}
        return kwargs

    def add_subplot(self, *args, **kwargs):
        """Construct axes using the figure's owned defaults."""
        with self._creation_defaults():
            return super().add_subplot(*args, **self._axes_options(args, kwargs))

    def add_axes(self, *args, **kwargs):
        """Construct manually positioned axes using owned defaults."""
        with self._creation_defaults():
            return super().add_axes(*args, **self._axes_options(args, kwargs))

    def text(self, *args, **kwargs):
        """Construct figure-level text without affecting other figures."""
        with self._creation_defaults():
            return super().text(*args, **kwargs)

    def suptitle(self, t, **kwargs):
        """Construct a supertitle with backend-owned text defaults."""
        with self._creation_defaults():
            return super().suptitle(t, **kwargs)


__all__ = ["TerminalAxes", "TerminalFigure"]
