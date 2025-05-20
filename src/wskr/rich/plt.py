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
from rich.table import Table

from wskr.plot import make_plot_grid
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

        w_cell_in = desired_width * w_px / (n_col * self.dpi)
        h_cell_in = desired_height * h_px / (n_row * self.dpi)
        self.figure.set_size_inches(w_cell_in / self.zoom, h_cell_in / self.zoom)

        img = RichImage(
            image_path=self._render_to_buffer(), desired_width=desired_width, desired_height=desired_height
        )
        yield from img.__rich_console__(console, options)


def sparkline(x, y, columns=8, rows=1):
    fig, ax = make_plot_grid(1, 1)
    ax[0].plot(x, y, c="w")
    ax[0].axis("off")
    ax[0].margins(0)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    return RichPlot(
        figure=fig,
        desired_width=columns,
        desired_height=rows,
        dpi=dpi_macbook_pro_13in_m2_2022,
    )


if __name__ == "__main__":
    dpi = dpi_macbook_pro_13in_m2_2022
    w_px, h_px, n_col, n_row = get_terminal_size()
    print(f"cell size:       {w_px / n_col:>6.2f} x{h_px / n_row:>6.2f} pixels")
    print(f"cell resolution: {dpi * n_col / w_px:>6.2f} x{dpi * n_row / h_px:>6.2f} cell/inch")

    table = Table(title="Sparklines", show_lines=False)
    table.add_column("column 1", justify="left")
    table.add_column("column 2", justify="center")
    table.add_column("column 3", justify="right")
    for _i in range(3):
        table.add_row("name", "detail", sparkline(np.linspace(0, 1, 32), rng.normal(size=32)))
    console.print(table)

    fig, ax = make_plot_grid(1, 1, figure_kwargs={"layout": "constrained"})
    x = np.linspace(0, 1, 128)
    y = np.exp((2j * np.pi * 5 - 3) * x)
    ax[0].plot(x, y.real, c="w")
    ax[0].set_xlim(left=0)
    ax[0].spines["bottom"].set_position("zero")
    ax[0].spines["top"].set_visible(False)
    ax[0].spines["right"].set_visible(False)
    ax[0].xaxis.set_tick_params(which="both", direction="inout")
    ax[0].xaxis.set_tick_params(which="major", length=7.0)
    ax[0].xaxis.set_tick_params(which="minor", length=4.0)

    y_max = np.max([abs(e) for e in ax[0].get_ylim()])
    ax[0].set_ylim(-y_max, y_max)

    rp = RichPlot(figure=fig, desired_width=40, desired_height=20, dpi=dpi_macbook_pro_13in_m2_2022)
    console.print(rp)
