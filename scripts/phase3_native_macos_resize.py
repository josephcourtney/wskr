"""Native macOS Kitty window-resize acceptance; explicitly requires visual screenshots.

Run in a fresh Kitty window:
    WSKR_FIT=contain uv run python -m scripts.phase3_native_macos_resize --mode unmanaged --height 2

Only the selected Kitty *window* is captured. Screen Recording permission
may be required. The parent process captures the retained image after the
plotting child interpreter exits; no editor, heredoc, or pasted source code
is displayed inside the terminal.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed local subprocess argv
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

from scripts import phase3_native_control_bridge as native_control
from scripts.phase3_screenshot_color import read_screenshot_srgb

if TYPE_CHECKING:
    from collections.abc import Callable

    from matplotlib.figure import Figure

    from wskr.terminal.profile import Geometry


_VISIBLE_PIXELS = 800
_MIN_START_WIDTH = 950
_MAX_SMALL_WIDTH = 790
_MIN_SMALL_HEIGHT = 320
_MIN_START_HEIGHT = 650
_MIN_RASTER_CHANGE = 80
_RED_THRESHOLD = 215
_OTHER_THRESHOLD = 55
_NEAR_BLACK_MAX = 15
_MAX_BLANK_FRACTION = 0.95
_SCREENSHOT_ATTEMPTS = 3
_MAX_HISTORY_LINES = 200
_HISTORY_PAYLOAD_WIDTH = 112
_HISTORY_GLYPH_ROWS = 8
_HISTORY_GLYPH_PIXELS = 70
_HISTORY_GLYPH_CONTRAST = 70
_HISTORY_NEUTRAL_CHANNEL_SPREAD = 45
_HISTORY_MAX_GLYPH_RUN_FRACTION = 0.22


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(report: dict, directory: Path) -> None:
    (directory / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")


def _colors(path: Path) -> dict[str, int]:
    pixels, _ = read_screenshot_srgb(path)
    r, g, b = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
    return {
        "red": int(np.count_nonzero((r > _RED_THRESHOLD) & (g < _OTHER_THRESHOLD) & (b < _OTHER_THRESHOLD))),
        "blue": int(np.count_nonzero((b > _RED_THRESHOLD) & (r < _OTHER_THRESHOLD) & (g < _OTHER_THRESHOLD))),
    }


def _history_text_below_plot(path: Path, *, cell_height_px: float, raster_width: int) -> bool:
    """Flag probable seeded-history overlap that simple bar-pixel counts miss.

    The fixture emits all history *before* the plot and emits no later text.
    Rows resembling text beneath the lowest bars therefore indicate that
    history has reflowed into the figure's location. This conservative check
    only detects a subset of overlaps; manual screenshot review remains
    mandatory.
    """
    pixels, _ = read_screenshot_srgb(path)
    pixels = pixels.astype(np.int16)
    red, green, blue = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
    bars = ((red > _RED_THRESHOLD) & (green < _OTHER_THRESHOLD) & (blue < _OTHER_THRESHOLD)) | (
        (blue > _RED_THRESHOLD) & (red < _OTHER_THRESHOLD) & (green < _OTHER_THRESHOLD)
    )
    colored_rows = np.flatnonzero(np.any(bars, axis=1))
    if not colored_rows.size:
        return False  # Existing visibility check already rejects absent bars.
    bottom = int(colored_rows[-1]) + max(8, int(cell_height_px / 2))
    background = np.median(pixels[: min(40, pixels.shape[0]), pixels.shape[1] // 2 :, :], axis=(0, 1))
    neutral = np.max(pixels, axis=2) - np.min(pixels, axis=2) < _HISTORY_NEUTRAL_CHANNEL_SPREAD
    high_contrast = np.max(np.abs(pixels - background), axis=2) > _HISTORY_GLYPH_CONTRAST
    likely_text_rows = 0
    for row in (neutral & high_contrast)[bottom:]:
        if np.count_nonzero(row) < _HISTORY_GLYPH_PIXELS:
            continue
        edges = np.diff(np.r_[False, row, False].astype(np.int8))
        runs = np.flatnonzero(edges == -1) - np.flatnonzero(edges == 1)
        if runs.size and np.max(runs) < raster_width * _HISTORY_MAX_GLYPH_RUN_FRACTION:
            likely_text_rows += 1
            if likely_text_rows >= _HISTORY_GLYPH_ROWS:
                return True
    return False


def _record_history_order(report: dict, stage: dict) -> None:
    """Fail seeded-history acceptance if text is visible below the plot.

    This catches the native macOS Kitty 0.49.2 yabai 9x2 / 96-line case,
    where both plot colors remain visible but a reflowed history line appears
    below the image. Non-detection does not prove prompt-safe placement.
    """
    if report.get("history_lines", 0) == 0 or stage["stage"] != "resized":
        return
    frame = report["frames"][-1]
    metrics = frame["geometry"]
    if _history_text_below_plot(
        Path(stage["screenshot"]),
        cell_height_px=metrics["height_px"] / metrics["rows"],
        raster_width=frame["raster"][0],
    ):
        stage["history_after_plot"] = True
        report.setdefault("visual_failures", []).append(
            "resized: probable reflowed history text below/behind the plot; inspect the screenshot for overlap"
        )


def _mostly_black(path: Path) -> bool:
    """Identify invalid black captures, not ordinary dark terminal backgrounds."""
    with Image.open(path) as source:
        pixels = np.asarray(source.convert("RGB"))
    return bool(np.mean(np.max(pixels, axis=2) <= _NEAR_BLACK_MAX) > _MAX_BLANK_FRACTION)


def _clear_scrollback() -> None:
    """Destructively reset scrollback only in the explicitly opted-in test."""
    sys.stdout.flush()
    os.write(sys.stdout.fileno(), b"\x1b[3J\x1b[2J\x1b[H")


def _history_fixture(lines: int) -> str:
    """Deterministic long lines that reflow after a narrow window resize."""
    if not 0 <= lines <= _MAX_HISTORY_LINES:
        msg = f"History fixture must contain 0-{_MAX_HISTORY_LINES} lines"
        raise ValueError(msg)
    return "".join(f"WSKR_HISTORY_{index:04d} " + "=" * (_HISTORY_PAYLOAD_WIDTH - 18) + "\n" for index in range(lines))


def _seed_history(lines: int) -> None:
    """Populate only the disposable diagnostic terminal, before any figure."""
    text = _history_fixture(lines)
    if text:
        sys.stdout.write(text)
        sys.stdout.flush()


def _screenshot(directory: Path, stage: str) -> dict:
    path = directory / f"{stage}.png"
    for attempt in range(_SCREENSHOT_ATTEMPTS):
        if native_control.enabled():
            native_control.request("capture", stage=stage, path=str(path.resolve()))
            succeeded = path.is_file()
        else:
            completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed argv
                ["/usr/sbin/screencapture", "-x", "-i", "-w", "-o", str(path)],
                check=False,
                timeout=180,
            )
            succeeded = completed.returncode == 0 and path.is_file()
        if not succeeded:
            msg = f"Kitty-window screenshot failed or was cancelled ({stage}). Check Screen Recording permission."
            raise RuntimeError(msg)
        if not _mostly_black(path):
            return {
                "stage": stage,
                "screenshot": str(path),
                "colors": _colors(path),
                "color_capture": read_screenshot_srgb(path)[1],
            }
        path.rename(directory / f"{stage}.invalid-{attempt + 1}.png")
        if attempt + 1 < _SCREENSHOT_ATTEMPTS:
            _dialog("Blank screenshot captured; select the visible Kitty window and click Continue")
    msg = f"{stage}: three blank screenshots; invalid captures are retained for inspection."
    raise RuntimeError(msg)


def _visible(stage: dict) -> None:
    if min(stage["colors"].values()) < _VISIBLE_PIXELS:
        msg = f"{stage['stage']}: red and blue bars are not both visible; see {stage['screenshot']}"
        raise AssertionError(msg)


def _record_visibility(report: dict, stage: dict) -> None:
    """Record a visual failure and keep running to capture recovery evidence."""
    try:
        _visible(stage)
    except AssertionError as exc:
        report.setdefault("visual_failures", []).append(str(exc))


def _geometry() -> Geometry:
    from wskr.terminal.profile import read_geometry  # ruff: ignore[import-outside-top-level]

    geometry = read_geometry()
    if geometry is None or min(geometry.rows, geometry.columns, geometry.width_px, geometry.height_px) <= 0:
        msg = "Attached Kitty did not report valid cell and pixel geometry."
        raise RuntimeError(msg)
    return geometry


def _dialog(prompt: str) -> None:
    """Use GUI prompts manually, or explicit controller checkpoints in automation."""
    if native_control.enabled():
        native_control.request("dialog", prompt=prompt)
        return
    script = f'display dialog "{prompt}" buttons {{"Cancel", "Continue"}} default button "Continue"'
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed argv
        ["/usr/bin/osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    if completed.returncode or "Continue" not in completed.stdout:
        msg = f"Native resize acceptance dialog cancelled or failed: {completed.stderr.strip()}"
        raise RuntimeError(msg)


def _until_valid(prompt: str, predicate: Callable[[Geometry], bool]) -> Geometry:
    for _ in range(6):
        geometry = _geometry()
        if predicate(geometry):
            return geometry
        _dialog(prompt)
    msg = "Requested window geometry was not reached after six attempts."
    raise RuntimeError(msg)


def _capture(report: dict, directory: Path, stage: str) -> dict:
    result = _screenshot(directory, stage)
    result["geometry"] = asdict(_geometry())
    report["stages"].append(result)
    _save(report, directory)
    return result


def _pump(figure: Figure, frames: list[dict], target: int) -> None:
    deadline = time.monotonic() + 5.0
    while len(frames) < target and time.monotonic() < deadline:
        figure.canvas.flush_events()
        time.sleep(0.05)
    if len(frames) != target:
        msg = f"Expected {target} fitted PNG uploads; observed {len(frames)}: {frames}"
        raise AssertionError(msg)


def _verify_source(figure: Figure, frames: list[dict], original: tuple[tuple[float, ...], float]) -> None:
    initial, small, large = (frame["raster"] for frame in frames)
    if not initial[0] - small[0] > _MIN_RASTER_CHANGE or not large[0] - small[0] > _MIN_RASTER_CHANGE:
        msg = f"Expected real fitted raster shrink/re-expansion, got {frames}"
        raise AssertionError(msg)
    if (tuple(figure.get_size_inches()), figure.dpi) != original:
        msg = "Source Matplotlib figure geometry or DPI was changed."
        raise AssertionError(msg)


def _inspect_and_save_frame(directory: Path, index: int, png: bytes, geometry: Geometry) -> tuple[int, int]:
    """Retain the exact transmitted PNG and ensure it fits the measured viewport."""
    with Image.open(BytesIO(png)) as image:
        size = image.size
    if not 0 < size[0] <= geometry.width_px or not 0 < size[1] <= geometry.height_px:
        msg = f"Raster {size} exceeds viewport {geometry}"
        raise AssertionError(msg)
    (directory / f"transmitted-frame-{index}.png").write_bytes(png)
    return size


def _worker(directory: Path, height: int, mode: str, *, clean_scrollback: bool, history_lines: int) -> None:
    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    from wskr.protocol.kitty_native import NativeKittyTransport  # ruff: ignore[import-outside-top-level]

    plt.ioff()
    backend = str(plt.get_backend())
    if backend.lower() != "module://wskr.render.matplotlib.kitty":
        msg = f"Wrong Matplotlib backend: {backend}"
        raise RuntimeError(msg)

    report: dict = {
        "mode": mode,
        "clean_scrollback": clean_scrollback,
        "history_lines": history_lines,
        "history_line_width": _HISTORY_PAYLOAD_WIDTH,
        "placement_contract": "terminal_history",
        "anchor_mode": os.getenv("WSKR_KITTY_ANCHOR", "physical"),
        "height_inches": height,
        "backend": backend,
        "macos": platform.mac_ver()[0],
        "kitty_version": os.getenv("KITTY_VERSION", "unknown"),
        "stages": [],
        "frames": [],
        "visual_failures": [],
        "passed_protocol_checks": False,
        "visual_review_required": True,
    }
    _save(report, directory)

    _until_valid(
        "Enlarge Kitty to at least 950 physical pixels wide and 650 tall; click Continue",
        lambda g: g.width_px >= _MIN_START_WIDTH and g.height_px >= _MIN_START_HEIGHT,
    )

    if clean_scrollback:
        _clear_scrollback()
    _seed_history(history_lines)
    fig, ax = plt.subplots(figsize=(9, height), dpi=100)
    ax.bar([1, 2], [3, 4], color=("red", "blue"))
    ax.set_title("wskr native macOS nonblocking resize")
    original = (tuple(fig.get_size_inches()), fig.dpi)
    send = NativeKittyTransport.send_anchored_image

    def record(transport: NativeKittyTransport, png: bytes) -> None:
        geometry = _geometry()
        size = _inspect_and_save_frame(directory, len(report["frames"]) + 1, png, geometry)
        send(transport, png)
        report["frames"].append({"raster": list(size), "geometry": asdict(geometry)})
        _save(report, directory)

    with patch.object(NativeKittyTransport, "send_anchored_image", record):
        plt.show(block=False)
        if len(report["frames"]) != 1:
            msg = f"Expected initial anchored frame: {report['frames']}"
            raise AssertionError(msg)
        _record_visibility(report, _capture(report, directory, "initial"))

        _dialog("Shrink Kitty below 790 physical px wide, keep above 320 px tall; click Continue")
        _until_valid(
            "Shrink farther (under 790 physical px wide, above 320 px tall); click Continue",
            lambda g: g.width_px < _MAX_SMALL_WIDTH and g.height_px >= _MIN_SMALL_HEIGHT,
        )
        _capture(report, directory, "before_redraw")
        _pump(fig, report["frames"], 2)
        resized = _capture(report, directory, "resized")
        _record_visibility(report, resized)
        _record_history_order(report, resized)

        _dialog("Expand Kitty above 950 physical px wide; click Continue")
        _until_valid(
            "Expand Kitty beyond 950 physical px wide; click Continue", lambda g: g.width_px >= _MIN_START_WIDTH
        )
        _pump(fig, report["frames"], 3)
        _record_visibility(report, _capture(report, directory, "expanded"))

    _verify_source(fig, report["frames"], original)
    report["passed_protocol_checks"] = True
    _save(report, directory)


def _validate_history_args(parser: argparse.ArgumentParser, *, lines: int, clean_scrollback: bool) -> None:
    if not 0 <= lines <= _MAX_HISTORY_LINES:
        parser.error(f"--history-lines must be between 0 and {_MAX_HISTORY_LINES}")
    if lines and not clean_scrollback:
        parser.error("--history-lines requires --clean-scrollback in a disposable Kitty window")


def _worker_argv(directory: Path, *, mode: str, height: int, clean_scrollback: bool, history_lines: int) -> list[str]:
    """Launch the worker as a module so sibling scripts remain importable."""
    return [
        sys.executable,
        "-m",
        "scripts.phase3_native_macos_resize",
        "--worker",
        "--mode",
        mode,
        "--height",
        str(height),
        "--directory",
        str(directory.resolve()),
        *(["--clean-scrollback"] if clean_scrollback else []),
        *(["--history-lines", str(history_lines)] if history_lines else []),
    ]


def _coordinate_window_start(mode: str) -> None:
    """Wait for explicitly requested automatic native window preparation."""
    if native_control.enabled():
        native_control.request("ready", case="resize", mode=mode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("unmanaged", "yabai"), required=True)
    parser.add_argument("--height", type=int, choices=(2, 6), required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--clean-scrollback",
        action="store_true",
        help="Erase terminal scrollback before display; use a disposable Kitty window",
    )
    parser.add_argument(
        "--history-lines",
        type=int,
        default=0,
        help="Controlled long-line terminal history before plotting; requires --clean-scrollback",
    )
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    _validate_history_args(parser, lines=args.history_lines, clean_scrollback=args.clean_scrollback)
    if sys.platform != "darwin" or not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("This acceptance test requires an interactive native macOS Kitty TTY.")
    if os.getenv("WSKR_FIT") != "contain":
        parser.error("Set WSKR_FIT=contain to qualify fitted Kitty rendering.")
    if not (os.getenv("KITTY_WINDOW_ID") or os.getenv("TERM") == "xterm-kitty"):
        parser.error("Run this test inside a real Kitty window (not a non-Kitty terminal).")

    if args.worker:
        if args.directory is None:
            parser.error("--worker requires --directory")
        try:
            _worker(
                args.directory,
                args.height,
                args.mode,
                clean_scrollback=args.clean_scrollback,
                history_lines=args.history_lines,
            )
        except BaseException:
            (args.directory / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        return 0

    _coordinate_window_start(args.mode)
    directory = Path("artifacts/phase3-native-resize") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + f"-{args.mode}-h{args.height}"
        + ("-clean" if args.clean_scrollback else "")
        + (f"-history{args.history_lines}" if args.history_lines else "")
    )
    directory.mkdir(parents=True, exist_ok=False)
    print(f"Evidence directory: {directory}")
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - direct child, inherited TTY
        _worker_argv(
            directory,
            mode=args.mode,
            height=args.height,
            clean_scrollback=args.clean_scrollback,
            history_lines=args.history_lines,
        ),
        check=False,
    )
    if completed.returncode:
        archive = shutil.make_archive(str(directory), "zip", root_dir=directory)
        print(f"FAILED: plotting child exited {completed.returncode}; evidence: {archive}", file=sys.stderr)
        return 1

    report = _read_json(directory / "report.json")
    try:
        _record_visibility(report, _capture(report, directory, "after_python_exit"))
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        archive = shutil.make_archive(str(directory), "zip", root_dir=directory)
        print(f"FAILED: post-exit persistence: {exc}; evidence: {archive}", file=sys.stderr)
        return 1
    _save(report, directory)
    archive = shutil.make_archive(str(directory), "zip", root_dir=directory)
    if report.get("visual_failures"):
        print(
            f"FAILED VISUAL ACCEPTANCE: {len(report['visual_failures'])} stage(s); evidence: {archive}", file=sys.stderr
        )
        return 1
    print(f"PROTOCOL + SCREENSHOT PIXEL CHECKS PASSED: {directory}/report.json")
    print(f"Evidence archive: {archive}")
    print("Review the five Kitty-window screenshots for correct placement, clipping and scrollback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
