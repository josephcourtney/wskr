"""Exercise event-pumped viewport resizing inside a real Kitty process.

A graphical harness moves the Kitty window between two known sizes and uses
file-backed handoffs exclusively to coordinate screenshots. The plotting
backend never receives or reads terminal input during this test.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure


_RESIZED_FRAMES = 2
_EXPANDED_FRAMES = 3


def _wait_for(path: Path, *, label: str) -> None:
    deadline = time.monotonic() + 18
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not path.exists():
        msg = f"Timed out waiting for {label}"
        raise TimeoutError(msg)


def _signal_initial_and_wait(directory: Path) -> None:
    (directory / "initial.ready").write_text("displayed\n", encoding="utf-8")
    _wait_for(directory / "resize.proceed", label="pre-redraw screenshot")


def _pump_until(figure: Figure, sent: list[dict[str, list[int]]], *, count: int) -> None:
    deadline = time.monotonic() + 18
    while len(sent) < count and time.monotonic() < deadline:
        figure.canvas.flush_events()  # real backend hook, no mock
        time.sleep(0.05)
    if len(sent) < count:
        msg = f"Event-pumped redraw did not occur: {sent}"
        raise TimeoutError(msg)


def _check_geometry_unchanged(figure: Figure, original: tuple[tuple[float, ...], float]) -> None:
    if (tuple(figure.get_size_inches()), figure.dpi) != original:
        msg = "Terminal window resizing modified user-owned figure dimensions"
        raise AssertionError(msg)


def _make_figure() -> Figure:
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    height = int(os.getenv("WSKR_CASE_HEIGHT", "2"))
    if height not in {2, 6}:
        msg = "Kitty GUI fixture supports figure heights of two or six inches"
        raise ValueError(msg)
    fig, ax = plt.subplots(figsize=(9, height), dpi=100)
    ax.bar([1, 2], [3, 4], color=("red", "blue"), width=0.65)
    ax.set(xlim=(0.2, 2.8), ylim=(0, 5), title="wskr event-pumped nonblocking resize")
    return fig


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args(argv)
    args.directory.mkdir(parents=True, exist_ok=True)

    # Establish the large starting window before creating the first figure.
    (args.directory / "launch.ready").write_text("launch\n", encoding="utf-8")
    _wait_for(args.directory / "launch.proceed", label="initial Kitty resize")

    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]
    from PIL import Image  # ruff: ignore[import-outside-top-level]

    from wskr.protocol.kitty_native import NativeKittyTransport  # ruff: ignore[import-outside-top-level]

    sent: list[dict[str, list[int]]] = []
    send = NativeKittyTransport.send_anchored_image

    def record_send(transport: NativeKittyTransport, png: bytes) -> None:
        with Image.open(BytesIO(png)) as image:
            size = image.size
        viewport = transport.get_window_size_px()
        if not 0 < size[0] <= viewport[0]:
            msg = f"Displayed width exceeds measured Kitty viewport: {size}, {viewport}"
            raise AssertionError(msg)
        if not 0 < size[1] <= viewport[1]:
            msg = f"Displayed height exceeds measured Kitty viewport: {size}, {viewport}"
            raise AssertionError(msg)
        send(transport, png)
        sent.append({"raster": list(size), "viewport": list(viewport)})
        (args.directory / "frames.json").write_text(json.dumps(sent), encoding="utf-8")

    with patch.object(NativeKittyTransport, "send_anchored_image", record_send):
        fig = _make_figure()
        original = tuple(fig.get_size_inches()), fig.dpi
        plt.show(block=False)
        if len(sent) != 1:
            msg = f"Unexpected initial uploads: {sent}"
            raise AssertionError(msg)
        _signal_initial_and_wait(args.directory)

        _pump_until(fig, sent, count=_RESIZED_FRAMES)
        if sent[-1]["raster"][0] >= sent[0]["raster"][0] - 80:
            msg = f"Fitted raster failed to shrink: {sent}"
            raise AssertionError(msg)
        _check_geometry_unchanged(fig, original)
        (args.directory / "resized.ready").write_text("redrawn\n", encoding="utf-8")
        _wait_for(args.directory / "resized.proceed", label="resized Kitty screenshot")
        _pump_until(fig, sent, count=_EXPANDED_FRAMES)
        if sent[-1]["raster"][0] <= sent[1]["raster"][0] + 80:
            msg = f"Fitted raster failed to expand with the Kitty viewport: {sent}"
            raise AssertionError(msg)
        _check_geometry_unchanged(fig, original)
        (args.directory / "expanded.ready").write_text("redrawn\n", encoding="utf-8")
        _wait_for(args.directory / "expanded.proceed", label="expanded Kitty screenshot")

    # Exit without explicit close: normal nonblocking output should persist.
    (args.directory / "finished").write_text("complete\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if output_dir := os.getenv("WSKR_GUI_LOG_DIR"):
            Path(output_dir, "python-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
