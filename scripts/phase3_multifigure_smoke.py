"""Hold a fitted Kitty multi-figure sheet for a real screenshot test."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready", required=True, type=Path)
    parser.add_argument("--proceed", required=True, type=Path)
    parser.add_argument("--closed", required=True, type=Path)
    args = parser.parse_args(argv)

    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    plt.figure(figsize=(3, 2), dpi=90, facecolor="red")
    plt.figure(figsize=(3, 2), dpi=90, facecolor="blue")

    def checkpoint(prompt: object = "", /) -> str:
        print(prompt, flush=True)
        args.ready.write_text("two-panels-visible\n", encoding="utf-8")
        deadline = time.monotonic() + 12
        while not args.proceed.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not args.proceed.exists():
            msg = "Timed out waiting for contact-sheet capture"
            raise TimeoutError(msg)
        return ""

    with patch("builtins.input", checkpoint):
        plt.show(block=True)

    args.closed.write_text("primary-restored\n", encoding="utf-8")


if __name__ == "__main__":
    main()
