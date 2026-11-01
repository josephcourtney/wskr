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
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any, Literal

    from matplotlib.text import Text
    from matplotlib.typing import ColorType


class TerminalAxes(Axes):
    """Use parent-figure styling when legends or text are created later."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._wskr_ready = False
        self._wskr_bg_owned = "facecolor" not in kwargs
        self._wskr_explicit_text: set[str] = set()
        super().__init__(*args, **kwargs)
        self._wskr_bg_initial = self.get_facecolor()
        self._wskr_ready = True

    def set_facecolor(self, color: ColorType | None) -> None:
        if getattr(self, "_wskr_ready", False):
            self._wskr_bg_owned = False
        super().set_facecolor(color)

    @staticmethod
    def _has_explicit_color(kwargs: dict[str, Any]) -> bool:
        fontdict = kwargs.get("fontdict")
        return "color" in kwargs or (isinstance(fontdict, dict) and "color" in fontdict)

    def set_title(
        self,
        label: str,
        fontdict: dict[str, Any] | None = None,
        loc: Literal["left", "center", "right"] | None = None,
        pad: float | None = None,
        *,
        y: float | None = None,
        **kwargs: object,
    ) -> Text:
        if getattr(self, "_wskr_ready", False) and (
            self._has_explicit_color(kwargs) or self._has_explicit_color(fontdict or {})
        ):
            self._wskr_explicit_text.add("title")
        return super().set_title(label, fontdict=fontdict, loc=loc, pad=pad, y=y, **kwargs)

    def set_xlabel(
        self,
        xlabel: str,
        fontdict: dict[str, Any] | None = None,
        labelpad: float | None = None,
        *,
        loc: Literal["left", "center", "right"] | None = None,
        **kwargs: object,
    ) -> Text:
        if getattr(self, "_wskr_ready", False) and (
            self._has_explicit_color(kwargs) or self._has_explicit_color(fontdict or {})
        ):
            self._wskr_explicit_text.add("xlabel")
        return super().set_xlabel(xlabel, fontdict=fontdict, labelpad=labelpad, loc=loc, **kwargs)

    def set_ylabel(
        self,
        ylabel: str,
        fontdict: dict[str, Any] | None = None,
        labelpad: float | None = None,
        *,
        loc: Literal["bottom", "center", "top"] | None = None,
        **kwargs: object,
    ) -> Text:
        if getattr(self, "_wskr_ready", False) and (
            self._has_explicit_color(kwargs) or self._has_explicit_color(fontdict or {})
        ):
            self._wskr_explicit_text.add("ylabel")
        return super().set_ylabel(ylabel, fontdict=fontdict, labelpad=labelpad, loc=loc, **kwargs)

    def refresh_owned_colors(self, previous: dict[str, Any], new: dict[str, Any]) -> bool:
        """Update only unchanged backend-provenance surfaces and primary labels."""
        changed = False
        has_owned_background = (
            self._wskr_bg_owned
            and "axes.facecolor" in previous
            and "axes.facecolor" in new
            and mpl.rcParams["axes.facecolor"] == mpl.rcParamsDefault["axes.facecolor"]
        )
        if (
            has_owned_background
            and self.get_facecolor() == to_rgba(previous["axes.facecolor"])
            and self.get_facecolor() != to_rgba(new["axes.facecolor"])
        ):
            self._wskr_ready = False
            try:
                super().set_facecolor(new["axes.facecolor"])
            finally:
                self._wskr_ready = True
            changed = True
        for name, artist, key in (
            ("title", self.title, "text.color"),
            ("xlabel", self.xaxis.label, "axes.labelcolor"),
            ("ylabel", self.yaxis.label, "axes.labelcolor"),
        ):
            if (
                name in self._wskr_explicit_text
                or key not in previous
                or key not in new
                or mpl.rcParams[key] != mpl.rcParamsDefault[key]
            ):
                continue
            current_color = to_rgba(artist.get_color())
            if current_color == to_rgba(previous[key]) and current_color != to_rgba(new[key]):
                artist.set_color(new[key])
                changed = True
        return changed

    @contextmanager
    def _owner_defaults(self) -> Generator[None]:
        """Obtain scoped defaults from the figure that owns the axes."""
        owner = getattr(self, "_parent_figure", None)
        if isinstance(owner, TerminalFigure):
            with owner._creation_defaults():  # ruff: ignore[private-member-access] - closely coupled backend subclasses
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

    def __init__(
        self,
        *args: Any,
        _wskr_defaults: dict[str, Any] | None = None,
        _wskr_bg_owned: bool = False,
        **kwargs: Any,
    ) -> None:
        self._wskr_defaults: dict[str, Any] = dict(_wskr_defaults or {})
        self._wskr_bg_owned = _wskr_bg_owned
        self._wskr_ready = False
        with self._creation_defaults():
            super().__init__(*args, **kwargs)
        self._wskr_bg_initial = self.get_facecolor()
        self._wskr_ready = True

    def set_facecolor(self, color: ColorType) -> None:
        if getattr(self, "_wskr_ready", False):
            self._wskr_bg_owned = False
        super().set_facecolor(color)

    def refresh_owned_colors(self, new: dict[str, Any]) -> bool:
        """Opt-in, strictly owned color refresh without touching data artists.

        Only originally backend-owned values are candidates. User edits and
        changes to globally configured Matplotlib styles remain authoritative.
        """
        previous = self._wskr_defaults
        changed = False
        if (
            self._wskr_bg_owned
            and "figure.facecolor" in new
            and self.get_facecolor() == self._wskr_bg_initial
            and self.get_facecolor() != to_rgba(new["figure.facecolor"])
        ):
            self._wskr_ready = False
            try:
                super().set_facecolor(new["figure.facecolor"])
            finally:
                self._wskr_ready = True
            self._wskr_bg_initial = self.get_facecolor()
            changed = True
        for axes in self.axes:
            if isinstance(axes, TerminalAxes):
                changed = axes.refresh_owned_colors(previous, new) or changed
        # Preserve only established ownership; do not acquire previously
        # user-owned keys on a subsequent terminal-theme change.
        updated: dict[str, Any] = {
            key: new.get(key, previous[key])
            for key in mpl.rcParams
            if key in previous and mpl.rcParams[key] == mpl.rcParamsDefault[key]
        }
        self._wskr_defaults = updated
        return changed

    @contextmanager
    def _creation_defaults(self) -> Generator[None]:
        """Only backend-owned rc keys remain active during artist creation.

        A style changed after this figure's construction takes precedence.
        """
        # Use Matplotlib's typed rc key set to rule out arbitrary string keys.
        # This also keeps rc_context's mapping key type precise for ty.
        active = {
            key: self._wskr_defaults[key]
            for key in mpl.rcParams
            if key in self._wskr_defaults and mpl.rcParams[key] == mpl.rcParamsDefault[key]
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
            and not kwargs.get("polar")
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
