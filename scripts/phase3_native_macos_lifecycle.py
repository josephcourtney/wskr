"""Native Kitty acceptance for a two-figure event pump and explicit close.

Run in a fresh *disposable* macOS Kitty window. Erases this window's
scrollback, captures window-only screenshots and never reads keyboard input.
The mode label does not independently attest actual yabai management.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed local child argv
import sys
import traceback
from dataclasses import asdict
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

from PIL import Image

from scripts.phase3_native_macos_resize import _capture, _clear_scrollback, _geometry, _save

if TYPE_CHECKING:
    from wskr.render.matplotlib.kitty import KittyFigureManager

_VISIBLE_PIXELS = 800


def _assess_stage(report: dict, stage: dict, *, red: bool, blue: bool) -> None:
    """Record visual failures without losing subsequent evidence."""
    for color, expected in (("red", red), ("blue", blue)):
        count = stage["colors"][color]
        if expected and count < _VISIBLE_PIXELS:
            report["visual_failures"].append(f"{stage['stage']}: missing {color} figure ({count} pixels)")
        if not expected and count >= _VISIBLE_PIXELS:
            report["visual_failures"].append(f"{stage['stage']}: closed {color} figure remains ({count} pixels)")


def _record_stage(report: dict, directory: Path, stage: str, *, red: bool, blue: bool) -> None:
    result = _capture(report, directory, stage)
    _assess_stage(report, result, red=red, blue=blue)
    _save(report, directory)


def _require_uploads(report: dict, expected: dict[str, int], stage: str) -> None:
    if report["uploads"] != expected:
        msg = f"{stage}: expected uploads {expected}, observed {report['uploads']}"
        raise AssertionError(msg)


def _worker(directory: Path, mode: str) -> None:  # ruff: ignore[too-many-statements] - linear GUI test transcript
    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]

    from wskr.protocol.kitty_native import NativeKittyTransport  # ruff: ignore[import-outside-top-level]

    report: dict = {
        "mode": mode,
        "macos": platform.mac_ver()[0],
        "kitty_version": os.getenv("KITTY_VERSION", "unknown"),
        "anchor_mode": os.getenv("WSKR_KITTY_ANCHOR", "physical"),
        "idle_redraw": os.getenv("WSKR_IDLE_REDRAW"),
        "geometry": asdict(_geometry()),
        "stages": [],
        "uploads": {"red": 0, "blue": 0},
        "frames": [],
        "resources": [],
        "visual_failures": [],
        "passed_protocol_checks": False,
        "visual_review_required": True,
    }
    _save(report, directory)
    _clear_scrollback()
    plt.ioff()

    red_fig, red_ax = plt.subplots(figsize=(5, 2), dpi=100)
    blue_fig, blue_ax = plt.subplots(figsize=(5, 2), dpi=100)
    red_bar = red_ax.bar([0], [3], color="red", width=0.8)[0]
    blue_bar = blue_ax.bar([0], [4], color="blue", width=0.8)[0]
    for axes, title in ((red_ax, "Red figure"), (blue_ax, "Blue figure")):
        axes.set_xlim(-0.5, 0.5)
        axes.set_ylim(0, 5)
        axes.set_title(title)

    figures = {"red": red_fig, "blue": blue_fig}
    # The backend-specific manager transport is intentionally inspected only
    # within this acceptance harness, never presented as a public API.
    transports = {label: cast("KittyFigureManager", fig.canvas.manager).transport for label, fig in figures.items()}
    labels = {id(transport): label for label, transport in transports.items()}
    original = {label: (tuple(fig.get_size_inches()), fig.dpi) for label, fig in figures.items()}
    original_send = NativeKittyTransport.send_anchored_image

    def record(transport: NativeKittyTransport, png: bytes) -> None:
        label = labels[id(transport)]
        with Image.open(BytesIO(png)) as image:
            width, height = image.size
        geometry = _geometry()
        if not 0 < width <= geometry.width_px or not 0 < height <= geometry.height_px:
            msg = f"{label} raster {width}x{height} exceeds measured {geometry}"
            raise AssertionError(msg)
        original_send(transport, png)
        report["uploads"][label] += 1
        report["frames"].append({"figure": label, "raster": [width, height], "geometry": asdict(geometry)})
        _save(report, directory)

    def resources(stage: str) -> None:
        report["resources"].append({
            "stage": stage,
            "active_images": {label: len(transport.manager._images) for label, transport in transports.items()},  # ruff: ignore[private-member-access] - test-only owned resource inspection
        })
        _save(report, directory)

    try:
        with patch.object(NativeKittyTransport, "send_anchored_image", record):
            plt.show(block=False)
            _require_uploads(report, {"red": 1, "blue": 1}, "initial")
            resources("initial")
            _record_stage(report, directory, "initial", red=True, blue=True)

            # A single canvas flush must service two independent figures.
            plt.ion()
            red_bar.set_height(4)
            blue_bar.set_height(2)
            red_fig.canvas.draw_idle()
            blue_fig.canvas.draw_idle()
            _require_uploads(report, {"red": 1, "blue": 1}, "queued")
            red_fig.canvas.flush_events()
            _require_uploads(report, {"red": 2, "blue": 2}, "pumped")
            resources("pumped")
            _record_stage(report, directory, "pumped", red=True, blue=True)

            plt.close(red_fig)
            resources("after_red_close")
            _record_stage(report, directory, "after_red_close", red=False, blue=True)

            plt.close(blue_fig)
            resources("after_blue_close")
            _record_stage(report, directory, "after_blue_close", red=False, blue=False)
    finally:
        plt.close("all")
        plt.ioff()

    for label, fig in figures.items():
        if (tuple(fig.get_size_inches()), fig.dpi) != original[label]:
            msg = f"{label}: source figure dimensions or DPI changed"
            raise AssertionError(msg)
    for state in report["resources"]:
        stage = state["stage"]
        expected = {
            "red": 0 if stage in {"after_red_close", "after_blue_close"} else 2,
            "blue": 0 if stage == "after_blue_close" else 2,
        }
        if state["active_images"] != expected:
            msg = f"{stage}: active images {state['active_images']} != {expected}"
            raise AssertionError(msg)
    report["passed_protocol_checks"] = True
    _save(report, directory)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("unmanaged", "yabai"), required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    if sys.platform != "darwin" or not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("Run inside an interactive native macOS Kitty TTY")
    if not (os.getenv("KITTY_WINDOW_ID") or os.getenv("TERM") == "xterm-kitty"):
        parser.error("Run inside a real Kitty window")
    if os.getenv("WSKR_FIT") != "contain" or os.getenv("WSKR_IDLE_REDRAW") != "coalesce":
        parser.error("Require WSKR_FIT=contain and WSKR_IDLE_REDRAW=coalesce")
    if args.worker:
        if args.directory is None:
            parser.error("--worker requires --directory")
        try:
            _worker(args.directory, args.mode)
        except BaseException:
            (args.directory / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        return 0

    directory = Path("artifacts/phase3-native-lifecycle") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{args.mode}-{os.getenv('WSKR_KITTY_ANCHOR', 'physical')}"
    )
    directory.mkdir(parents=True, exist_ok=False)
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed local argv
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--mode",
            args.mode,
            "--directory",
            str(directory.resolve()),
        ],
        check=False,
    )
    if completed.returncode:
        archive = shutil.make_archive(str(directory), "zip", root_dir=directory)
        print(f"FAILED: plotting child returned {completed.returncode}; evidence: {archive}", file=sys.stderr)
        return 1
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    _record_stage(report, directory, "after_child_exit", red=False, blue=False)
    archive = shutil.make_archive(str(directory), "zip", root_dir=directory)
    if report["visual_failures"]:
        print(f"FAILED VISUAL ACCEPTANCE: {report['visual_failures']}; evidence: {archive}", file=sys.stderr)
        return 1
    print(f"PROTOCOL + SCREENSHOT PIXEL CHECKS PASSED: {directory / 'report.json'}")
    print(f"Evidence archive: {archive}")
    print("Review screenshots and capture the returned shell prompt separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
