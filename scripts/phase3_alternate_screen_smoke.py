"""Real Kitty screenshot fixture for a temporary blocking Matplotlib session.

This fixture substitutes the Enter prompt with a file-backed handoff only so
an external screenshot test can capture the alternate screen before closure.
The ordinary foreground Enter path is tested separately on a real PTY.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from unittest.mock import patch
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready", required=True, type=Path)
    parser.add_argument("--proceed", required=True, type=Path)
    parser.add_argument("--closed", required=True, type=Path)
    args = parser.parse_args(argv)

    # The primary screen markers must reappear adjacent after closing the
    # alternate screen. The plot must remain absent on the restored screen.
    print("\x1b[48;2;0;255;0m" + " " * 28 + "\x1b[0m PRIMARY BEFORE", flush=True)

    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    _, ax = plt.subplots(figsize=(4, 3), dpi=95)
    ax.bar([1, 2, 3], [2, 3, 2.5], color=("cyan", "magenta", "yellow"))
    ax.set(xlim=(0.5, 3.5), ylim=(0, 3.5), title="temporary Kitty alternate screen")

    def checkpoint(prompt: object = "", /) -> str:
        print(prompt, flush=True)
        args.ready.write_text("alternate-active\n", encoding="utf-8")
        end = time.monotonic() + 12
        while not args.proceed.exists() and time.monotonic() < end:
            time.sleep(0.05)
        if not args.proceed.exists():
            msg = "Alternate-screen screenshot did not complete before deadline"
            raise TimeoutError(msg)
        return ""

    with patch("builtins.input", checkpoint):
        plt.show(block=True)

    print("\x1b[48;2;255;0;0m" + " " * 28 + "\x1b[0m PRIMARY AFTER", flush=True)
    args.closed.write_text("primary-restored\n", encoding="utf-8")


if __name__ == "__main__":
    main()
