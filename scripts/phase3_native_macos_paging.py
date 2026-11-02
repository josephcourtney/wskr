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
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed module child on the caller's foreground TTY
import sys
import time
import traceback
from dataclasses import asdict
from datetime import UTC, datetime
from io import BytesIO
from itertools import product
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
_MIN_USABLE_WIDTH = 400
_MIN_USABLE_HEIGHT = 240
_SHRINK_FRACTION = 0.85
_RESTORE_FRACTION = 0.85
_MIN_COLOR_PIXELS = 1300
_MAX_UNEXPECTED_PIXELS = 600
_MAX_SIGNAL_SECONDS = 100
_COLOR_TOLERANCE = 80
_SCREENSHOT_SAMPLE_STEP = 2
_GENERATED_CHANNEL_LEVELS = (64, 96, 128, 160, 192, 224, 255)
_MIN_GENERATED_BRIGHTNESS = 192
_EXPECTED_FRAMES = 6
_MIN_TILE_CHANNEL_SPREAD = 80
_MIN_TERMINAL_ROWS = 4


def _palette(count: int) -> tuple[tuple[str, tuple[int, int, int]], ...]:
    """Generate widely separated bright colors for arbitrary page capacities."""
    colors = list(_COLORS)
    if count <= len(colors):
        return tuple(colors[:count])
    candidates = [
        (red, green, blue)
        for red, green, blue in product(_GENERATED_CHANNEL_LEVELS, repeat=3)
        if max(red, green, blue) >= _MIN_GENERATED_BRIGHTNESS
        and max(red, green, blue) - min(red, green, blue) >= _MIN_TILE_CHANNEL_SPREAD
    ]
    while len(colors) < count and candidates:

        def separation(rgb: tuple[int, int, int]) -> int:
            return min(sum((a - b) ** 2 for a, b in zip(rgb, previous, strict=True)) for _, previous in colors)

        rgb = max(candidates, key=separation)
        candidates.remove(rgb)
        colors.append((f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}", rgb))
    if len(colors) != count:
        msg = f"Not enough distinct test colors for {count} figures"
        raise ValueError(msg)
    return tuple(colors)


def _figure_count(geometry: Geometry) -> int:
    """Ensure more test figures than can fit on the initial page."""
    return max(len(_COLORS), plan_sheet_pages(len(_COLORS), geometry).page_size + 2)


def _worker_argv(
    event_fd: int, directory: Path, figure_count: int = len(_COLORS), *, mode: str = "unmanaged"
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "scripts.phase3_native_macos_paging",
        "--mode",
        mode,
        "--worker",
        "--event-fd",
        str(event_fd),
        "--directory",
        str(directory.resolve()),
        "--figure-count",
        str(figure_count),
    ]


def _figures_on_page(geometry: Geometry, page_index: int, count: int = len(_COLORS)) -> list[int]:
    plan = plan_sheet_pages(count, geometry)
    selection = plan.page_slice(page_index)
    return list(range(selection.start, min(selection.stop, count)))


def _color_pixels(path: Path, count: int = len(_COLORS)) -> list[int]:
    """Classify screenshot tiles by nearest RGB color with conversion tolerance.

    Native macOS captures can transform source PNG colors through a display
    profile. Exact RGB comparisons falsely call visibly present panels absent.
    Assign each sampled pixel to its one nearest palette color, so expanded
    tolerances cannot double-count adjacent colors or ordinary terminal text.
    """
    with Image.open(path) as source:
        pixels = np.asarray(source.convert("RGB"))[::_SCREENSHOT_SAMPLE_STEP, ::_SCREENSHOT_SAMPLE_STEP].astype(
            np.int16
        )
    best_squared = np.full(pixels.shape[:2], _COLOR_TOLERANCE**2 + 1, dtype=np.int32)
    best_index = np.full(pixels.shape[:2], -1, dtype=np.int16)
    for index, (_, rgb) in enumerate(_palette(count)):
        delta = pixels.astype(np.int32) - np.asarray(rgb, dtype=np.int32)
        squared = np.sum(delta * delta, axis=2, dtype=np.int32)
        selected = (squared < best_squared) & (squared <= _COLOR_TOLERANCE**2)
        best_squared[selected] = squared[selected]
        best_index[selected] = index
    counts = np.bincount(best_index[best_index >= 0], minlength=count)
    return (counts * _SCREENSHOT_SAMPLE_STEP**2).tolist()


def _check_page(report: dict, stage: dict, index: int) -> None:
    count = report.get("figure_count", len(_COLORS))
    visible = _figures_on_page(_geometry_from_stage(stage), index, count)
    stage["expected_figures"] = visible
    stage["color_pixels"] = _color_pixels(Path(stage["screenshot"]), count)
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
    if page_index >= 0:
        _check_page(report, evidence, page_index)
    else:
        evidence["color_pixels"] = _color_pixels(Path(evidence["screenshot"]), report.get("figure_count", len(_COLORS)))
        if any(count > _MAX_UNEXPECTED_PIXELS for count in evidence["color_pixels"]):
            report["failures"].append(f"{stage}: contact-sheet tile remained on the primary screen")
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
            if signal_byte == b"F":
                continue  # A delayed resize event is not a completed restore.
            msg = f"Expected worker event {expected!r}, received {signal_byte!r}"
            raise RuntimeError(msg)
    msg = f"Worker did not send {expected!r} within the bounded GUI interaction window"
    raise TimeoutError(msg)


def _latest_frame(directory: Path) -> dict | None:
    """Read the latest complete native render receipt, if available."""
    path = directory / "worker.json"
    if not path.is_file():
        return None
    try:
        frames = json.loads(path.read_text(encoding="utf-8"))["frames"]
    except (OSError, json.JSONDecodeError, KeyError):
        return None
    return frames[-1] if frames else None


def _drain_events(fd: int) -> None:
    """Discard obsolete resize signals without reading Kitty stdin."""
    while select.select([fd], [], [], 0)[0]:
        if not os.read(fd, 4096):
            return


def _wait_render(fd: int, directory: Path, prior: str, geometry: Geometry | None = None) -> dict:
    """Match a new PNG receipt, not an arbitrary queued resize notification."""
    deadline = time.monotonic() + _MAX_SIGNAL_SECONDS
    while time.monotonic() < deadline:
        frame = _latest_frame(directory)
        if frame is not None and frame["sha256"] != prior:
            measured = frame["geometry"]
            if geometry is None or (
                measured["width_px"] == geometry.width_px and measured["height_px"] == geometry.height_px
            ):
                _drain_events(fd)
                return frame
        remaining = deadline - time.monotonic()
        if remaining > 0 and select.select([fd], [], [], min(1.0, remaining))[0]:
            received = os.read(fd, 4096)
            if not received:
                msg = "Plotting child closed before expected new page PNG"
                raise RuntimeError(msg)
            if b"R" in received:
                msg = "Plotting child restored the terminal before the expected page render"
                raise RuntimeError(msg)
    msg = "No matching new page PNG was transmitted after the requested navigation or resize"
    raise TimeoutError(msg)


def _worker(directory: Path, event_fd: int, figure_count: int) -> None:
    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    from wskr.protocol.kitty_native import NativeKittyTransport  # ruff: ignore[import-outside-top-level]

    plt.ioff()
    figures = []
    original = []
    for number, (color, _) in enumerate(_palette(figure_count), start=1):
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
    """Require only an ordinary usable Kitty window, not an exact height."""
    return _until_valid(
        "Use any normally sized Kitty window (at least 400x240 terminal pixels); click Continue",
        lambda g: (
            g.width_px >= _MIN_USABLE_WIDTH and g.height_px >= _MIN_USABLE_HEIGHT and g.rows >= _MIN_TERMINAL_ROWS
        ),
    )


def _small_geometry(initial: Geometry) -> Geometry:
    """Accept any substantial width reduction; ignore cell-step rounding."""
    target = round(initial.width_px * _SHRINK_FRACTION)
    return _until_valid(
        f"Make Kitty noticeably narrower (measured width below {target} px); height may stay unchanged",
        lambda g: g.width_px <= target and g.height_px >= _MIN_USABLE_HEIGHT and g.rows >= _MIN_TERMINAL_ROWS,
    )


def _expanded_geometry(initial: Geometry) -> Geometry:
    """Accept approximate restoration without requiring exact pixel dimensions."""
    target = round(initial.width_px * _RESTORE_FRACTION)
    return _until_valid(
        f"Expand Kitty toward its original width (at least {target} measured px)",
        lambda g: g.width_px >= target and g.height_px >= _MIN_USABLE_HEIGHT and g.rows >= _MIN_TERMINAL_ROWS,
    )


def _run_sequence(fd: int, directory: Path, report: dict) -> None:
    first = _wait_render(fd, directory, "")
    _take_page(report, directory, "initial_page", 0)
    report["stages"][-1]["frame_sha256"] = first["sha256"]

    _dialog("Click Continue, then focus Kitty and type n followed by Enter.")
    next_frame = _wait_render(fd, directory, first["sha256"])
    _take_page(report, directory, "next_page", 1)
    report["stages"][-1]["frame_sha256"] = next_frame["sha256"]

    _dialog("Click Continue, then focus Kitty and type p followed by Enter.")
    previous = _wait_render(fd, directory, next_frame["sha256"])
    _take_page(report, directory, "previous_page", 0)
    report["stages"][-1]["frame_sha256"] = previous["sha256"]

    _dialog("Make Kitty substantially narrower; you may leave its height unchanged. Click Continue after resizing.")
    narrow = _small_geometry(_geometry_from_stage(report["stages"][0]))
    report["narrow_geometry"] = asdict(narrow)
    report["narrow_page_capacity"] = plan_sheet_pages(report["figure_count"], narrow).page_size
    report["page_capacity_changed"] = report["narrow_page_capacity"] != report["initial_page_capacity"]
    resized = _wait_render(fd, directory, previous["sha256"], narrow)
    _take_page(report, directory, "resized_page", 0)
    report["stages"][-1]["frame_sha256"] = resized["sha256"]

    _dialog("Click Continue, focus Kitty and type n followed by Enter at the narrow size.")
    small_next = _wait_render(fd, directory, resized["sha256"])
    _take_page(report, directory, "next_page_small", 1)
    report["stages"][-1]["frame_sha256"] = small_next["sha256"]

    _dialog("Expand Kitty approximately to its original width; its height need not change.")
    large = _expanded_geometry(_geometry_from_stage(report["stages"][0]))
    expanded = _wait_render(fd, directory, small_next["sha256"], large)
    _take_page(report, directory, "expanded_page", 1)
    report["stages"][-1]["frame_sha256"] = expanded["sha256"]

    _dialog("Click Continue, focus Kitty and press Enter on a BLANK input line to close paging.")
    _wait_event(fd, b"R")
    _take_page(report, directory, "restored_primary", -1)


def _validate_worker(report: dict, worker: dict) -> None:
    """Reject incomplete child evidence while permitting intermediate drag redraws."""
    report["worker"] = worker
    frames = worker["frames"]
    if not worker["finished"] or len(frames) < _EXPECTED_FRAMES:
        report["failures"].append("Expected at least six contact-sheet frames and a completed blocking session")
        return
    first = frames[0]
    smallest_viewport = min(frame["geometry"]["width_px"] for frame in frames)
    smallest_raster = min(frame["raster"][0] for frame in frames)
    if first["geometry"]["width_px"] <= smallest_viewport:
        report["failures"].append("Narrowing the terminal did not reduce measured viewport width")
    if first["raster"][0] <= smallest_raster:
        report["failures"].append("Narrowing the terminal did not reduce transmitted PNG width")


def _finish_child(process: subprocess.Popen[bytes], fd: int, directory: Path, report: dict) -> None:
    """Complete the GUI transcript and qualify transmitted pages."""
    _run_sequence(fd, directory, report)
    code = process.wait(timeout=10)
    if code != 0:
        report["failures"].append(f"Plotting worker exited {code}")
        return
    _validate_worker(report, json.loads((directory / "worker.json").read_text(encoding="utf-8")))


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
    initial = _start_geometry()
    report["initial_geometry"] = asdict(initial)
    report["figure_count"] = _figure_count(initial)
    report["initial_page_capacity"] = plan_sheet_pages(report["figure_count"], initial).page_size
    _palette(report["figure_count"])
    _clear_scrollback()
    print("WSKR_PAGING_PRIMARY_SENTINEL", flush=True)
    _take_page(report, directory, "primary_before", -1)
    read_fd, write_fd = os.pipe()
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(  # ruff: ignore[subprocess-without-shell-equals-true] - direct local module child
            _worker_argv(write_fd, directory, report["figure_count"], mode=mode),
            pass_fds=(write_fd,),
        )
        os.close(write_fd)
        _finish_child(process, read_fd, directory, report)
    except (
        OSError,
        ValueError,
        AssertionError,
        RuntimeError,
        TimeoutError,
        KeyboardInterrupt,
        subprocess.SubprocessError,
    ):
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


def _argument_parser() -> argparse.ArgumentParser:
    """Expose identical parent and worker argument validation for tests."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("unmanaged", "yabai"), required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--event-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--figure-count", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--directory", type=Path, help=argparse.SUPPRESS)
    return parser


def main() -> int:
    parser = _argument_parser()
    args = parser.parse_args()
    if sys.platform != "darwin" or not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("This test requires native macOS with a foreground interactive Kitty TTY")
    if not (os.getenv("KITTY_WINDOW_ID") or os.getenv("TERM") == "xterm-kitty"):
        parser.error("Run inside a Kitty window")
    if os.getenv("WSKR_FIT") != "contain":
        parser.error("Use WSKR_FIT=contain")
    if args.worker:
        if args.directory is None or args.event_fd is None or args.figure_count is None:
            parser.error("Worker requires --event-fd, --directory and --figure-count")
        try:
            _worker(args.directory, args.event_fd, args.figure_count)
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
