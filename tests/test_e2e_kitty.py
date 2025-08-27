import contextlib
import importlib
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageChops

import wskr.tty.kitty_remote as kr
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

logger = logging.getLogger(__name__)


pytestmark = pytest.mark.slow

# The payload demo lives under tests/payloads/payload.py
PAYLOAD_MODULE = "tests.payloads.payload"


def test_payload_script_generates_image_and_done(tmp_path, monkeypatch):
    """Run payload.main() in-process, stub out IO, and verify files."""
    # 1) Use a fresh temp dir
    monkeypatch.chdir(tmp_path)

    # 2) Tell payload where to write its done file
    done_file = tmp_path / "demo.done"
    monkeypatch.setenv("KITTY_DEMO_DONE_FILE", str(done_file))

    # 3) Stub out PIL.Image and PIL.ImageDraw
    fake_PIL = types.ModuleType("PIL")
    fake_Image = types.ModuleType("PIL.Image")
    fake_ImageDraw = types.ModuleType("PIL.ImageDraw")

    def fake_new(mode, size, color):
        # Mode, size, color → ignore, just write a dummy PNG
        class Img:
            def save(self, path, **kw):
                Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)

        return Img()

    def fake_draw(im):
        class Draw:
            def ellipse(self, *args, **kwargs):
                pass

            def rectangle(self, *args, **kwargs):
                pass

        return Draw()

    fake_Image.new = fake_new  # type: ignore[attr-defined]
    fake_ImageDraw.Draw = fake_draw  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "PIL", fake_PIL)
    monkeypatch.setitem(sys.modules, "PIL.Image", fake_Image)
    monkeypatch.setitem(sys.modules, "PIL.ImageDraw", fake_ImageDraw)

    # 4) Stub image transport to avoid external calls
    class Dummy:
        def send_image(self, png):
            pass

    monkeypatch.setattr("wskr.tty.registry.get_image_transport", lambda name="kitty": Dummy())

    # 5) Stub input() so it doesn't block
    monkeypatch.setattr("builtins.input", lambda prompt="": "")

    # 6) Fake argv for payload
    monkeypatch.setattr(
        sys,
        "argv",
        ["payload.py", "--scenario", "checker", "--width", "50", "--height", "50"],
    )

    # 7) Import & run payload.main()
    payload = importlib.import_module(PAYLOAD_MODULE)
    importlib.reload(payload)
    payload.main()  # type: ignore[attr-defined]

    # 8) Verify payload.png
    img = tmp_path / "payload.png"
    assert img.exists(), "payload.png should have been written"
    data = img.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")

    # 9) Verify done flag
    assert done_file.exists()
    assert done_file.read_text().strip() == "done"


