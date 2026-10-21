"""Pure mapping of measured terminal values to backend-owned Matplotlib defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cycler import cycler

from wskr.terminal.color import RGB

if TYPE_CHECKING:
    from typing import Any

    from wskr.terminal.profile import TerminalProfile


_MIN_PALETTE_COLORS = 3
_MIN_CONTRAST_RATIO = 3.0
_MIN_COLOR_DISTANCE_SQUARED = 48 * 48


@dataclass(frozen=True, slots=True)
class FigureDefaults:
    """Default figure dimensions in inches and the effective raster DPI."""

    width_in: float
    height_in: float
    dpi: float


def suggested_figure_size(
    profile: TerminalProfile,
    *,
    dpi: float = 100,
    width_fraction: float = 0.9,
    height_fraction: float = 0.33,
) -> FigureDefaults | None:
    """Return no suggestion when cell pixels are unknown.

    Figure size is a default only; explicit figsize/dpi must not be overwritten.
    """
    width = profile.width_px.value
    height = profile.height_px.value
    if not width or not height or dpi <= 0:
        return None
    if not (0 < width_fraction <= 1 and 0 < height_fraction <= 1):
        msg = "Figure fractions must be between zero and one"
        raise ValueError(msg)
    return FigureDefaults(width * width_fraction / dpi, height * height_fraction / dpi, dpi)


def _contrast_ratio(a: RGB, b: RGB) -> float:
    """Compute luminance-based contrast against the terminal background."""
    lighter = max(a.luminance, b.luminance)
    darker = min(a.luminance, b.luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _color_separation_squared(a: RGB, b: RGB) -> int:
    """Reject effectively identical palette entries."""
    return (a.red - b.red) ** 2 + (a.green - b.green) ** 2 + (a.blue - b.blue) ** 2


def _visible_palette(colors: tuple[RGB | None, ...], background: RGB) -> list[str]:
    """Prefer terminal palette order after excluding low-contrast duplicates."""
    selected: list[RGB] = []
    for candidate in colors:
        if candidate is None or _contrast_ratio(candidate, background) < _MIN_CONTRAST_RATIO:
            continue
        if any(_color_separation_squared(candidate, other) < _MIN_COLOR_DISTANCE_SQUARED for other in selected):
            continue
        selected.append(candidate)
    return [color.to_hex() for color in selected]


def resolve_rc_defaults(
    profile: TerminalProfile,
    *,
    explicit: dict[str, Any] | None = None,
    dpi: float = 100,
) -> dict[str, Any]:
    """Produce only inferred defaults, leaving explicit caller-owned values intact.

    This function never changes Matplotlib rcParams, artists or global styles.
    The renderer must only apply the result to backend-owned new figures.
    """
    defaults: dict[str, Any] = {}
    foreground = profile.foreground.value
    background = profile.background.value
    if background is not None:
        defaults["figure.facecolor"] = background.to_hex()
        defaults["axes.facecolor"] = background.to_hex()
        defaults["savefig.facecolor"] = background.to_hex()
    if foreground is not None:
        text = foreground.to_hex()
        defaults.update({
            "text.color": text,
            "axes.labelcolor": text,
            "axes.edgecolor": text,
            "xtick.color": text,
            "ytick.color": text,
        })
    if foreground is not None and background is not None:
        muted = RGB(
            round(0.25 * foreground.red + 0.75 * background.red),
            round(0.25 * foreground.green + 0.75 * background.green),
            round(0.25 * foreground.blue + 0.75 * background.blue),
        )
        defaults["grid.color"] = muted.to_hex()
    cell_height = profile.cell_height_px.value
    if cell_height is not None and dpi > 0:
        defaults["font.size"] = max(6.0, cell_height * 0.6 * 72 / dpi)

    palette = profile.ansi_palette.value
    if palette is not None and background is not None:
        usable = _visible_palette(palette, background)
        if len(usable) >= _MIN_PALETTE_COLORS:
            defaults["axes.prop_cycle"] = cycler(color=usable)

    figure = suggested_figure_size(profile, dpi=dpi)
    if figure is not None:
        defaults["figure.figsize"] = (figure.width_in, figure.height_in)
        defaults["figure.dpi"] = figure.dpi

    for key in explicit or ():
        defaults.pop(key, None)
    return defaults


__all__ = ["FigureDefaults", "resolve_rc_defaults", "suggested_figure_size"]
