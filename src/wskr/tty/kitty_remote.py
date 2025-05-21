# ruff: noqa: S603
import contextlib
import json
import logging
import shutil
import subprocess  # noqa: S404
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class WindowConfig:
    title: str = "wskr-kitty"
    width: int = 800
    height: int = 600
    x: int = 100
    y: int = 100
    max_wait: float = 10.0


def find_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        msg = f"'{name}' not found in PATH."
        logger.error(msg)
        raise FileNotFoundError(msg)
    return path


def run(
    cmd: list[str], *, capture_output: bool = False, check: bool = False, **kwargs
) -> subprocess.CompletedProcess | bytes:
    logger.debug("Running: %s", " ".join(cmd))
    if capture_output and not check:
        return subprocess.check_output(cmd, **kwargs)
    return subprocess.run(cmd, capture_output=capture_output, check=check, **kwargs)


def try_json_output(cmd: list[str]) -> list[dict] | None:
    try:
        return json.loads(run(cmd, capture_output=True))
    except Exception as e:
        logger.debug("JSON parsing failed: %s", e)
        return None


def _abort(msg: str) -> None:
    logger.error(msg)
    sys.exit(1)


# === FILE WAITING ===
def wait_for_file_with_content(path: Path, timeout: float = 10.0, poll: float = 0.3) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists() and path.read_text().strip():
            return
        time.sleep(poll)
    msg = f"Timeout waiting for signal in {path}"
    raise TimeoutError(msg)


def wait_for_file_to_exist(path: Path, timeout: float = 3.0, poll: float = 0.1) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if path.exists():
            return
        time.sleep(poll)
    _abort(f"File never appeared at {path}")


# === WINDOW OPERATIONS ===


def query_windows(yabai_bin: str) -> list[dict]:
    return try_json_output([yabai_bin, "-m", "query", "--windows"]) or []


def configure_window(
    yabai_bin: str,
    win_id: int,
    *,
    float_it: bool = True,
    width: int | None = None,
    height: int | None = None,
    x: int | None = None,
    y: int | None = None,
    focus: bool = True,
) -> None:
    def yabai(*args: str) -> None:
        run([yabai_bin, "-m", "window", str(win_id), *args], capture_output=False)

    if float_it:
        yabai("--toggle", "float")
    if width is not None and height is not None:
        yabai("--resize", f"abs:{width}:{height}")
    if x is not None and y is not None:
        yabai("--move", f"abs:{x}:{y}")
    if focus:
        yabai("--focus")


def take_screenshot(yabai_bin: str, predicate: Callable[[dict], bool], dest: Path) -> bool:
    windows = query_windows(yabai_bin)
    win_id = next((w["id"] for w in windows if predicate(w)), None)

    if win_id is None:
        logger.error("No matching window for screenshot.")
        return False

    result = run(
        [
            "screencapture",
            "-o",
            "-x",
            "-l",
            str(win_id),
            str(dest),
        ],
        check=True,
    )
    if result.returncode == 0 and dest.exists():
        logger.info("Screenshot saved to %s", dest)
        return True

    logger.error("Screenshot failed: %s", result.stderr.decode())
    return False


def close_kitty_window(kitty_bin: str, predicate: Callable[[dict], bool]) -> None:
    sessions = try_json_output([kitty_bin, "@", "ls"]) or []
    for os_win in sessions:
        for tab in os_win.get("tabs", []):
            for win in tab.get("windows", []):
                if predicate(win):
                    run([kitty_bin, "@", "close-window", "--match", f"id:{win['id']}"], check=True)
                    return


# === KITTY INTERACTIONS ===


def launch_kitty_terminal(kitty_bin: str, sock: str, title: str, env: dict) -> subprocess.Popen:
    return subprocess.Popen(
        [
            kitty_bin,
            "-1",
            "--title",
            title,
            "--override",
            "allow_remote_control=yes",
            "--listen-on",
            sock,
        ],
        env=env,
    )


def send_kitty_command(kitty_bin: str, sock: str, command: str, env: dict) -> None:
    subprocess.Popen(
        [
            kitty_bin,
            "@",
            "--to",
            sock,
            "send-text",
            command,
            "\n",
        ],
        env=env,
    )


def get_window_id(done_file: Path) -> int:
    try:
        return int(done_file.read_text().strip())
    except Exception as e:
        _abort(f"Failed to parse window id: {e}")
    finally:
        done_file.write_text("")


def show_log(log_file: Path) -> None:
    if not log_file.exists():
        logger.error("No log file found at %s", log_file)
        return

    logger.debug("==== BEGIN KITTY SESSION LOG ====")
    for line in log_file.read_text(encoding="utf-8").splitlines():
        logger.debug("[KITTY] %s", line)
    logger.debug("==== END KITTY SESSION LOG ====\n")


def cleanup_temp_files(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def terminate_process(proc: subprocess.Popen) -> None:
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                # After kill, wait again but ignore if it still times out
                with contextlib.suppress(subprocess.TimeoutExpired):
                    proc.wait(timeout=2)

    except PermissionError:
        logger.exception("Failed to terminate kitty process")
        raise


def send_startup_command(kitty_bin: str, sock: str, done_file: Path, env: dict) -> None:
    cmd = f"yabai -m query --windows --window | jq -r .id > '{done_file}'; clear; stty size;"
    send_kitty_command(kitty_bin, sock, cmd, env)


def send_payload(kitty_bin: str, sock: str, env: dict, script: Path, done_file: Path, log_file: Path) -> None:
    cmd = f"clear; python '{script}' 2>&1 | tee '{log_file}'; echo 'done' > '{done_file}'"
    send_kitty_command(kitty_bin, sock, cmd, env)
