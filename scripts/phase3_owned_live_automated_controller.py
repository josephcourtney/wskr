"""Drive owned-live macOS Kitty GUI acceptance without dialogs or manual resizing.

Launches a *dedicated* Kitty OS window/socket for each case. Kitty remote
control captures only this instance's screen; yabai cases use yabai resizing
rather than pretending that Kitty can override a managed tiling layout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed local process commands
import sys
import tempfile
import time
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from collections.abc import Sequence

_WIDTH_SMALL = 720
_WIDTH_LARGE = 1200
_HEIGHT_SMALL = {2: 500, 6: 740}
_HEIGHT_LARGE = 1000
_TALL_FIGURE_HEIGHT = 6
_MARKER_TIMEOUT = 40.0
_REMOTE_TIMEOUT = 20.0
_POLL_INTERVAL = 0.1
_RED_THRESHOLD = 215
_OTHER_THRESHOLD = 55
_MIN_BAR_PIXELS = 800
_RESIZE_DELTA = 80
_MAX_BLACK_FRACTION = 0.98
_NEAR_BLACK_THRESHOLD = 15
_EXPECTED_FRAMES = 3
_FIGURE_WIDTH = 900
_MIN_WIDE_WIDTH = 950
_MAX_NARROW_WIDTH = 790
_MIN_NARROW_WIDTH = 440
_MAX_RESIZE_ATTEMPTS = 3


class AcceptanceError(RuntimeError):
    """Failure or unsupported GUI environment, with preserved evidence."""


def _run(argv: list[str], *, timeout: int = 20) -> str:
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed command argv
        argv, capture_output=True, text=True, check=False, timeout=timeout
    )
    if completed.returncode:
        msg = f"Command failed ({completed.returncode}): {argv!r}: {completed.stderr.strip()}"
        raise AcceptanceError(msg)
    return completed.stdout.strip()


def _remote(socket: str, *args: str) -> str:
    return _run(["kitten", "@", "--to", socket, *args], timeout=int(_REMOTE_TIMEOUT))


def _await(path: Path, *, timeout: float = _MARKER_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(_POLL_INTERVAL)
    msg = f"Worker did not reach {path.name}"
    raise AcceptanceError(msg)


def _signal(directory: Path, marker: str) -> None:
    (directory / marker).write_text("ready\n", encoding="utf-8")


def _window_id(socket: str) -> int:
    """Resolve the single terminal window in our isolated Kitty socket."""
    layouts = json.loads(_remote(socket, "ls"))
    windows = [window for os_window in layouts for tab in os_window["tabs"] for window in tab["windows"]]
    if len(windows) != 1:
        msg = f"Expected one isolated Kitty window, found {len(windows)}"
        raise AcceptanceError(msg)
    return int(windows[0]["id"])


def _wait_window_id(socket: str) -> int:
    deadline = time.monotonic() + _MARKER_TIMEOUT
    while time.monotonic() < deadline:
        try:
            return _window_id(socket)
        except (AcceptanceError, OSError, ValueError, KeyError, json.JSONDecodeError):
            time.sleep(_POLL_INTERVAL)
    msg = "Kitty remote socket did not expose the test window"
    raise AcceptanceError(msg)


def _capture(socket: str, window_id: int, path: Path) -> dict[str, int | float]:
    """Use Kitty's native OS-window screenshot; no macOS picker or accessibility."""
    _remote(socket, "screenshot", "--match", f"id:{window_id}", str(path))
    with Image.open(path) as image:
        pixels = np.asarray(image.convert("RGB"))
    r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    return {
        "width_px": int(pixels.shape[1]),
        "height_px": int(pixels.shape[0]),
        "red": int(np.count_nonzero((r > _RED_THRESHOLD) & (g < _OTHER_THRESHOLD) & (b < _OTHER_THRESHOLD))),
        "blue": int(np.count_nonzero((b > _RED_THRESHOLD) & (r < _OTHER_THRESHOLD) & (g < _OTHER_THRESHOLD))),
        "black_fraction": round(float(np.mean(np.max(pixels, axis=2) < _NEAR_BLACK_THRESHOLD)), 5),
    }


