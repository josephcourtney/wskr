"""Fully unattended native Kitty P3 scenarios with isolated yabai window control.

Run on macOS with Kitty, yabai, Screen Recording permission and a disposable
space. This opt-in controller creates/destroys only its own space and window.
A separate foreground worker retains all terminal keyboard input ownership.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed, bounded tool argv
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

_STATES = ("unmanaged", "floating", "bsp", "float-space")
_CASES = ("resize", "paging", "lifecycle", "appearance")
_RUN_SECONDS = 240
_COMMAND_SECONDS = 15
_POLL_SECONDS = 0.1
_EXACTLY_ONE = 1
_MIN_SCREENSHOT_BYTES = 100
_START_WIDTH = 1200
_START_HEIGHT = 760
_NARROW_WIDTHS = (620, 510, 430, 360)
_NARROW_HEIGHTS = (410, 340, 300, 260)


def _invoke(argv: list[str], *, timeout: int = _COMMAND_SECONDS) -> str:
    """Return stdout or fail with the exact bounded command and stderr."""
    proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - bounded exact argv
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )
    if proc.returncode:
        msg = f"{argv!r}: exit {proc.returncode}: {proc.stderr.strip()}"
        raise RuntimeError(msg)
    return proc.stdout


def _window_matches(window: dict, title: str) -> bool:
    """Only the exact, unique Kitty title may be controlled."""
    return window.get("title") == title and str(window.get("app", "")).lower() == "kitty"


def _state_matches(window: dict, space: dict, state: str) -> bool:
    floating = window.get("is-floating")
    layout = space.get("type")
    if state == "bsp":
        return layout == "bsp" and floating is False
    if state == "float-space":
        return layout == "float" and floating is True
    return layout == "bsp" and floating is True


def _action(prompt: str) -> str:
    """Translate known harness instructions, rejecting unknown GUI steps."""
    value = prompt.lower()
    checkpoints = (
        ("dark", ("dark color theme",)),
        ("light", ("light color theme",)),
        ("enter", ("blank input line",)),
        ("n", ("type n",)),
        ("p", ("type p",)),
        (
            "shrink",
            ("shrink", "narrower", "shorter", "resize the kitty window", "page capacity changes"),
        ),
        ("expand", ("expand",)),
        ("initial", ("enlarge", "normally sized kitty")),
        ("retry", ("blank screenshot captured",)),
    )
    for action, markers in checkpoints:
        if any(marker in value for marker in markers):
            return action
    msg = f"Unrecognized native GUI checkpoint: {prompt}"
    raise ValueError(msg)


class NativeController:
    """Own only a uniquely titled Kitty window and a newly created yabai space."""

    def __init__(self, *, root: Path, state: str, case: str, height: int) -> None:
        self.root = root.resolve()
        self.state = state
        self.case = case
        self.height = height
        self.title = f"wskr-p3-{uuid.uuid4().hex[:12]}"
        self.space_label = self.title
        self.rule_label = self.title
        self.previous_uuid: str | None = None
        self.space_uuid: str | None = None
        self.space_index: int | None = None
        self.window_id: int | None = None
        self.window_owner_pid: int | None = None
        self.kitty_window_id: int | None = None
        self.kitty_process: subprocess.Popen[bytes] | None = None
        self.socket_dir: Path | None = None
        self.socket_path: Path | None = None
        self.rule_installed = False
        self.shrinks = 0
        self.base_frame: dict | None = None
        self.events: list[dict] = []
        self.window_observations: list[dict] = []
        self.commands: list[dict] = []
        self.cleanup_errors: list[str] = []

    def yabai(self, *args: str) -> str:
        argv = ["yabai", "-m", *args]
        output = _invoke(argv)
        self.commands.append({"argv": argv, "output": output[:1000]})
        return output

    def query(self, *args: str) -> dict:
        """Read a single yabai object, rejecting unexpected JSON containers."""
        result = json.loads(self.yabai("query", *args))
        if not isinstance(result, dict):
            msg = f"Expected yabai object for {args!r}"
            raise TypeError(msg)
        return result

    def query_list(self, *args: str) -> list[dict]:
        """Read yabai collections, keeping list/object query shapes distinct."""
        result = json.loads(self.yabai("query", *args))
        if not isinstance(result, list):
            msg = f"Expected yabai array for {args!r}"
            raise TypeError(msg)
        return result

    def _spaces(self) -> list[dict]:
        return self.query_list("--spaces")

    def _own_space(self) -> None:
        current = self.query("--spaces", "--space")
        self.previous_uuid = current["uuid"]
        before = {item["uuid"] for item in self._spaces()}
        self.yabai("space", "--create")
        created = [item for item in self._spaces() if item["uuid"] not in before]
        if len(created) != _EXACTLY_ONE:
            msg = "Could not independently identify exactly one new test space"
            raise RuntimeError(msg)
        space = created[0]
        self.space_uuid = space["uuid"]
        self.space_index = int(space["index"])
        self.yabai("space", str(self.space_index), "--label", self.space_label)
        self.yabai("space", self.space_label, "--layout", "float" if self.state == "float-space" else "bsp")
        self.yabai("space", "--focus", self.space_label)

    def _spawn(self) -> None:
        rule = [
            f"label={self.rule_label}",
            "app=^[Kk]itty$",
            f"title=^{re.escape(self.title)}$",
            f"space={self.space_label}",
            f"manage={'off' if self.state == 'unmanaged' else 'on'}",
        ]
        self.yabai("rule", "--add", *rule)
        self.rule_installed = True
        env = {
            **os.environ,
            "WSKR_NATIVE_CONTROL_DIR": str(self.root),
            "WSKR_FIT": "contain",
            "WSKR_IDLE_REDRAW": "coalesce",
            "WSKR_KITTY_ANCHOR": "unicode",
            "MPLBACKEND": "wskr_kitty",
        }
        # macOS AF_UNIX paths are short; a long artifacts path cannot host a
        # usable Kitty socket. The private 0700 directory also limits access.
        self.socket_dir = Path(tempfile.mkdtemp(prefix="wskr-native-", dir="/tmp"))
        socket = self.socket_dir / "kitty-{kitty_pid}.sock"
        argv = [
            "kitty", "--single-instance=no", "--title", self.title,
            "--override", "allow_remote_control=socket-only",
            "--listen-on", f"unix:{socket}",
            sys.executable, "-m", "scripts.phase3_native_auto_entry",
            "--case", self.case, "--height", str(self.height),
            "--mode", "unmanaged" if self.state == "unmanaged" else "yabai",
        ]
        self.commands.append({"argv": argv})
        self.kitty_process = subprocess.Popen(  # ruff: ignore[subprocess-without-shell-equals-true] - dedicated app
            argv, cwd=Path(__file__).resolve().parents[1], env=env
        )
        self.socket_path = Path(str(socket).replace("{kitty_pid}", str(self.kitty_process.pid)))
        deadline = time.monotonic() + 25
        last_identity: tuple[int, int] | None = None
        stable_samples = 0
        while time.monotonic() < deadline:
            if self.kitty_process.poll() is not None:
                msg = "Dedicated Kitty process terminated before window identification"
                raise RuntimeError(msg)
            matches = [w for w in self.query_list("--windows") if _window_matches(w, self.title)]
            if len(matches) > _EXACTLY_ONE:
                msg = "Ambiguous Kitty test-window identity"
                raise RuntimeError(msg)
            if matches:
                match = matches[0]
                self.window_observations.append({
                    "id": match.get("id"),
                    "pid": match.get("pid"),
                    "space": match.get("space"),
                    "has_ax_reference": match.get("has-ax-reference"),
                    "title": match.get("title"),
                })
                # macOS may publish a window record before AX can resolve it.
                # Bind only after two consistent ready snapshots.
                identity = (int(match["id"]), int(match["pid"]))
                ready = match.get("has-ax-reference") is not False
                stable_samples = stable_samples + 1 if ready and identity == last_identity else int(ready)
                last_identity = identity
                if stable_samples >= 2:
                    self.window_id, self.window_owner_pid = identity
                    self.yabai("rule", "--remove", self.rule_label)
                    self.rule_installed = False
                    if self.state == "floating" and self._window().get("is-floating") is False:
                        self.yabai("window", str(self.window_id), "--toggle", "float")
                    self._verify()
                    self._identify_kitty_window()
                    return
            else:
                last_identity = None
                stable_samples = 0
            time.sleep(_POLL_SECONDS)
        msg = f"Kitty window did not stabilize in yabai; observations={self.window_observations[-5:]}"
        raise TimeoutError(msg)

    def _identify_kitty_window(self, *, timeout: float = 10.0) -> None:
        """Bind the Kitty-internal window ID, distinct from the macOS/yabai ID."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                tree = json.loads(self.kitty("ls"))
                windows = [
                    window for os_window in tree
                    for tab in os_window.get("tabs", [])
                    for window in tab.get("windows", [])
                ]
                if len(windows) == _EXACTLY_ONE:
                    self.kitty_window_id = int(windows[0]["id"])
                    return
            except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired):
                time.sleep(_POLL_SECONDS)
                continue
            time.sleep(_POLL_SECONDS)
        msg = "Unable to identify exactly one Kitty-internal window on private socket"
        raise RuntimeError(msg)

    def _target(self) -> str:
        if self.kitty_window_id is None:
            msg = "Kitty-internal window ID was not established"
            raise RuntimeError(msg)
        return f"id:{self.kitty_window_id}"

    def _window(self) -> dict:
        """Verify stable OS identity using the full yabai window snapshot.

        A freshly created Kitty window can appear in --windows before yabai's
        targeted --window <id> resolver can address it.
        """
        if self.window_id is None:
            msg = "Test window not identified"
            raise RuntimeError(msg)
        windows = self.query_list("--windows")
        matches = [w for w in windows if w.get("id") == self.window_id]
        if len(matches) != _EXACTLY_ONE:
            candidates = [
                {"id": w.get("id"), "title": w.get("title"), "pid": w.get("pid"), "space": w.get("space")}
                for w in windows if str(w.get("app", "")).lower() == "kitty"
            ]
            self.window_observations.append({"missing_id": self.window_id, "kitty_candidates": candidates})
            status = self.kitty_process.poll() if self.kitty_process is not None else None
            msg = f"Owned Kitty OS window {self.window_id} disappeared or became ambiguous; pid status={status}"
            raise RuntimeError(msg)
        result = matches[0]
        if str(result.get("app", "")).lower() != "kitty":
            msg = "Owned window ID now refers to a non-Kitty application"
            raise RuntimeError(msg)
        if self.window_owner_pid is not None and result.get("pid") != self.window_owner_pid:
            msg = "Owned Kitty OS window PID changed; refusing possible window-ID reuse"
            raise RuntimeError(msg)
        if result.get("space") != self.space_index:
            msg = "Test window left its isolated yabai space"
            raise RuntimeError(msg)
        return result

    def _verify(self) -> dict:
        window = self._window()
        space = self.query("--spaces", "--space", str(self.space_index))
        # Do not accidentally change a preexisting user's tiling tree.
        others = [
            window for window in self.query_list("--windows")
            if window.get("space") == self.space_index and window["id"] != self.window_id
        ]
        if others:
            msg = "An unrelated window entered the dedicated test space; aborting"
            raise RuntimeError(msg)
        if not _state_matches(window, space, self.state):
            msg = (
                f"Requested {self.state} but observed floating={window.get('is-floating')}, "
                f"space={space.get('type')}"
            )
            raise RuntimeError(msg)
        return {"window": window, "space": space, "requested_state": self.state, "verified": True}

    def _size(self, *, small: bool) -> None:
        self._verify()
        if self.state == "bsp":
            if small:
                if self.base_frame is None:
                    msg = "Missing initial BSP geometry"
                    raise RuntimeError(msg)
                # Absolute padding is derived from the ORIGINAL full viewport,
                # not the progressively smaller test window's current frame.
                fraction = 0.26 + 0.06 * min(self.shrinks, 3)
                side = int(self.base_frame["w"] * fraction)
                vertical = int(self.base_frame["h"] * fraction)
                self.yabai("space", self.space_label, "--padding", f"abs:{vertical}:{vertical}:{side}:{side}")
            else:
                self.yabai("space", self.space_label, "--padding", "abs:0:0:0:0")
                self.base_frame = self._window()["frame"]
        else:
            index = min(self.shrinks, len(_NARROW_WIDTHS) - 1)
            width = _NARROW_WIDTHS[index] if small else _START_WIDTH
            height = _NARROW_HEIGHTS[index] if small else _START_HEIGHT
            self.yabai("window", str(self.window_id), "--resize", f"abs:{width}:{height}")
        if small:
            self.shrinks += 1
        else:
            self.shrinks = 0
        time.sleep(0.4)
        self._verify()

    def kitty(self, *args: str) -> str:
        # Kitty may daemonize on macOS, so the GUI's {kitty_pid} need not
        # equal the PID returned by Popen. Only scan our private socket dir.
        if self.socket_dir is not None:
            sockets = list(self.socket_dir.glob("kitty-*.sock"))
            if len(sockets) > _EXACTLY_ONE:
                msg = "Ambiguous Kitty control sockets in private test directory"
                raise RuntimeError(msg)
            if sockets:
                self.socket_path = sockets[0]
        if self.socket_path is None or not self.socket_path.exists():
            msg = "Kitty control socket not available"
            raise RuntimeError(msg)
        return _invoke(["kitty", "@", "--to", f"unix:{self.socket_path}", *args])

    def _theme(self, *, light: bool) -> None:
        fg, bg = ("#20252b", "#f7f8fa") if light else ("#ebf0f4", "#252b30")
        self.kitty("set-colors", "--match", self._target(), f"foreground={fg}", f"background={bg}")

    def _capture(self, *, stage: str, path: str) -> None:
        self._verify()
        destination = Path(path).resolve()
        # Prevent remote workers from causing writes outside their own evidence tree.
        artifacts = (Path(__file__).resolve().parents[1] / "artifacts").resolve()
        if not destination.is_relative_to(artifacts) or destination.suffix != ".png":
            msg = "Refusing screenshot path outside wskr artifacts"
            raise RuntimeError(msg)
        destination.parent.mkdir(parents=True, exist_ok=True)
        _invoke(["/usr/sbin/screencapture", "-x", "-l", str(self.window_id), "-o", str(destination)], timeout=30)
        if not destination.is_file() or destination.stat().st_size < _MIN_SCREENSHOT_BYTES:
            msg = f"Native window-only capture failed: {stage}"
            raise RuntimeError(msg)

    def _handle(self, event: dict) -> None:
        action = event["action"]
        details = event["details"]
        if action == "ready":
            self._size(small=False)
        elif action == "capture":
            self._capture(stage=details["stage"], path=details["path"])
        elif action == "dialog":
            step = _action(details["prompt"])
            if step == "initial":
                self._size(small=False)
            elif step == "shrink":
                self._size(small=True)
            elif step == "expand":
                self._size(small=False)
            elif step == "retry":
                self._verify()
            elif step in {"dark", "light"}:
                self._theme(light=step == "light")
            else:
                self._verify()
                # send-text uses Python-style escapes; only the worker reads stdin.
                self.kitty("send-text", "--match", self._target(), f"{step}\\n" if step != "enter" else "\\n")
        else:
            msg = f"Unknown controller event action: {action}"
            raise ValueError(msg)

    def _poll_events(self) -> bool:
        handled = False
        for event_path in sorted((self.root / "events").glob("*.json")):
            event = json.loads(event_path.read_text(encoding="utf-8"))
            event_path.unlink()
            receipt: dict = {"ok": True}
            try:
                self._handle(event)
                event["observation"] = self._verify()
            except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.TimeoutExpired) as exc:
                receipt = {"ok": False, "error": str(exc)}
                event["error"] = str(exc)
            self.events.append(event)
            target = self.root / "acks" / f"{event['id']}.json"
            target.write_text(json.dumps(receipt), encoding="utf-8")
            handled = True
            if not receipt["ok"]:
                msg = receipt["error"]
                raise RuntimeError(msg)
        return handled

    def _check_returned_prompt(self) -> None:
        """Require a real foreground shell prompt and the worker exit marker."""
        for _ in range(35):
            prompt = self.kitty("get-text", "--match", self._target(), "--extent", "screen")
            if "WSKR_NATIVE_AUTO_PROMPT>" in prompt and "WSKR_NATIVE_AUTO_EXIT:" in prompt:
                (self.root / "returned_text.txt").write_text(prompt, encoding="utf-8")
                return
            time.sleep(_POLL_SECONDS)
        (self.root / "returned_text.txt").write_text(prompt, encoding="utf-8")
        msg = "Returned real zsh prompt/exit marker missing from Kitty screen"
        raise RuntimeError(msg)

    def _collect_worker_evidence(self, worker: dict) -> None:
        """Copy the one completed harness ZIP, preserving source evidence."""
        if worker.get("returncode"):
            msg = f"Native P3 harness returned {worker['returncode']}"
            raise RuntimeError(msg)
        evidence = worker.get("evidence_archive")
        if worker.get("archive_count") != _EXACTLY_ONE or not evidence:
            msg = "Unable to identify one unambiguous harness ZIP"
            raise RuntimeError(msg)
        source = Path(evidence).resolve()
        artifacts = (Path(__file__).resolve().parents[1] / "artifacts").resolve()
        if not source.is_relative_to(artifacts) or not source.is_file():
            msg = "Native worker evidence archive was not found under wskr artifacts"
            raise RuntimeError(msg)
        shutil.copy2(source, self.root / "harness.zip")

    def _complete_worker(self, path: Path) -> dict:
        worker = json.loads(path.read_text(encoding="utf-8"))
        self._check_returned_prompt()
        self._verify()
        _invoke(
            [
                "/usr/sbin/screencapture",
                "-x",
                "-l",
                str(self.window_id),
                "-o",
                str(self.root / "returned_prompt.png"),
            ],
            timeout=30,
        )
        self._collect_worker_evidence(worker)
        return worker

    def _await_worker(self) -> dict:
        """Pump only controller event files; do not read the plotting PTY."""
        deadline = time.monotonic() + _RUN_SECONDS
        while time.monotonic() < deadline:
            self._poll_events()
            completed = self.root / "completed.json"
            if completed.exists():
                return self._complete_worker(completed)
            if self.kitty_process is not None and self.kitty_process.poll() is not None:
                msg = "Kitty exited before the P3 harness completed"
                raise RuntimeError(msg)
            time.sleep(_POLL_SECONDS)
        msg = "Native GUI harness exceeded its bounded deadline"
        raise TimeoutError(msg)

    def _finish_report(self, result: dict) -> None:
        """Record desktop cleanup failures as qualification failures."""
        self.cleanup()
        if self.cleanup_errors:
            result["cleanup_errors"] = self.cleanup_errors
            result["passed_protocol_checks"] = False
            result.setdefault("error", "Native test window or space cleanup failed")
        result["events"] = self.events
        result["commands"] = self.commands
        result["space_uuid"] = self.space_uuid
        result["window_id"] = self.window_id
        result["window_owner_pid"] = self.window_owner_pid
        result["window_observations"] = self.window_observations
        result["kitty_window_id"] = self.kitty_window_id
        (self.root / "controller.json").write_text(
            json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8"
        )

    def run(self) -> dict:
        (self.root / "events").mkdir(parents=True)
        (self.root / "acks").mkdir()
        result: dict = {"state": self.state, "case": self.case, "height": self.height, "title": self.title}
        try:
            self._own_space()
            self._spawn()
            result["worker"] = self._await_worker()
            result["passed_protocol_checks"] = True
        except (OSError, ValueError, TypeError, RuntimeError, TimeoutError, subprocess.TimeoutExpired) as exc:
            result["error"] = str(exc)
            result["passed_protocol_checks"] = False
        finally:
            self._finish_report(result)
        return result

    def _cleanup_rule(self) -> None:
        if not self.rule_installed:
            return
        try:
            self.yabai("rule", "--remove", self.rule_label)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            self.cleanup_errors.append(f"rule removal: {exc}")

    def _cleanup_kitty(self) -> None:
        process = self.kitty_process
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        except OSError as exc:
            self.cleanup_errors.append(f"Kitty process termination: {exc}")

    def _restore_previous_space(self) -> None:
        if not self.previous_uuid:
            return
        try:
            prior = next(s for s in self._spaces() if s["uuid"] == self.previous_uuid)
            self.yabai("space", "--focus", str(prior["index"]))
        except (OSError, RuntimeError, StopIteration, KeyError, subprocess.TimeoutExpired) as exc:
            self.cleanup_errors.append(f"prior space restoration: {exc}")

    def _require_empty_owned_space(self, space_index: int) -> None:
        """Never relocate an unrelated desktop window by destroying its space."""
        occupied = [w for w in self.query_list("--windows") if w.get("space") == space_index]
        if occupied:
            ids = [w.get("id") for w in occupied]
            msg = f"Owned test space still contains windows: {ids}"
            raise RuntimeError(msg)

    def _destroy_owned_space(self) -> None:
        if not self.space_uuid:
            return
        try:
            created = next(s for s in self._spaces() if s["uuid"] == self.space_uuid)
            self._require_empty_owned_space(int(created["index"]))
            self.yabai("space", "--destroy", str(created["index"]))
        except (OSError, RuntimeError, StopIteration, KeyError, subprocess.TimeoutExpired) as exc:
            self.cleanup_errors.append(f"owned test space destruction: {exc}")

    def _remove_socket(self) -> None:
        if self.socket_dir is None:
            return
        try:
            shutil.rmtree(self.socket_dir)
        except OSError as exc:
            self.cleanup_errors.append(f"private Kitty socket cleanup: {exc}")

    def cleanup(self) -> None:
        """Undo only owned resources, collecting all cleanup failures."""
        self._cleanup_rule()
        self._cleanup_kitty()
        self._restore_previous_space()
        self._destroy_owned_space()
        self._remove_socket()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=_STATES, required=True)
    parser.add_argument("--case", choices=_CASES, required=True)
    parser.add_argument("--height", type=int, choices=(2, 6), default=2)
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("Requires native macOS")
    for command in ("kitty", "yabai", "/usr/sbin/screencapture"):
        if shutil.which(command) is None:
            parser.error(f"Required native tool unavailable: {command}")
    root = Path("artifacts/phase3-native-yabai") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{args.state}-{args.case}-{args.height}"
    )
    root.mkdir(parents=True, exist_ok=False)
    controller = NativeController(root=root, state=args.state, case=args.case, height=args.height)
    report = controller.run()
    archive = shutil.make_archive(str(root), "zip", root_dir=root)
    print(f"Native yabai evidence archive: {archive}")
    if not report.get("passed_protocol_checks"):
        print(f"FAILED: {report.get('error')}", file=sys.stderr)
        return 1
    print("Native automation passed protocol checks; screenshot review remains required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
