"""Real Kitty GUI fixture for the explicitly owned alternate-screen live mode."""

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

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from wskr.protocol.kitty_native import NativeKittyTransport
from wskr.render.matplotlib.live import owned_viewport

if TYPE_CHECKING:
    from collections.abc import Sequence


def _await(path: Path) -> None:
    deadline = time.monotonic() + 18
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not path.exists():
        msg = f"Timed out waiting for {path.name}"
        raise TimeoutError(msg)


def _poll(view) -> None:
    deadline = time.monotonic() + 18
    while time.monotonic() < deadline:
        if view.poll_resize():
            return
        time.sleep(0.05)
    msg = "Live viewport did not observe a stable terminal resize"
    raise TimeoutError(msg)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args(argv)
    directory = args.directory
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "launch.ready").write_text("ready\n", encoding="utf-8")
    _await(directory / "launch.proceed")

    fig = Figure(figsize=(9, 2), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.bar([1, 2], [3, 4], color=("red", "blue"), width=0.65)
    ax.set(xlim=(0.2, 2.8), ylim=(0, 5))
    original = tuple(fig.get_size_inches()), fig.dpi

    sent: list[dict[str, list[int]]] = []
    original_send = NativeKittyTransport.send_image

    def record(transport: NativeKittyTransport, png: bytes) -> None:
        with Image.open(BytesIO(png)) as source:
            size = source.size
        viewport = transport.get_window_size_px()
        if size[0] > viewport[0] or size[1] > viewport[1]:
            msg = f"Live PNG exceeds viewport: {size}, {viewport}"
            raise AssertionError(msg)
        original_send(transport, png)
        sent.append({"raster": list(size), "viewport": list(viewport)})
        (directory / "frames.json").write_text(json.dumps(sent), encoding="utf-8")

    with patch.object(NativeKittyTransport, "send_image", record), owned_viewport(fig) as screen:
        (directory / "initial.ready").write_text("ready\n", encoding="utf-8")
        _await(directory / "resize.proceed")
        _poll(screen)
        (directory / "resized.ready").write_text("ready\n", encoding="utf-8")
        _await(directory / "expand.proceed")
        _poll(screen)
        (directory / "expanded.ready").write_text("ready\n", encoding="utf-8")
        _await(directory / "exit.proceed")

    if [frame["raster"][0] for frame in sent] != [900, 612, 900]:
        msg = f"Unexpected live PNG sizes: {sent}"
        raise AssertionError(msg)
    if (tuple(fig.get_size_inches()), fig.dpi) != original:
        msg = "Live redraw changed source Figure dimensions"
        raise AssertionError(msg)
    (directory / "finished").write_text("ready\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if output_dir := os.getenv("WSKR_GUI_LOG_DIR"):
            Path(output_dir, "python-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