def _query_yabai(title: str) -> dict:
    windows = json.loads(_run(["yabai", "-m", "query", "--windows"]))
    matches = [entry for entry in windows if entry.get("title") == title and entry.get("app", "").lower() == "kitty"]
    if len(matches) != 1:
        msg = f"yabai cannot uniquely identify the Kitty window ({len(matches)} matches)"
        raise AcceptanceError(msg)
    return matches[0]


def _resize(
    socket: str,
    window_id: int,
    title: str,
    *,
    mode: str,
    small: bool,
    height: int,
    requested_width: int | None = None,
) -> str:
    width = requested_width if requested_width is not None else (_WIDTH_SMALL if small else _WIDTH_LARGE)
    wanted_height = _HEIGHT_SMALL[height] if small else _HEIGHT_LARGE
    if mode == "unmanaged":
        _remote(
            socket,
            "resize-os-window",
            "--match",
            f"id:{window_id}",
            "--unit",
            "pixels",
            "--width",
            str(width),
            "--height",
            str(wanted_height),
        )
        return "kitty_remote"

    window = _query_yabai(title)
    identifier = str(window["id"])
    if window.get("is-floating", False):
        _run(["yabai", "-m", "window", identifier, "--resize", f"abs:{width}:{wanted_height}"])
        return "yabai_float_absolute"
    if window.get("is-managed", False):
        # BSP layout owns dimensions. Change its split ratio; the measured
        # result is checked below, not assumed to be the requested size.
        _run(["yabai", "-m", "window", identifier, "--ratio", "abs:0.30" if small else "abs:0.70"])
        return "yabai_bsp_ratio"
    msg = "yabai sees the Kitty window but reports neither floating nor BSP-managed"
    raise AcceptanceError(msg)


def _wait_new_width(socket: str, window_id: int, prior_width: int, *, smaller: bool, out: Path) -> dict:
    deadline = time.monotonic() + 15
    last: dict = {}
    while time.monotonic() < deadline:
        last = _capture(socket, window_id, out)
        width = int(last["width_px"])
        if smaller and width <= prior_width - _RESIZE_DELTA:
            return last
        if not smaller and width >= prior_width + _RESIZE_DELTA:
            return last
        time.sleep(0.2)
    msg = f"Window did not {'shrink' if smaller else 'expand'} enough; prior={prior_width}, last={last}"
    raise AcceptanceError(msg)


def _calibrated_request(*, requested: int, observed: int, target: int) -> int:
    """Convert a target screenshot width to Kitty/yabai OS-size units.

    Retina and window chrome make requested sizes differ from Kitty screenshot
    pixels. Use measured output rather than assuming a scale of 1 or 2.
    """
    if min(requested, observed, target) <= 0:
        msg = "Window resize calibration requires positive measured dimensions"
        raise ValueError(msg)
    return max(180, round(requested * target / observed))


def _resize_to_fit(
    socket: str,
    window_id: int,
    title: str,
    *,
    mode: str,
    height: int,
    wide_measurement: dict,
    out: Path,
) -> list[dict]:
    """Target a narrow physical viewport through iterative resizing."""
    prior_width = int(wide_measurement["width_px"])
    request = _calibrated_request(requested=_WIDTH_LARGE, observed=prior_width, target=_WIDTH_SMALL)
    attempts: list[dict] = []
    previous_request = _WIDTH_LARGE
    for attempt in range(_MAX_RESIZE_ATTEMPTS):
        method = _resize(socket, window_id, title, mode=mode, small=True, height=height, requested_width=request)
        measured = _wait_new_width(socket, window_id, prior_width, smaller=request < previous_request, out=out)
        width = int(measured["width_px"])
        info = {"attempt": attempt + 1, "method": method, "requested_width": request, "observed_width_px": width}
        attempts.append(info)
        if _MIN_NARROW_WIDTH <= width < _MAX_NARROW_WIDTH:
            height_px = int(measured["height_px"])
            minimum_height = 500 if height == _TALL_FIGURE_HEIGHT else 320
            if height_px < minimum_height:
                msg = f"Window too short at {width}x{height_px} physical px; expected height >= {minimum_height}"
                raise AcceptanceError(msg)
            return attempts
        if mode == "yabai" and method == "yabai_bsp_ratio":
            break  # exact width is controlled by yabai's surrounding layout
        previous_request = request
        request = _calibrated_request(requested=request, observed=width, target=_WIDTH_SMALL)
        prior_width = width
    msg = f"Could not reach a fitted physical width < {_MAX_NARROW_WIDTH} px: {attempts}"
    raise AcceptanceError(msg)


