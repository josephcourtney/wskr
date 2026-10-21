# ruff: file-ignore[subprocess-without-shell-equals-true]  # bounded owned GUI and validation children
"""Run-specific validation evidence: commands, Kitty screenshots, manifest, ZIP.

Screen images are captured from uniquely titled, newly launched Kitty windows.
No unrelated desktop/window fallback is allowed; a missing window is a failure.
A captured screenshot remains *unreviewed*, not evidence of visible plotting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - bounded owned child processes
import sys
import time
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ("check", "phase1", "test-tty", "test-kitty")
SCENARIOS = ("matplotlib", "rich", "noop")
RCPARAM_KEYS = (
    "figure.figsize",
    "figure.dpi",
    "figure.facecolor",
    "axes.facecolor",
    "text.color",
    "axes.labelcolor",
    "savefig.facecolor",
    "savefig.transparent",
)
RCPARAM_CODE = (
    "import json, matplotlib as mpl;"
    f"keys={RCPARAM_KEYS!r};"
    "print(json.dumps({k: {'configured': str(mpl.rcParams[k]),"
    "'default': str(mpl.rcParamsDefault[k])} for k in keys}, indent=2))"
)


def _short_git(*args: str) -> str | None:
    """Read nonsecret repository metadata without inheriting Git subprocess errors."""
    git = shutil.which("git")
    if git is None:
        return None
    result = subprocess.run(
        [git, *args], cwd=ROOT, capture_output=True, text=True, check=False, timeout=10
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _run_logged(command: list[str], log_path: Path, *, timeout: float) -> dict:
    """Persist stdout/stderr and return an exact subprocess outcome."""
    started = time.monotonic()
    try:
        with log_path.open("wb") as stream:
            completed = subprocess.run(
                command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False, timeout=timeout
            )
        return {"status": "passed" if completed.returncode == 0 else "failed", "exit_code": completed.returncode,
                "duration_s": round(time.monotonic() - started, 3), "log": str(log_path.name)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        with log_path.open("ab") as stream:
            stream.write(f"\nEvidence runner error: {exc}\n".encode())
        return {"status": "failed", "error": str(exc), "duration_s": round(time.monotonic() - started, 3),
                "log": str(log_path.name)}


def _find_window(title: str, *, timeout: float) -> int:
    """Resolve a unique, owned window via macOS CoreGraphics (no yabai needed)."""
    swift = shutil.which("swift")
    if swift is None:
        msg = "swift executable unavailable; cannot safely identify Kitty window"
        raise RuntimeError(msg)
    result = subprocess.run(
        [swift, str(ROOT / "scripts" / "find_kitty_window.swift"), title, str(timeout)],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=timeout + 20
    )
    if result.returncode != 0:
        msg = f"Kitty window lookup failed: {result.stderr.strip() or result.stdout.strip()}"
        raise RuntimeError(msg)
    try:
        return int(result.stdout.strip())
    except ValueError as exc:
        msg = f"Unexpected Kitty window identifier: {result.stdout!r}"
        raise RuntimeError(msg) from exc


def _wait_for_render(marker: Path, process: subprocess.Popen, *, timeout: float) -> None:
    """Require the smoke child to finish rendering before taking a screenshot."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() == "render-complete":
            return
        if process.poll() is not None:
            msg = f"Dedicated Kitty process exited before render marker (exit={process.returncode})"
            raise RuntimeError(msg)
        time.sleep(0.2)
    msg = "No render completion marker from dedicated Kitty window"
    raise TimeoutError(msg)


def _stop_owned_process(process: subprocess.Popen) -> None:
    """Close only the dedicated Kitty process launched for this scenario."""
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=4)
    except OSError:
        # The process may already have been reaped or its PID invalidated.
        return


def _validate_png(path: Path) -> tuple[int, int]:
    """Validate complete PNG data and report dimensions, not plotted visibility."""
    from PIL import Image  # ruff: ignore[import-outside-top-level] - only GUI captures need Pillow

    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return image.size


