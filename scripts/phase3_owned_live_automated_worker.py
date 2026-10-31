"""Worker for fully-automated native Kitty owned-viewport acceptance.

This process runs *inside* the launched Kitty window. It never prompts the user.
A separate controller script resizes the OS window, captures screenshots, and
signals progression through simple marker files.
"""

from __future__ import annotations

import argparse
import json
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
from wskr.render.matplotlib.live import LiveViewport, owned_viewport

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_SMALL_SETTLE_TIMEOUT = 12.0
_POLL_INTERVAL = 0.05
_INITIAL_WIDTH = 900
_EXPECTED_FRAMES = 3


def _await(path: Path, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(_POLL_INTERVAL)
    msg = f"Timed out waiting for {path.name}"
    raise TimeoutError(msg)


def _write(path: Path, text: str = "ready\n") -> None:
    path.write_text(text, encoding="utf-8")


def _save(directory: Path, report: dict) -> None:
    (directory / "worker-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _make_figure(height: int) -> Figure:
    fig = Figure(figsize=(9, height), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.bar([1, 2], [3, 4], color=("red", "blue"), width=0.65)
    ax.set(xlim=(0.2, 2.8), ylim=(0, 5), title="wskr owned live viewport automation")
    return fig


def _poll_until_frame(view: LiveViewport, frames: list[dict], expected_count: int) -> None:
    deadline = time.monotonic() + _SMALL_SETTLE_TIMEOUT
    while time.monotonic() < deadline:
        changed = view.poll_resize()
        if changed and len(frames) >= expected_count:
            return
        time.sleep(_POLL_INTERVAL)
    msg = f"Resize did not produce frame {expected_count}; observed {len(frames)} frame(s)"
    raise TimeoutError(msg)


def _display_session(
    fig: Figure,
    directory: Path,
    report: dict,
    record: Callable[[NativeKittyTransport, bytes], None],
) -> None:
    with patch.object(NativeKittyTransport, "send_image", record), owned_viewport(fig) as view:
        if len(report["frames"]) != 1:
            msg = f"Expected one initial frame, got {len(report['frames'])}"
            raise AssertionError(msg)
        _write(directory / "initial.ready")
        _await(directory / "small.proceed")
        _poll_until_frame(view, report["frames"], 2)
        _write(directory / "resized.ready")
        _await(directory / "large.proceed")
        _poll_until_frame(view, report["frames"], 3)
        _write(directory / "expanded.ready")
        _await(directory / "exit.proceed")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--height", type=int, choices=(2, 6), required=True)
    args = parser.parse_args(argv)

    directory = args.directory
    directory.mkdir(parents=True, exist_ok=True)

    fig = _make_figure(args.height)
    original = (tuple(fig.get_size_inches()), fig.dpi)

    report: dict = {"height_inches": args.height, "frames": []}
    _save(directory, report)

    original_send = NativeKittyTransport.send_image

    def record(transport: NativeKittyTransport, png: bytes) -> None:
        with Image.open(BytesIO(png)) as image:
            size = image.size
        viewport = transport.get_window_size_px()
        if size[0] > viewport[0] or size[1] > viewport[1]:
            msg = f"Rendered PNG {size} exceeds viewport {viewport}"
            raise AssertionError(msg)
        original_send(transport, png)
        report["frames"].append({"raster": list(size), "viewport": list(viewport)})
        _save(directory, report)

    _write(directory / "launch.ready")
    _await(directory / "launch.proceed")

    try:
        _display_session(fig, directory, report, record)
    except BaseException:
        (directory / "worker-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise

    if len(report["frames"]) != _EXPECTED_FRAMES:
        msg = f"Expected {_EXPECTED_FRAMES} frames, got {len(report['frames'])}"
        raise AssertionError(msg)
    if report["frames"][0]["raster"][0] != _INITIAL_WIDTH:
        msg = f"Unexpected initial raster width: {report['frames'][0]['raster'][0]}"
        raise AssertionError(msg)
    if (tuple(fig.get_size_inches()), fig.dpi) != original:
        msg = "Owned viewport mutated the source Figure geometry"
        raise AssertionError(msg)

    _write(directory / "finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