def test_full_kitty_remote_workflow(tmp_path, monkeypatch):
    """Simulate the full kitty_remote flow: launch, startup, payload, screenshot, close, cleanup."""
    sock = tmp_path / "kitty.sock"
    done_file = tmp_path / "startup.done"
    log_file = tmp_path / "demo.log"
    shot_file = tmp_path / "screen.png"

    # 1) Fake 'kitty' in PATH
    dummy_bin = tmp_path / "kitty"
    dummy_bin.write_text("#!/bin/sh\nexit 0\n")
    dummy_bin.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(kr, "find_executable", lambda name: str(dummy_bin))

    # 2) launch_kitty_terminal → Popen stub
    launched = {}

    class DummyPopen:
        def __init__(self, args, env=None, **kw):
            launched["args"] = args
            launched["env"] = env

        def poll(self):
            return 0

    monkeypatch.setattr(sys.modules["subprocess"], "Popen", DummyPopen)
    _ = kr.launch_kitty_terminal(str(dummy_bin), sock, "demo", os.environ)
    assert launched["args"][0].endswith("kitty")

    # 3) send_startup_command writes "42"
    def fake_start(kb, sk, cmd, env):
        done_file.write_text("42")

    monkeypatch.setattr(kr, "send_kitty_command", fake_start)
    kr.send_startup_command(str(dummy_bin), sock, done_file, os.environ)
    kr.wait_for_file_with_content(done_file, timeout=1.0)
    assert done_file.read_text().strip() == "42"

    # 4) send_payload simulates payload + log
    def fake_sendcmd(kb, sk, cmd, env):
        done_file.write_text("done")
        log_file.write_text("log entry\n")

    monkeypatch.setattr(kr, "send_kitty_command", fake_sendcmd)
    kr.send_payload(str(dummy_bin), sock, os.environ, Path("irrelevant"), done_file, log_file)
    kr.wait_for_file_with_content(done_file, timeout=1.0)
    assert done_file.read_text().strip() == "done"
    assert log_file.read_text().startswith("log entry")

    # 5) take_screenshot writes SCREEN
    monkeypatch.setattr(kr, "query_windows", lambda _: [{"id": 42}])

    def fake_run(cmd, *, check=False, **kw):
        Path(cmd[-1]).write_bytes(b"SCREEN")
        return type("R", (), {"returncode": 0, "stderr": b""})()

    monkeypatch.setattr(kr, "run", fake_run)
    ok = kr.take_screenshot("yabai", lambda w: w["id"] == 42, shot_file)
    assert ok
    assert shot_file.read_bytes() == b"SCREEN"

    # 6) close_kitty_window must find our window and invoke close-window
    #    stub try_json_output so that close_kitty_window sees a matching window
    monkeypatch.setattr(
        kr,
        "try_json_output",
        lambda cmd: [{"tabs": [{"windows": [{"id": 42}]}]}],
    )

    calls = []
    monkeypatch.setattr(kr, "run", lambda cmd, **kw: calls.append(cmd))
    kr.close_kitty_window(str(dummy_bin), lambda w: w["id"] == 42)
    assert any("close-window" in " ".join(c) for c in calls)

    # 7) cleanup_temp_files removes done_file & log_file
    kr.cleanup_temp_files(done_file, log_file)
    assert not done_file.exists()
    assert not log_file.exists()


def test_take_screenshot_matches_reference(tmp_path, monkeypatch):
    """take_screenshot should produce a file identical to our reference PNG."""
    # 1) Point to the reference capture in tests/data/reference
    ref = Path(__file__).parent / "data" / "reference" / "cap_0001.png"
    assert ref.exists(), "Reference image must be committed at tests/data/reference/cap_0001.png"

    # 2) Destination path
    dest = tmp_path / "screenshot.png"

    # 3) Stub query_windows so we have a matching window id
    monkeypatch.setattr(kr, "query_windows", lambda _: [{"id": 1}])

    # 4) Stub run() to copy the reference into our dest
    def fake_run(cmd, *, check=False, **kw):
        dest.write_bytes(ref.read_bytes())
        return type("R", (), {"returncode": 0, "stderr": b""})()

    monkeypatch.setattr(kr, "run", fake_run)

    # 5) Run take_screenshot and assert it returns True
    ok = kr.take_screenshot("yabai", lambda w: w["id"] == 1, dest)
    assert ok

    # 6) Finally, the bytes on disk must match the reference exactly
    assert dest.read_bytes() == ref.read_bytes()


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
                # give it another 2s to exit cleanly, then swallow any further timeout
                with contextlib.suppress(subprocess.TimeoutExpired):
                    proc.wait(timeout=2)
    except PermissionError:
        logger.exception("Failed to terminate kitty process")
        raise


def prepare_paths() -> tuple[Path, Path, str, str]:
    tmp = tempfile.NamedTemporaryFile(delete=False)  # noqa: SIM115
    done_file = Path(tmp.name)
    log_file = done_file.with_suffix(".log")
    uid = done_file.parts[-1]
    sock = f"unix:/tmp/kitty-{uid}.sock"
    return done_file, log_file, sock, uid


def script_path() -> Path:
    return Path(__file__).parent / "payload.py"


def capture_reference():
    pass