def _capture_scenario(name: str, run_id: str, directory: Path, *, timeout: float) -> dict:
    """Render and capture one independently owned Kitty GUI window."""
    kitty = shutil.which("kitty")
    if kitty is None:
        return {"status": "failed", "error": "kitty executable missing"}
    if platform.system() != "Darwin":
        return {"status": "failed", "error": "macOS screencapture is required"}
    token = f"wskr-{hashlib.sha256(run_id.encode()).hexdigest()[:12]}-{name}"
    marker = directory / f"{name}.ready"
    reference = directory / f"{name}-reference.png"
    screenshot = directory / f"{name}-screen.png"
    launch_log = directory / f"{name}-kitty.log"
    env = dict(os.environ)
    env["WSKR_PROTOCOL"] = "kitty" if name == "rich" else "noop"
    cmd = [
        kitty, "--title", token, "--directory", str(ROOT), "--hold",
        sys.executable, str(ROOT / "scripts" / "phase1_visual_smoke.py"),
        "--mode", name, "--reference", str(reference), "--ready-file", str(marker), "--pause",
    ]
    print(f"[capture] {name}: starting dedicated Kitty window", flush=True)
    process = None
    try:
        with launch_log.open("wb") as stream:
            process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        _wait_for_render(marker, process, timeout=timeout)
        window = _find_window(token, timeout=timeout)
        # A compositor frame is needed after the renderer has returned.
        time.sleep(0.6)
        result = subprocess.run(
            ["/usr/sbin/screencapture", "-x", "-o", "-l", str(window), str(screenshot)],
            capture_output=True, text=True, check=False, timeout=20
        )
        if result.returncode != 0 or not screenshot.is_file():
            msg = f"screencapture failed (exit {result.returncode}): {result.stderr.strip()}"
            raise RuntimeError(msg)
        width, height = _validate_png(screenshot)
        print(f"[capture] {name}: captured {width}x{height} (visual content unreviewed)", flush=True)
        return {"status": "captured_unreviewed", "window_id": window,
                "screenshot": screenshot.name, "reference": reference.name if reference.is_file() else None,
                "size_px": [width, height]}
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        print(f"[capture] {name}: FAILED: {exc}", flush=True)
        return {"status": "failed", "error": str(exc),
                "reference": reference.name if reference.is_file() else None}
    finally:
        try:
            if process is not None:
                _stop_owned_process(process)
        finally:
            marker.unlink(missing_ok=True)


def _file_hashes(directory: Path) -> dict[str, str]:
    """Index immutable evidence files before writing the manifest."""
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }


def _zip_run(directory: Path) -> Path:
    """Archive only this run's regular files in stable path order."""
    dest = directory.with_suffix(".zip")
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=str(path.relative_to(directory)))
    return dest


def collect(
    output_root: Path, *, checks: bool = True, gui: bool = True, timeout: float = 45
) -> tuple[Path, dict]:
    """Always produce a run-specific archive, even after failed validation."""
    started = datetime.now(UTC)
    sha = _short_git("rev-parse", "--short=10", "HEAD") or "unknown"
    run_id = f"{started:%Y%m%dT%H%M%S%fZ}-{sha}-{uuid.uuid4().hex[:6]}"
    folder = output_root.resolve() / run_id
    folder.mkdir(parents=True, exist_ok=False)
    logs = folder / "logs"
    logs.mkdir()
    pictures = folder / "screenshots"
    pictures.mkdir()
    manifest: dict = {
        "run_id": run_id, "started_utc": started.isoformat(),
        "git": {"sha": _short_git("rev-parse", "HEAD"),
                "branch": _short_git("branch", "--show-current"),
                "status_porcelain": _short_git("status", "--porcelain")},
        "environment": {"os": platform.platform(), "python": sys.version.split()[0],
                        "TERM": os.getenv("TERM"), "COLORTERM": os.getenv("COLORTERM"),
                        "WSKR_PROTOCOL": os.getenv("WSKR_PROTOCOL")},
        "checks": {}, "screenshots": {},
    }
    try:
        config = _run_logged([sys.executable, "-c", RCPARAM_CODE], logs / "matplotlib-rcparams.log", timeout=30)
        manifest["matplotlib_rcparams"] = config
        for name in CHECKS:
            if checks:
                print(f"[check] just {name}", flush=True)
                just = shutil.which("just")
                command = [just, name] if just is not None else ["just", name]
                result = _run_logged(command, logs / f"just-{name}.log", timeout=240)
            else:
                result = {"status": "skipped", "reason": "--no-checks"}
            manifest["checks"][name] = result
            print(f"[check] {name}: {result['status']}", flush=True)
        for name in SCENARIOS:
            manifest["screenshots"][name] = (
                _capture_scenario(name, run_id, pictures, timeout=timeout)
                if gui else {"status": "skipped", "reason": "--no-gui"}
            )
    finally:
        manifest["finished_utc"] = datetime.now(UTC).isoformat()
        manifest["file_sha256"] = _file_hashes(folder)
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        archive = _zip_run(folder)
        print(f"Evidence directory: {folder}", flush=True)
        print(f"Evidence ZIP: {archive}", flush=True)
    return archive, manifest


def main(argv: Sequence[str] | None = None) -> int:
    """Collect a full run or a restricted, explicitly labeled subset."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts" / "evidence")
    parser.add_argument("--no-checks", action="store_true", help="Skip automated checks (marked skipped)")
    parser.add_argument("--no-gui", action="store_true", help="Skip screenshots (marked skipped)")
    parser.add_argument("--timeout", type=float, default=45, help="Per-scenario GUI readiness timeout")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    _, manifest = collect(args.out, checks=not args.no_checks, gui=not args.no_gui, timeout=args.timeout)
    failures = [
        name for name, result in {**manifest["checks"], **manifest["screenshots"]}.items()
        if result["status"] == "failed"
    ]
    return 1 if failures or manifest["matplotlib_rcparams"]["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
