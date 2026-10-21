"""Manual terminal visual characterization for Phase 1.

Run inside a real Kitty terminal and capture an OS screenshot. This script
cannot certify image visibility from a successful process exit.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure


def _plot() -> Figure:
    """Build a stable multi-line Matplotlib graph with text and a legend."""
    import matplotlib.pyplot as plt  # ruff: ignore[PLC0415]
    import numpy as np  # ruff: ignore[PLC0415]

    x = np.linspace(0, 4 * np.pi, 400)
    fig, ax = plt.subplots()
    ax.plot(x, np.sin(x), label="Sine")
    ax.plot(x, np.cos(x), label="Cosine")
    ax.set(xlabel="Radians", ylabel="Amplitude", title="wskr: Matplotlib / Rich visual check")
    ax.grid(alpha=0.25)
    ax.legend()
    return fig


def _require_tty() -> None:
    """Avoid sending raw terminal graphics into a pipe or captured stdout."""
    if not sys.stdout.isatty():
        msg = "Visual checks require a foreground terminal; do not pipe or redirect output."
        raise SystemExit(msg)


def _run_matplotlib(reference: Path | None) -> None:
    """Exercise the stock Matplotlib terminal backend, not the Rich adapter."""
    import matplotlib  # ruff: ignore[PLC0415]

    matplotlib.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[PLC0415]

    fig = _plot()
    if reference is not None:
        reference.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(reference)
        print(f"Reference PNG: {reference}")
    print(f"Figure size before display: {tuple(fig.get_size_inches())}, DPI: {fig.dpi}")
    plt.show()
    print("Matplotlib returned from show(); screen visibility still requires inspection.")


def _run_rich(reference: Path | None, *, fallback: bool) -> None:
    """Exercise a Rich panel and table with explicitly selected transport."""
    if fallback:
        os.environ["WSKR_PROTOCOL"] = "noop"
    elif os.environ.get("WSKR_PROTOCOL") != "kitty":
        msg = "To test actual Kitty-backed Rich rendering, run: WSKR_PROTOCOL=kitty just visual-smoke rich"
        raise SystemExit(msg)

    import matplotlib  # ruff: ignore[PLC0415]

    matplotlib.use("Agg")
    from rich.console import Console  # ruff: ignore[PLC0415]
    from rich.panel import Panel  # ruff: ignore[PLC0415]
    from rich.table import Table  # ruff: ignore[PLC0415]

    from wskr.render.rich.plt import RichPlot  # ruff: ignore[PLC0415]

    fig = _plot()
    if reference is not None:
        reference.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(reference)
        print(f"Reference PNG: {reference}")
    console = Console()
    console.print(Panel(RichPlot(fig, desired_width=40, desired_height=10), title="wskr Rich panel"))
    table = Table(title="wskr Rich table")
    table.add_column("Kind")
    table.add_column("Plot")
    table.add_row("Sine + cosine", RichPlot(fig, desired_width=36, desired_height=8))
    console.print(table)
    print("Rich returned from rendering; inspect panel/table placement in Kitty.")


def main(argv: Sequence[str] | None = None) -> None:
    """Render reproducible manual scenarios without assuming visual success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("matplotlib", "rich", "noop"), default="matplotlib")
    parser.add_argument("--reference", type=Path, help="Optional reference PNG path")
    parser.add_argument("--pause", action="store_true", help="Hold the terminal for an OS screenshot")
    args = parser.parse_args(argv)

    _require_tty()
    print(f"Scenario: {args.mode}; TERM={os.getenv('TERM')}; WSKR_PROTOCOL={os.getenv('WSKR_PROTOCOL')}")
    if args.mode == "matplotlib":
        _run_matplotlib(args.reference)
    else:
        _run_rich(args.reference, fallback=args.mode == "noop")
    if args.pause:
        input("Inspect/capture the terminal window, then press Enter to exit: ")


if __name__ == "__main__":
    main()