def save_for_debug(img_ref, img_got, img_diff, uid):
    # 1) make a unique debug folder
    debug_dir = Path(tempfile.mkdtemp(prefix=f"screenshot-debug-{uid}-"))

    ref_path = debug_dir / f"ref_{uid}.png"
    got_path = debug_dir / f"got_{uid}.png"
    diff_path = debug_dir / f"diff_{uid}.png"
    img_ref.save(ref_path)
    img_got.save(got_path)
    img_diff.save(diff_path)

    # 4) let the user know where they landed
    print(f"Saved debug images to {debug_dir}", file=sys.stderr)
    kitty_path = Path(shutil.which("kitty")).resolve()

    # 5) display all three inline via kitty icat
    subprocess.run(
        [kitty_path, "+kitten", "icat", "--align", "left", str(ref_path)],
        check=False,
    )
    subprocess.run(
        [kitty_path, "+kitten", "icat", "--align", "right", str(got_path)],
        check=False,
    )
    subprocess.run(
        [kitty_path, "+kitten", "icat", "--align", "center", str(diff_path)],
        check=False,
    )


def assert_pixels(capture_path, uid):
    # 1) Reference image we expect to reproduce
    ref = Path(__file__).parent / "data" / "reference" / "cap_0001.png"
    assert ref.exists(), "Need a reference at tests/data/reference/cap_0001.png"
    assert capture_path.exists()

    img_ref = Image.open(ref).convert("RGB")
    w, h = img_ref.size
    strip = 300

    # 3) recompute & save the pixel-difference
    img_got = Image.open(capture_path).convert("RGB")
    img_diff = ImageChops.difference(img_ref, img_got)

    img_diff = img_diff.crop((0, 0, w, h - strip))

    diff_arr = np.array(img_diff, dtype=int)

    max_diff = int(diff_arr.max())
    mean_diff = float(diff_arr.mean())

    # allow up to 2-level difference per channel and low average error
    try:
        assert max_diff <= 2, f"max pixel diff {max_diff} > 2"
        assert mean_diff < 0.5, f"mean pixel diff {mean_diff} ≥ 0.5"
    except AssertionError:
        # On failure: save ref, capture, and diff for later, then display them
        save_for_debug(img_ref, img_got, img_diff, uid)
        raise


def test_compare_screenshot():
    cfg = WindowConfig()
    try:
        kitty_bin = find_executable("kitty")
        yabai_bin = find_executable("yabai")
    except FileNotFoundError as exc:
        pytest.skip(str(exc))

    done_file, log_file, sock, uid = prepare_paths()
    sock_path = Path(sock.removeprefix("unix:"))
    env = {
        **os.environ,
        "KITTY_DEMO_DONE_FILE": str(done_file),
    }

    proc = launch_kitty_terminal(kitty_bin, Path(sock), cfg.title, env)  # type: ignore[possibly-unresolved-reference]
    wait_for_file_to_exist(sock_path)

    send_startup_command(kitty_bin, Path(sock), done_file, env)  # type: ignore[possibly-unresolved-reference]
    wait_for_file_with_content(done_file, timeout=cfg.max_wait)
    win_id = get_window_id(done_file)

    configure_window(yabai_bin, win_id, width=cfg.width, height=cfg.height, x=cfg.x, y=cfg.y)  # type: ignore[possibly-unresolved-reference]

    send_payload(kitty_bin, Path(sock), env, script_path(), done_file, log_file)  # type: ignore[possibly-unresolved-reference]
    wait_for_file_with_content(done_file, timeout=cfg.max_wait)

    show_log(log_file)

    capture_path = Path.cwd() / f"capture_{uid}.png"
    take_screenshot(yabai_bin, lambda w: w.get("app") == "kitty" and w.get("id") == win_id, capture_path)  # type: ignore[possibly-unresolved-reference]

    close_kitty_window(kitty_bin, lambda w: w.get("title", "").startswith(cfg.title))  # type: ignore[possibly-unresolved-reference]
    cleanup_temp_files(done_file, log_file)
    terminate_process(proc)

    assert_pixels(capture_path, uid)
