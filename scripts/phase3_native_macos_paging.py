"""Native macOS Kitty foreground paging, resize and screen-restoration acceptance.

Run only in a disposable Kitty window, with the window picker and macOS dialogs.
The plotting child alone consumes canonical Kitty input. The coordinating
parent only reads a private event pipe; no synthetic keyboard input is sent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import select
import shutil
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import asdict
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import numpy as np
from PIL import Image

from scripts.phase3_native_macos_resize import _capture, _clear_scrollback, _dialog, _geometry, _save, _until_valid
from wskr.render.matplotlib.sheet import plan_sheet_pages

if TYPE_CHECKING:
    from wskr.terminal.profile import Geometry

_COLORS = (
    ("#ed2444", (237, 36, 68)),
    ("#238cdb", (35, 140, 219)),
    ("#37bb67", (55, 187, 103)),
    ("#e98a28", (233, 138, 40)),
    ("#984bd5", (152, 75, 213)),
    ("#27b5ae", (39, 181, 174)),
    ("#d8cd39", (216, 205, 57)),
    ("#cb598c", (203, 89, 140)),
    ("#879de8", (135, 157, 232)),
)
_MIN_START_WIDTH = 950
_MIN_START_HEIGHT = 420
_MAX_START_HEIGHT = 650
_MIN_SMALL_WIDTH = 500
_MAX_SMALL_WIDTH = 760
_MIN_COLOR_PIXELS = 1300
_MAX_UNEXPECTED_PIXELS = 600
_MAX_SIGNAL_SECONDS = 100


def _worker_argv(event_fd: int, directory: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "scripts.phase3_native_macos_paging",
        "--worker",
        "--event-fd",
        str(event_fd),
        "--directory",
        str(directory.resolve()),
    ]


def _figures_on_page(geometry: Geometry, page_index: int) -> list[int]:
    plan = plan_sheet_pages(len(_COLORS), geometry)
    selection = plan.page_slice(min(page_index, plan.total_pages - 1))
    return list(range(selection.start, min(selection.stop, len(_COLORS))))


def _color_pixels(path: Path) -> list[int]:
    """Count solid tile colors in a screenshot; content ordering still needs review."""
    with Image.open(path) as source:
        pixels = np.asarray(source.convert("RGB"), dtype=np.int16)
    return [
        int(np.count_nonzero(np.all(np.abs(pixels - np.asarray(rgb)) <= 12, axis=2)))
        for _, rgb in _COLORS
    ]


def _check_page(report: dict, stage: dict, index: int) -> None:
    visible = _figures_on_page(_geometry_from_stage(stage), index)
    stage["expected_figures"] = visible
    stage["color_pixels"] = _color_pixels(Path(stage["screenshot"]))
    for number, count in enumerate(stage["color_pixels"]):
        if number in visible and count < _MIN_COLOR_PIXELS:
            report["failures"].append(f"{stage['stage']}: expected figure {number + 1}, got {count} pixels")
        if number not in visible and count > _MAX_UNEXPECTED_PIXELS:
            report["failures"].append(f"{stage['stage']}: unexpected figure {number + 1}, got {count} pixels")


def _geometry_from_stage(stage: dict) -> Geometry:
    from wskr.terminal.profile import Geometry  # ruff: ignore[import-outside-top-level]

    return Geometry(**stage["geometry"])


def _take_page(report: dict, directory: Path, stage: str, page_index: int) -> None:
    evidence = _capture(report, directory, stage)
    _check_page(report, evidence, page_index)
    _save(report, directory)


def _wait_event(fd: int, expected: bytes, *, timeout: float = _MAX_SIGNAL_SECONDS) -> None:
    """Receive one frame/restore marker from the worker's private pipe only."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if select.select([fd], [], [], remaining)[0]:
            signal_byte = os.read(fd, 1)
            if signal_byte == expected:
                return
            msg = f"Expected worker event {expected!r}, received {signal_byte!r}"
            raise RuntimeError(msg)
    msg = f"Worker did not send {expected!r} within the bounded GUI interaction window"
    raise TimeoutError(msg)


def _worker(directory: Path, event_fd: int) -> None:
    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    from wskr.protocol.kitty_native import NativeKittyTransport  # ruff: ignore[import-outside-top-level]

    plt.ioff()
    figures = []
    original = []
    for number, (color, _) in enumerate(_COLORS, start=1):
        fig = plt.figure(figsize=(3, 2), dpi=80, facecolor=color)
        fig.text(0.5, 0.5, f"Figure {number}", fontsize=32, ha="center", va="center", color="white")
        figures.append(fig)
        original.append((tuple(fig.get_size_inches()), fig.dpi))

    events: dict = {"frames": [], "finished": False}
    target = directory / "worker.json"
    original_send = NativeKittyTransport.send_image

    def record(transport: NativeKittyTransport, png: bytes) -> None:
        geometry = _geometry()
        with Image.open(BytesIO(png)) as image:
            raster = image.size
        if not 0 < raster[0] <= geometry.width_px or not 0 < raster[1] <= geometry.height_px:
            msg = f"Blocking contact sheet {raster} exceeds {geometry}"
            raise AssertionError(msg)
        original_send(transport, png)
        events["frames"].append({
            "raster": list(raster),
            "geometry": asdict(geometry),
            "sha256": hashlib.sha256(png).hexdigest(),
        })
        target.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
        os.write(event_fd, b"F")

    try:
        with patch.object(NativeKittyTransport, "send_image", record):
            # The real foreground terminal delivers actual n/p/Enter lines.
            plt.show(block=True)
        for fig, prior in zip(figures, original, strict=True):
            if (tuple(fig.get_size_inches()), fig.dpi) != prior:
                msg = "Blocking contact sheet mutated source figsize or DPI"
                raise AssertionError(msg)
        events["finished"] = True
        target.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
        print("WSKR_PAGING_DONE", flush=True)
        os.write(event_fd, b"R")
    finally:
        os.close(event_fd)
        plt.close("all")


