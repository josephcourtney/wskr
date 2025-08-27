"""Command-line demonstration of wskr features."""

from __future__ import annotations

import argparse
import os
from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.pyplot as plt

from . import init

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Render a simple demonstration plot using wskr."""
    parser = argparse.ArgumentParser(prog="wskr.demo", add_help=False)
    parser.add_argument("--style", default="auto-dark", help="Matplotlib style to apply")
    parser.add_argument("-h", "--help", action="help")
    args = parser.parse_args(list(argv) if argv is not None else None)

    # Ensure we don't attempt to talk to a real terminal when run in tests.
    os.environ.setdefault("WSKR_TRANSPORT", "noop")
    try:
        mpl.use("wskr", force=True)
    except ValueError:  # pragma: no cover - backend not installed
        mpl.use("Agg", force=True)
    init(style=args.style)

    _fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 0], marker="o")
    ax.set_title("wskr demo")
    plt.show()
    return 0


if __name__ == "__main__":  # pragma: no cover - module execution
    raise SystemExit(main())
