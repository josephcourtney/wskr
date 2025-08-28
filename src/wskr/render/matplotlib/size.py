"""Helpers for converting terminal dimensions to figure sizes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class TerminalMetrics:
    """Pixel and cell metrics describing the active terminal."""

    w_px: int
    h_px: int
    n_col: int
    n_row: int
    dpi: int
    zoom: float = 1.0


def autosize_figure(figure: Figure, width_px: int, height_px: int) -> None:
    """Resize ``figure`` to fit within the terminal window."""
    if width_px <= 0 or height_px <= 0:
        logger.warning(
            "autosize_figure: received non-positive dimensions (%d, %d), skipping resize",
            width_px,
            height_px,
        )
        return

    dpi = figure.dpi
    orig_w, orig_h = figure.get_size_inches()
    aspect = orig_h / orig_w if orig_w else 1.0

    if aspect > 1:
        new_h = height_px / dpi
        new_w = new_h / aspect
    else:
        new_w = width_px / dpi
        new_h = new_w * aspect

    figure.set_size_inches(new_w, new_h)


def compute_terminal_figure_size(
    desired_width: int, desired_height: int, metrics: TerminalMetrics
) -> tuple[float, float]:
    """Compute figure width and height in inches for the given metrics."""
    w_in = desired_width * metrics.w_px / (metrics.n_col * metrics.dpi * metrics.zoom)
    h_in = desired_height * metrics.h_px / (metrics.n_row * metrics.dpi * metrics.zoom)
    return w_in, h_in