def _save(directory: Path, report: dict) -> None:
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _stage(directory: Path, report: dict, socket: str, window_id: int, name: str, *, visible: bool) -> dict:
    measurements = _capture(socket, window_id, directory / f"{name}.png")
    report["stages"].append({"stage": name, **measurements})
    if measurements["black_fraction"] > _MAX_BLACK_FRACTION:
        report["failures"].append(f"{name}: nearly black screenshot")
    if visible and min(int(measurements["red"]), int(measurements["blue"])) < _MIN_BAR_PIXELS:
        report["failures"].append(f"{name}: plot not visible: {measurements}")
    _save(directory, report)
    return measurements


def _verify(report: dict, directory: Path) -> None:
    frames = json.loads((directory / "worker-report.json").read_text(encoding="utf-8"))["frames"]
    report["frames"] = frames
    if len(frames) != _EXPECTED_FRAMES:
        report["failures"].append(f"Expected three PNGs, got {len(frames)}")
        return
    widths = [int(frame["raster"][0]) for frame in frames]
    if widths[0] - widths[1] < _RESIZE_DELTA or widths[2] - widths[1] < _RESIZE_DELTA:
        report["failures"].append(f"Raster did not shrink and expand: {widths}")
    if widths[0] != _FIGURE_WIDTH or widths[2] != _FIGURE_WIDTH:
        report["failures"].append(f"Expected full-size 900-pixel PNG at both wide stages: {widths}")
    before = report["stages"][0]
    restored = report["stages"][-1]
    for color in ("red", "blue"):
        if int(restored[color]) > int(before[color]) + _MIN_BAR_PIXELS:
            report["failures"].append(f"Residual {color} plot pixels after restoring main screen")


def _exercise_case(directory: Path, report: dict, socket: str, title: str, mode: str, height: int) -> None:
    """Drive the controller/worker stages using the selected window-management policy."""
    _await(directory / "launch.ready")
    window_id = _wait_window_id(socket)
    report["kitty_window_id"] = window_id
    if mode == "yabai":
        report["yabai_initial"] = _query_yabai(title)
    # Initial resize happens before any plotted image is transmitted.
    method = _resize(socket, window_id, title, mode=mode, small=False, height=height)
    report["steps"].append({"stage": "initial_resize", "method": method})
    time.sleep(0.5)
    primary = _stage(directory, report, socket, window_id, "primary_before", visible=False)
    if int(primary["width_px"]) < _MIN_WIDE_WIDTH:
        msg = f"Initial OS window is too narrow for an unfitted 900px image: {primary}"
        raise AcceptanceError(msg)
    _signal(directory, "launch.proceed")
    _await(directory / "initial.ready")
    initial = _stage(directory, report, socket, window_id, "initial", visible=True)
    attempts = _resize_to_fit(
        socket,
        window_id,
        title,
        mode=mode,
        height=height,
        wide_measurement=initial,
        out=directory / "resize_probe.png",
    )
    report["steps"].append({"stage": "small_resize", "attempts": attempts})
    _signal(directory, "small.proceed")
    _await(directory / "resized.ready")
    resized = _stage(directory, report, socket, window_id, "resized", visible=True)
    method = _resize(socket, window_id, title, mode=mode, small=False, height=height)
    report["steps"].append({"stage": "large_resize", "method": method})
    _wait_new_width(socket, window_id, int(resized["width_px"]), smaller=False, out=directory / "expand_probe.png")
    _signal(directory, "large.proceed")
    _await(directory / "expanded.ready")
    _stage(directory, report, socket, window_id, "expanded", visible=True)
    _signal(directory, "exit.proceed")
    _await(directory / "finished")
    _stage(directory, report, socket, window_id, "primary_restored", visible=False)
    if mode == "yabai":
        report["yabai_final"] = _query_yabai(title)
    _verify(report, directory)