def _start_geometry() -> Geometry:
    return _until_valid(
        "Set Kitty at least 950 physical pixels wide and 420-650 pixels high; click Continue",
        lambda g: g.width_px >= _MIN_START_WIDTH and _MIN_START_HEIGHT <= g.height_px <= _MAX_START_HEIGHT,
    )


def _small_geometry() -> Geometry:
    return _until_valid(
        "Shrink Kitty to 500-760 physical pixels wide, keeping height at 420-650 px; click Continue",
        lambda g: _MIN_SMALL_WIDTH <= g.width_px <= _MAX_SMALL_WIDTH
        and _MIN_START_HEIGHT <= g.height_px <= _MAX_START_HEIGHT,
    )


def _run_sequence(fd: int, directory: Path, report: dict) -> None:
    _wait_event(fd, b"F")
    _take_page(report, directory, "initial_page", 0)

    _dialog("Click Continue, then focus Kitty and type n followed by Enter.")
    _wait_event(fd, b"F")
    _take_page(report, directory, "next_page", 1)

    _dialog("Click Continue, then focus Kitty and type p followed by Enter.")
    _wait_event(fd, b"F")
    _take_page(report, directory, "previous_page", 0)

    _dialog("Shrink Kitty to 500-760 px wide and 420-650 px high, then click Continue.")
    _small_geometry()
    _wait_event(fd, b"F")
    _take_page(report, directory, "resized_page", 0)

    _dialog("Click Continue, focus Kitty and type n followed by Enter at the narrow size.")
    _wait_event(fd, b"F")
    _take_page(report, directory, "next_page_small", 1)

    _dialog("Expand Kitty beyond 950 px wide, keep 420-650 px high, then click Continue.")
    _start_geometry()
    _wait_event(fd, b"F")
    _take_page(report, directory, "expanded_page", 1)

    _dialog("Click Continue, focus Kitty and press Enter on a BLANK input line to close paging.")
    _wait_event(fd, b"R")
    _take_page(report, directory, "restored_primary", -1)


def _main_parent(directory: Path, mode: str) -> int:
    directory.mkdir(parents=True, exist_ok=False)
    report: dict = {
        "mode": mode,
        "mode_is_label_only": True,
        "macos": platform.mac_ver()[0],
        "input_owner": "foreground_plotting_child",
        "stages": [],
        "failures": [],
        "visual_review_required": True,
        "passed_protocol_checks": False,
    }
    _save(report, directory)
    _start_geometry()
    _clear_scrollback()
    print("WSKR_PAGING_PRIMARY_SENTINEL", flush=True)
    _take_page(report, directory, "primary_before", -1)
    read_fd, write_fd = os.pipe()
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(  # ruff: ignore[subprocess-without-shell-equals-true] - direct local module child
            _worker_argv(write_fd, directory),
            pass_fds=(write_fd,),
        )
        os.close(write_fd)
        _run_sequence(read_fd, directory, report)
        code = process.wait(timeout=10)
        if code != 0:
            report["failures"].append(f"Plotting worker exited {code}")
        else:
            worker = json.loads((directory / "worker.json").read_text(encoding="utf-8"))
            report["worker"] = worker
            if not worker["finished"] or len(worker["frames"]) != 6:
                report["failures"].append("Expected six contact-sheet frames and a completed blocking session")
            if worker["frames"]:
                if worker["frames"][0]["geometry"]["width_px"] <= worker["frames"][3]["geometry"]["width_px"]:
                    report["failures"].append("Narrowing the terminal did not reduce measured raster width")
    except BaseException:
        (directory / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        report["failures"].append("Paging GUI coordination failed; see error.txt")
    finally:
        os.close(read_fd)
        if process is None:
            os.close(write_fd)
        elif process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
        report["passed_protocol_checks"] = not report["failures"]
        _save(report, directory)

    archive = shutil.make_archive(str(directory), "zip", root_dir=directory)
    if report["failures"]:
        print(f"FAILED native paging acceptance: {report['failures']}; evidence: {archive}", file=sys.stderr)
        return 1
    print(f"PROTOCOL + SCREENSHOT PIXEL CHECKS PASSED: {directory / 'report.json'}")
    print(f"Evidence archive: {archive}")
    print("Review all screenshots, especially prompt overlay and primary-screen restoration.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("unmanaged", "yabai"), required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--event-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--directory", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "darwin" or not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("This test requires native macOS with a foreground interactive Kitty TTY")
    if not (os.getenv("KITTY_WINDOW_ID") or os.getenv("TERM") == "xterm-kitty"):
        parser.error("Run inside a Kitty window")
    if os.getenv("WSKR_FIT") != "contain":
        parser.error("Use WSKR_FIT=contain")
    if args.worker:
        if args.directory is None or args.event_fd is None:
            parser.error("Worker requires --event-fd and --directory")
        try:
            _worker(args.directory, args.event_fd)
        except BaseException:
            (args.directory / "worker-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        return 0
    directory = Path("artifacts/phase3-native-paging") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{args.mode}"
    )
    return _main_parent(directory, args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
