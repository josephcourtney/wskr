"""Native macOS Kitty acceptance for the explicitly owned live Matplotlib viewport.

Run in a fresh Kitty window from the repository root:

    WSKR_FIT=contain MPLBACKEND=wskr_kitty uv run python \
        scripts/phase3_owned_live_native_acceptance.py --mode unmanaged --height 2

Repeat for height 6 and mode yabai. Mode labels evidence only; it does not
change yabai configuration. Prompts use native dialogs; screenshots capture
only the Kitty window. Artifacts include PNGs, geometry, and a ZIP archive.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed local command argv
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
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from wskr.protocol.kitty_native import NativeKittyTransport
from wskr.render.matplotlib.live import owned_viewport
from wskr.terminal.profile import read_geometry

if TYPE_CHECKING:
    from collections.abc import Callable

    from wskr.render.matplotlib.live import LiveViewport
    from wskr.terminal.profile import Geometry

_MIN_START_WIDTH = 950
_MAX_SMALL_WIDTH = 790
_MIN_START_HEIGHT = 650
_MIN_SMALL_HEIGHT = 320
_MIN_REDRAW_WIDTH_CHANGE = 80
_MIN_VISIBLE_PIXELS = 800
_MAX_BLACK_FRACTION = 0.95
_NEAR_BLACK = 15
_MAX_CAPTURE_ATTEMPTS = 3
_RED_THRESHOLD = 215
_OTHER_THRESHOLD = 55
_TALL_FIGURE_HEIGHT = 6
_EXPECTED_FRAME_COUNT = 3


def pixel_counts(path: Path) -> dict[str, int | float]:
    """Compute red/blue coverage and detect nearly blank picker captures."""
    with Image.open(path) as image:
        array = np.asarray(image.convert("RGB"))
    r, g, b = array[..., 0], array[..., 1], array[..., 2]
    return {
        "red": int(np.count_nonzero((r > _RED_THRESHOLD) & (g < _OTHER_THRESHOLD) & (b < _OTHER_THRESHOLD))),
        "blue": int(np.count_nonzero((b > _RED_THRESHOLD) & (r < _OTHER_THRESHOLD) & (g < _OTHER_THRESHOLD))),
        "near_black_fraction": round(float(np.mean(np.max(array, axis=2) <= _NEAR_BLACK)), 5),
    }


def visible_bars(measurement: dict[str, int | float]) -> bool:
    return min(int(measurement["red"]), int(measurement["blue"])) >= _MIN_VISIBLE_PIXELS


def _command(argv: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed local argv
        argv, check=False, capture_output=True, text=True, timeout=timeout
    )


def _dialog(message: str) -> None:
    quoted = message.replace("\\", "\\\\").replace('"', '\\"')
    script = f'display dialog "{quoted}" buttons {{"Cancel", "Continue"}} default button "Continue"'
    result = _command(["/usr/bin/osascript", "-e", script])
    if result.returncode or "button returned:Continue" not in result.stdout:
        msg = f"Native macOS dialog cancelled: {result.stderr.strip()}"
        raise RuntimeError(msg)


def _geometry() -> Geometry:
    geometry = read_geometry()
    if geometry is None or min(geometry.rows, geometry.columns, geometry.width_px, geometry.height_px) <= 0:
        msg = "Kitty did not report valid cell and pixel geometry"
        raise RuntimeError(msg)
    return geometry


def _wait_geometry(predicate: Callable[[Geometry], bool], message: str) -> Geometry:
    for _attempt in range(8):
        measurement = _geometry()
        if predicate(measurement):
            return measurement
        _dialog(message + f" (currently {measurement.width_px}x{measurement.height_px} physical px)")
    msg = "Requested Kitty window size was not reached"
    raise RuntimeError(msg)


def _capture(directory: Path, stage: str) -> dict:
    """Capture selected Kitty window; keep rejected black-picker artifacts."""
    target = directory / f"{stage}.png"
    for attempt in range(1, _MAX_CAPTURE_ATTEMPTS + 1):
        result = _command(["/usr/sbin/screencapture", "-x", "-i", "-w", "-o", str(target)])
        if result.returncode or not target.is_file():
            msg = f"Screenshot cancelled/denied at {stage}: {result.stderr.strip()}"
            raise RuntimeError(msg)
        counts = pixel_counts(target)
        if counts["near_black_fraction"] < _MAX_BLACK_FRACTION:
            return {"stage": stage, "screenshot": str(target), "colors": counts, "geometry": asdict(_geometry())}
        target.rename(directory / f"{stage}.invalid-{attempt}.png")
        if attempt < _MAX_CAPTURE_ATTEMPTS:
            _dialog("Blank screenshot detected. Click Continue, then select the Kitty window.")
    msg = f"All {stage} screenshot captures were nearly black"
    raise RuntimeError(msg)


def _save(directory: Path, report: dict) -> None:
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _record_stage(directory: Path, report: dict, stage: str, *, expect_visible: bool) -> None:
    evidence = _capture(directory, stage)
    counts = evidence["colors"]
    if expect_visible and not visible_bars(counts):
        report["failures"].append(f"{stage}: red/blue bars not both visible: {counts}")
    report["stages"].append(evidence)
    _save(directory, report)


def _poll_for_redraw(view: LiveViewport, frames: list[dict], expected: int) -> None:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if view.poll_resize() and len(frames) >= expected:
            break
        time.sleep(0.05)
    if len(frames) != expected:
        msg = f"Expected {expected} transmitted frames, received {len(frames)}"
        raise AssertionError(msg)


def _versions() -> dict:
    versions: dict[str, str] = {"macos": platform.mac_ver()[0]}
    for program in ("kitty", "yabai"):
        if shutil.which(program):
            result = _command([program, "--version"], timeout=5)
            versions[program] = (result.stdout or result.stderr).strip()[:200]
    return versions


def _probe_unowned() -> int:
    """Probe same-TTY ownership with redirected stdin and stdout."""
    fig = Figure(figsize=(3, 2), dpi=100)
    FigureCanvasAgg(fig)
    try:
        with owned_viewport(fig):
            pass
    except RuntimeError as exc:
        if "foreground" in str(exc).lower() or "tty" in str(exc).lower():
            return 0
        return 2
    return 3


def _check_unowned() -> None:
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed interpreter and script
        [sys.executable, str(Path(__file__).resolve()), "--probe-unowned"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if result.returncode or b"\x1b" in result.stdout or b"\x1b" in result.stderr:
        msg = (
            f"Redirected/background TTY rejection failed: return code {result.returncode}; "
            f"output {result.stdout!r} {result.stderr!r}"
        )
        raise AssertionError(msg)


def _make_figure(height: int) -> Figure:
    fig = Figure(figsize=(9, height), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.bar([1, 2], [3, 4], color=("red", "blue"), width=0.65)
    ax.set(xlim=(0.2, 2.8), ylim=(0, 5), title="wskr owned live viewport native acceptance")
    return fig


def _run(directory: Path, mode: str, height: int) -> dict:
    report: dict = {
        "mode": mode,
        "mode_is_label_only": True,
        "height_inches": height,
        "versions": _versions(),
        "frames": [],
        "stages": [],
        "failures": [],
        "human_review_required": True,
        "protocol_passed": False,
    }
    _save(directory, report)
    _check_unowned()
    _record_stage(directory, report, "primary_before", expect_visible=False)
    _wait_geometry(
        lambda g: g.width_px >= _MIN_START_WIDTH and g.height_px >= _MIN_START_HEIGHT,
        "Enlarge test Kitty to at least 950x650 physical pixels and click Continue",
    )

    fig = _make_figure(height)
    original = (tuple(fig.get_size_inches()), fig.dpi)
    original_send = NativeKittyTransport.send_image

    def record(transport: NativeKittyTransport, png: bytes) -> None:
        with Image.open(BytesIO(png)) as image:
            size = image.size
        geometry = _geometry()
        if not (0 < size[0] <= geometry.width_px and 0 < size[1] <= geometry.height_px):
            msg = f"PNG {size} exceeds measured viewport {geometry}"
            raise AssertionError(msg)
        original_send(transport, png)
        report["frames"].append({"raster": list(size), "geometry": asdict(geometry)})
        _save(directory, report)

    with patch.object(NativeKittyTransport, "send_image", record), owned_viewport(fig) as screen:
        if len(report["frames"]) != 1:
            msg = "Expected exactly one initial PNG upload"
            raise AssertionError(msg)
        _record_stage(directory, report, "initial", expect_visible=True)
        minimum_height = 500 if height == _TALL_FIGURE_HEIGHT else _MIN_SMALL_HEIGHT
        _dialog(
            "Shrink Kitty below 790 physical pixels wide while keeping at least "
            + str(minimum_height)
            + " pixels high. Click Continue when ready."
        )
        _wait_geometry(
            lambda g: g.width_px < _MAX_SMALL_WIDTH and g.height_px >= minimum_height,
            f"Resize Kitty below 790 px wide and at least {minimum_height} px high; click Continue",
        )
        _poll_for_redraw(screen, report["frames"], 2)
        _record_stage(directory, report, "resized", expect_visible=True)
        _dialog("Expand Kitty above 950 physical pixels wide; click Continue")
        _wait_geometry(
            lambda g: g.width_px >= _MIN_START_WIDTH,
            "Expand Kitty beyond 950 physical pixels wide; click Continue",
        )
        _poll_for_redraw(screen, report["frames"], 3)
        _record_stage(directory, report, "expanded", expect_visible=True)

    _record_stage(directory, report, "primary_restored", expect_visible=False)
    frames = report["frames"]
    if len(frames) != _EXPECTED_FRAME_COUNT:
        report["failures"].append(f"Expected 3 PNGs, got {len(frames)}")
    else:
        a, b, c = (f["raster"][0] for f in frames)
        if a - b <= _MIN_REDRAW_WIDTH_CHANGE or c - b <= _MIN_REDRAW_WIDTH_CHANGE:
            report["failures"].append(f"PNG did not shrink and grow as expected: {[a, b, c]}")
    if (tuple(fig.get_size_inches()), fig.dpi) != original:
        report["failures"].append("Matplotlib Figure dimensions or DPI mutated")
    baseline = report["stages"][0]["colors"]
    restored = report["stages"][-1]["colors"]
    for color in ("red", "blue"):
        if restored[color] > baseline[color] + max(800, int(report["stages"][1]["colors"][color]) // 5):
            report["failures"].append(f"Possible residual plotted {color} pixels in restored primary screen")
    report["protocol_passed"] = not report["failures"]
    _save(directory, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("unmanaged", "yabai"), default="unmanaged")
    parser.add_argument("--height", choices=(2, 6), type=int, default=2)
    parser.add_argument("--output", type=Path, default=Path("artifacts/phase3-owned-live-native"))
    parser.add_argument("--probe-unowned", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.probe_unowned:
        return _probe_unowned()
    if sys.platform != "darwin" or not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("Run interactively in a native macOS Kitty terminal")
    if not (os.getenv("KITTY_WINDOW_ID") or os.getenv("TERM") == "xterm-kitty"):
        parser.error("Run inside Kitty; this test does not support other terminals")
    if os.getenv("WSKR_FIT", "").lower() != "contain":
        parser.error("Set WSKR_FIT=contain")

    directory = args.output / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{args.mode}-h{args.height}")
    directory.mkdir(parents=True, exist_ok=False)
    result = 1
    try:
        report = _run(directory, args.mode, args.height)
        if not report["failures"]:
            result = 0
    except BaseException:  # ruff: ignore[blind-except] - archive all native GUI failures, including Ctrl-C
        (directory / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
    archive = shutil.make_archive(str(directory), "zip", root_dir=directory)
    print(f"Native owned viewport evidence: {archive}")
    if result:
        print("Automated acceptance FAILED; inspect report.json and error.txt", file=sys.stderr)
    else:
        print("Automated checks PASSED; manually inspect placement and restoration screenshots")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