def _case(root: Path, output: Path, mode: str, height: int) -> Path:
    label = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = output / f"{label}-{mode}-h{height}-{uuid.uuid4().hex[:8]}"
    directory.mkdir(parents=True)
    # macOS AF_UNIX socket paths are short (typically 104 bytes maximum).
    # Do not place the socket beneath the potentially long evidence path.
    socket_path = Path(tempfile.gettempdir()) / f"wskr-{uuid.uuid4().hex[:12]}.sock"
    socket = f"unix:{socket_path}"
    title = f"wskr-accept-{uuid.uuid4().hex[:12]}"
    report: dict = {"mode": mode, "height_inches": height, "title": title, "steps": [], "stages": [], "failures": []}
    _save(directory, report)
    worker = [
        "kitty",
        "--config",
        "NONE",
        "--hold",
        "--title",
        title,
        "--listen-on",
        socket,
        "-o",
        "allow_remote_control=socket-only",
        sys.executable,
        str(root / "scripts/phase3_owned_live_automated_worker.py"),
        "--directory",
        str(directory),
        "--height",
        str(height),
    ]
    env = os.environ.copy()
    env["WSKR_FIT"] = "contain"
    # Only one Kitty instance, not a shell subprocess, owns the graphical TTY.
    proc: subprocess.Popen[bytes] | None = None
    try:
        with (directory / "kitty-launch.log").open("wb") as log:
            proc = subprocess.Popen(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed worker argv
                worker, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT
            )
        _exercise_case(directory, report, socket, title, mode, height)
    except BaseException:  # ruff: ignore[blind-except] - always archive failed native runs
        report["failures"].append("Controller exception; see controller-error.txt")
        (directory / "controller-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        report["passed"] = not report["failures"]
        _save(directory, report)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        socket_path.unlink(missing_ok=True)
        shutil.make_archive(str(directory), "zip", root_dir=directory)
    return directory


def _yabai_status() -> str | None:
    """Return a diagnostic when yabai is installed but its socket is not available."""
    if not shutil.which("yabai"):
        return "yabai executable not found"
    try:
        reply = _run(["yabai", "-m", "query", "--windows"], timeout=5)
        if not isinstance(json.loads(reply), list):
            return "yabai returned unexpected window-query data"
    except (AcceptanceError, subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as exc:
        return f"yabai service unavailable: {exc}"
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("unmanaged", "yabai", "all"), default="all")
    parser.add_argument("--height", choices=(2, 6), type=int)
    parser.add_argument("--output", type=Path, default=Path("artifacts/phase3-owned-live-native-auto"))
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        parser.error("Native macOS only")
    if not shutil.which("kitty") or not shutil.which("kitten"):
        parser.error("Kitty and its kitten remote client must be installed")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    modes = ("unmanaged", "yabai") if args.mode == "all" else (args.mode,)
    heights = (args.height,) if args.height is not None else (2, 6)
    cases = [(mode, height) for mode in modes for height in heights]
    results: list[dict] = []
    yabai_error = _yabai_status() if "yabai" in modes else None
    for mode, height in cases:
        if mode == "yabai" and yabai_error:
            result = {"case": f"{mode}-h{height}", "status": "SKIP", "reason": yabai_error}
            print(f"SKIP {mode}-h{height}: {yabai_error}")
        else:
            directory = _case(root, output, mode, height)
            report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
            result = {
                "case": f"{mode}-h{height}",
                "status": "PASS" if report["passed"] else "FAIL",
                "archive": str(directory) + ".zip",
            }
            print(f"{result['status']} {mode}-h{height}: {directory}.zip")
        results.append(result)
    summary_path = output / f"summary-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    summary_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Consolidated results: {summary_path}")
    # A skipped required case is incomplete, never a false positive PASS.
    return 0 if all(result["status"] == "PASS" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
