"""Stage two fitted contact-sheet pages for real Kitty screenshot evidence."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Sequence


def _await_release(ready: Path, release: Path) -> None:
    ready.write_text("ready\n", encoding="utf-8")
    deadline = time.monotonic() + 15
    while not release.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not release.exists():
        msg = "Timed out waiting for Kitty paging screenshot"
        raise TimeoutError(msg)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args(argv)
    args.directory.mkdir(parents=True, exist_ok=True)

    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    from wskr.render.matplotlib import core  # ruff: ignore[import-outside-top-level]

    for color in ("red", "blue", "green"):
        plt.figure(figsize=(3, 2), dpi=80, facecolor=color)

    def checkpoints(managers: object, geometry: object) -> None:
        _await_release(args.directory / "page0.ready", args.directory / "page0.proceed")
        core._redraw_foreground_figures(managers, page_index=1)
        _await_release(args.directory / "page1.ready", args.directory / "page1.proceed")

    with patch.object(core, "_wait_for_foreground_resize", checkpoints):
        plt.show(block=True)
    (args.directory / "closed").write_text("restored\n", encoding="utf-8")


if __name__ == "__main__":
    main()
