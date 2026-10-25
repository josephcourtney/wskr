"""Native macOS Kitty window-resize acceptance; explicitly requires visual screenshots.

Run in a fresh Kitty window:
    WSKR_FIT=contain uv run python scripts/phase3_native_macos_resize.py --mode unmanaged --height 2

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


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(report: dict, directory: Path) -> None:
    (directory / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")


def _colors(path: Path) -> dict[str, int]:
    with Image.open(path) as source:
        pixels = np.asarray(source.convert("RGB"))
    r, g, b = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
    return {
        "red": int(np.count_nonzero((r > _RED_THRESHOLD) & (g < _OTHER_THRESHOLD) & (b < _OTHER_THRESHOLD))),
        "blue": int(np.count_nonzero((b > _RED_THRESHOLD) & (r < _OTHER_THRESHOLD) & (g < _OTHER_THRESHOLD))),
    }


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
    return "".join(
        f"WSKR_HISTORY_{index:04d} " + "=" * (_HISTORY_PAYLOAD_WIDTH - 18) + "\n"
        for index in range(lines)
    )


def _seed_history(lines: int) -> None:
    """Populate only the disposable diagnostic terminal, before any figure."""
    text = _history_fixture(lines)
    if text:
        sys.stdout.write(text)
        sys.stdout.flush()


def _screenshot(directory: Path, stage: str) -> dict:
    path = directory / f"{stage}.png"
    for attempt in range(_SCREENSHOT_ATTEMPTS):
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed argv
            ["/usr/sbin/screencapture", "-x", "-i", "-w", "-o", str(path)],
            check=False,
            timeout=180,
        )
        if completed.returncode or not path.is_file():
            msg = f"Kitty-window screenshot failed or was cancelled ({stage}). Check Screen Recording permission."
            raise RuntimeError(msg)
        if not _mostly_black(path):
            return {"stage": stage, "screenshot": str(path), "colors": _colors(path)}
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
    """Use a separate native GUI prompt so plot anchors do not scroll."""
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
        with Image.open(BytesIO(png)) as image:
            size = image.size
        geometry = _geometry()
        if not 0 < size[0] <= geometry.width_px or not 0 < size[1] <= geometry.height_px:
            msg = f"Raster {size} exceeds viewport {geometry}"
            raise AssertionError(msg)
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
        _record_visibility(report, _capture(report, directory, "resized"))

        _dialog("Expand Kitty above 950 physical px wide; click Continue")
        _until_valid(
            "Expand Kitty beyond 950 physical px wide; click Continue", lambda g: g.width_px >= _MIN_START_WIDTH
        )
        _pump(fig, report["frames"], 3)
        _record_visibility(report, _capture(report, directory, "expanded"))

    _verify_source(fig, report["frames"], original)
    report["passed_protocol_checks"] = True
    _save(report, directory)


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
    if not 0 <= args.history_lines <= _MAX_HISTORY_LINES:
        parser.error(f"--history-lines must be between 0 and {_MAX_HISTORY_LINES}")
    if args.history_lines and not args.clean_scrollback:
        parser.error("--history-lines requires --clean-scrollback in a disposable Kitty window")
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

    directory = Path("artifacts/phase3-native-resize") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + f"-{args.mode}-h{args.height}"
        + ("-clean" if args.clean_scrollback else "")
        + (f"-history{args.history_lines}" if args.history_lines else "")
    )
    directory.mkdir(parents=True, exist_ok=False)
    print(f"Evidence directory: {directory}")
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - direct child, inherited TTY
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--mode",
            args.mode,
            "--height",
            str(args.height),
            "--directory",
            str(directory.resolve()),
            *(["--clean-scrollback"] if args.clean_scrollback else []),
            *(["--history-lines", str(args.history_lines)] if args.history_lines else []),
        ],
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
