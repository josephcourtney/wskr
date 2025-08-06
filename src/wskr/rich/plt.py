from __future__ import annotations

import array
import fcntl
import sys
import termios
from functools import lru_cache
from io import BytesIO
from typing import TYPE_CHECKING

import numpy as np
from rich.console import Console, ConsoleOptions, RenderResult
from rich.measure import Measurement

from wskr.mpl.utils import compute_terminal_figure_size
from wskr.rich.img import RichImage

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

rng = np.random.default_rng()

console = Console()

dpi_macbook_pro_13in_m2_2022 = 227
dpi_external_monitors_195 = 137


@lru_cache(maxsize=1)
def get_terminal_size() -> tuple[float, float, int, int]:
    """Determine the pixel dimensions of each character cell in the terminal."""
    buf = array.array("H", [0, 0, 0, 0])
    try:
        fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, buf)
    except OSError:
        return (8, 16, 80, 24)
    n_row, n_col, w_px, h_px = buf
    return w_px, h_px, n_col, n_row


def _render_to_buffer(rich_plot: RichPlot) -> BytesIO:
    buf = BytesIO()
    rich_plot.figure.savefig(
        buf,
        format="PNG",
        dpi=rich_plot.dpi * rich_plot.zoom,
        transparent=True,
    )
    buf.seek(0)
    return buf


class RichPlot:
    """Renderable for displaying Matplotlib figures in the terminal using RichImage."""

    def __init__(
        self,
        figure: plt.Figure,
        desired_width: int | None = None,
        desired_height: int | None = None,
        zoom: float = 1.0,
        dpi: int = 100,
    ):
        """
        Initialize Renderable.

        :param figure: Matplotlib Figure object.
        :param desired_width: Desired width in characters (cells).
        :param desired_height: Desired height in characters (cells).
        """
        self.figure = figure
        self.desired_width = desired_width
        self.desired_height = desired_height
        self.zoom = zoom
        self.dpi = dpi

    def _adapt_size(self, console: Console, options: ConsoleOptions) -> tuple[int, int]:
        if self.desired_width is None:
            desired_width = self.desired_width or console.size.width
        elif self.desired_width <= 0:
            desired_width = self.desired_width + console.size.width
        else:
            desired_width = self.desired_width

        if self.desired_height is None:
            desired_height = self.desired_height or (options.height or console.size.height)
        elif self.desired_height <= 0:
            desired_height = self.desired_height + (options.height or console.size.height)
        else:
            desired_height = self.desired_height
        return desired_width, desired_height

    def _render_to_buffer(self) -> BytesIO:
        """Render the figure to a PNG in memory."""
        buf = BytesIO()
        self.figure.savefig(
            buf,
            format="PNG",
            dpi=self.dpi * self.zoom,
            transparent=True,
        )
        buf.seek(0)
        return buf

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:  # noqa: PLW3201
        """Measure the width needed for the figure."""
        desired_width, _desired_height = self._adapt_size(console, options)
        max_width = min(desired_width, options.max_width)
        min_width = min(desired_width, options.max_width)
        return Measurement(min_width, max_width)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:  # noqa: PLW3201
        """Render the figure within the terminal constraints."""
        w_px, h_px, n_col, n_row = get_terminal_size()

        desired_width, desired_height = self._adapt_size(console, options)

        w_cell_in, h_cell_in = compute_terminal_figure_size(
            desired_width, desired_height, w_px, h_px, n_col, n_row, self.dpi, self.zoom
        )
        self.figure.set_size_inches(w_cell_in / self.zoom, h_cell_in / self.zoom)

        img = RichImage(
            image_path=self._render_to_buffer(), desired_width=desired_width, desired_height=desired_height
        )
        yield from img.__rich_console__(console, options)
