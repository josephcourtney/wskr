import contextlib
import logging
import os
import subprocess  # noqa: S404
import tempfile
from pathlib import Path

from wskr.tty.kitty_remote import (
    WindowConfig,
    close_kitty_window,
    configure_window,
    find_executable,
    get_window_id,
    launch_kitty_terminal,
    send_payload,
    send_startup_command,
    take_screenshot,
    wait_for_file_to_exist,
    wait_for_file_with_content,
)

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


def show_log(log_file: Path) -> None:
    if not log_file.exists():
        logging.error("No log file found at %s", log_file)
        return

    logging.debug("==== BEGIN KITTY SESSION LOG ====")
    for line in log_file.read_text(encoding="utf-8").splitlines():
        logging.debug("[KITTY] %s", line)
    logging.debug("==== END KITTY SESSION LOG ====\n")


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
                # give it another 2s to exit cleanly, then swallow any further timeout
                with contextlib.suppress(subprocess.TimeoutExpired):
                    proc.wait(timeout=2)
    except PermissionError as e:
        logging.exception("Failed to terminate kitty process: %s", e)


def prepare_paths() -> tuple[Path, Path, str, str]:
    done_file = Path(tempfile.NamedTemporaryFile(delete=False).name)
    log_file = done_file.with_suffix(".log")
    uid = done_file.name.split(os.sep)[-1]
    sock = f"unix:/tmp/kitty-{uid}.sock"
    return done_file, log_file, sock, uid


def script_path() -> Path:
    return Path(__file__).parent / "payload.py"


cfg = WindowConfig()
kitty_bin = find_executable("kitty")
yabai_bin = find_executable("yabai")

done_file, log_file, sock, uid = prepare_paths()
sock_path = Path(sock.removeprefix("unix:"))
env = {**os.environ, "KITTY_DEMO_DONE_FILE": str(done_file)}

proc = launch_kitty_terminal(kitty_bin, sock, cfg.title, env)
wait_for_file_to_exist(sock_path)

send_startup_command(kitty_bin, sock, done_file, env)
wait_for_file_with_content(done_file, timeout=cfg.max_wait)
win_id = get_window_id(done_file)

configure_window(yabai_bin, win_id, width=cfg.width, height=cfg.height, x=cfg.x, y=cfg.y)

send_payload(kitty_bin, sock, env, script_path(), done_file, log_file)
wait_for_file_with_content(done_file, timeout=cfg.max_wait)

show_log(log_file)

capture_path = Path.cwd() / f"capture_{uid}.png"
take_screenshot(yabai_bin, lambda w: w.get("app") == "kitty" and w.get("id") == win_id, capture_path)

close_kitty_window(kitty_bin, lambda w: w.get("title", "").startswith(cfg.title))
cleanup_temp_files(done_file, log_file)
terminate_process(proc)
