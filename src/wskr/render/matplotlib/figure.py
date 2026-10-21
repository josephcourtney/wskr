"""Figure-local Matplotlib style defaults, without global rcParams mutation.

A backend-created Figure captures only values whose ownership was established
at construction. Each new axes/text object receives a temporary rc context;
custom Figure subclasses and explicit artist arguments remain authoritative.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import matplotlib as mpl
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any


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
            key: value
            for key, value in self._wskr_defaults.items()
            if mpl.rcParams[key] == mpl.rcParamsDefault[key]
        }
        with mpl.rc_context(rc=active):
            yield

    def add_subplot(self, *args: Any, **kwargs: Any) -> Any:
        """Construct axes using the figure's owned defaults."""
        with self._creation_defaults():
            return super().add_subplot(*args, **kwargs)

    def add_axes(self, *args: Any, **kwargs: Any) -> Any:
        """Construct manually positioned axes using owned defaults."""
        with self._creation_defaults():
            return super().add_axes(*args, **kwargs)

    def text(self, *args: Any, **kwargs: Any) -> Any:
        """Construct figure-level text without affecting other figures."""
        with self._creation_defaults():
            return super().text(*args, **kwargs)

    def suptitle(self, t: str, **kwargs: Any) -> Any:
        """Construct a supertitle with backend-owned text defaults."""
        with self._creation_defaults():
            return super().suptitle(t, **kwargs)


__all__ = ["TerminalFigure"]
