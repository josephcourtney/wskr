"""Render ordinary Matplotlib output, exit Python, and leave Kitty history visible.

The completion marker is written by the earliest atexit callback, after
Matplotlib's registered figure-manager cleanup has finished. Kitty --hold
keeps the window available for a screenshot after the Python process exits.
"""

from __future__ import annotations

import argparse
import atexit
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    """Draw a deterministic colored chart and exit without calling plt.close."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-file", type=Path, required=True)
    args = parser.parse_args(argv)

    # This callback is registered *before* importing Matplotlib, so it runs
    # after Gcf.destroy_all and the backend's shutdown marker.
    atexit.register(args.ready_file.write_text, "python-exited\n", encoding="utf-8")

    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    _, ax = plt.subplots(figsize=(4, 3), dpi=110)
    ax.bar([1, 2, 3], [1.5, 2.5, 2], color=("cyan", "magenta", "yellow"))
    ax.set(xlim=(0.5, 3.5), ylim=(0, 3), title="wskr: persistent output after Python exit")
    plt.show()
    print("Rendered ordinary Matplotlib output; Python is exiting.")


if __name__ == "__main__":
    main()
