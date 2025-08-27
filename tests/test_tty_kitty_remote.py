import shutil
import subprocess
from pathlib import Path

import pytest

from wskr.tty.kitty_remote import (
    WindowConfig,
    _abort,
    cleanup_temp_files,
    close_kitty_window,
    configure_window,
    find_executable,
    get_window_id,
    launch_kitty_terminal,
    query_windows,
    run,
    send_kitty_command,
    send_payload,
    send_startup_command,
    show_log,
    take_screenshot,
    terminate_process,
    try_json_output,
    wait_for_file_to_exist,
    wait_for_file_with_content,
)


def test_window_config_defaults():
    cfg = WindowConfig()
    assert cfg.title == "wskr-kitty"
    assert cfg.width == 800
    assert cfg.height == 600
    assert cfg.x == 100
    assert cfg.y == 100
    assert cfg.max_wait == 10.0


def test_find_executable_found(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    assert find_executable("foo") == "/usr/bin/foo"


def test_find_executable_not_found(monkeypatch, caplog):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    caplog.set_level("ERROR")
    with pytest.raises(FileNotFoundError):
        find_executable("missing")
    assert "not found in PATH" in caplog.text


def test_run_uses_check_output(monkeypatch):
    # capture_output=True, check=False → uses check_output
    monkeypatch.setattr(subprocess, "check_output", lambda cmd, **kw: b"stdout")
    res = run(["echo", "hi"], capture_output=True, check=False)
    assert res == b"stdout"


def test_run_uses_run(monkeypatch):
    fake = subprocess.CompletedProcess(args=["x"], returncode=0)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kw: fake)
    res = run(["ls"], capture_output=False, check=True, timeout=0.1)
    assert res is fake


def test_try_json_output_valid(monkeypatch):
    # stub run to return JSON bytes
    monkeypatch.setattr("wskr.tty.kitty_remote.run", lambda cmd, capture_output, **kw: b'[{"id":1}]')
    result = try_json_output(["cmd"])
    assert isinstance(result, list)
    assert result[0]["id"] == 1


def test_try_json_output_invalid(monkeypatch, caplog):
    # stub run to return bad JSON
    monkeypatch.setattr("wskr.tty.kitty_remote.run", lambda *args, **kw: b"not json")
    caplog.set_level("DEBUG")
    assert try_json_output(["cmd"]) is None
    assert "JSON parsing failed" in caplog.text


def test_abort_raises_system_exit():
    with pytest.raises(SystemExit):
        _abort("fatal error")


def test_wait_for_file_with_content_success(tmp_path):
    p = tmp_path / "f"
    p.write_text("content")
    # should return immediately
    wait_for_file_with_content(p, timeout=1.0)


def test_wait_for_file_with_content_timeout(tmp_path):
    p = tmp_path / "nope"
    # timeout=0 forces immediate TimeoutError
    with pytest.raises(TimeoutError):
        wait_for_file_with_content(p, timeout=0)


def test_wait_for_file_to_exist_success(tmp_path):
    p = tmp_path / "exists"
    p.write_text("x")
    wait_for_file_to_exist(p, timeout=0.1)


def test_wait_for_file_to_exist_abort(tmp_path):
    p = tmp_path / "missing"
    with pytest.raises(SystemExit):
        wait_for_file_to_exist(p, timeout=0)


def test_query_windows(monkeypatch):
    monkeypatch.setattr("wskr.tty.kitty_remote.try_json_output", lambda cmd: [{"a": 1}])
    assert query_windows("yabai") == [{"a": 1}]
    monkeypatch.setattr("wskr.tty.kitty_remote.try_json_output", lambda cmd: None)
    assert query_windows("yabai") == []


def test_configure_window_all_options(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "wskr.tty.kitty_remote.run",
        lambda args, capture_output=False, **kw: calls.append(args),
    )
    configure_window("yb", 42, float_it=True, width=10, height=20, x=1, y=2, focus=True)
    expected = [
        ["yb", "-m", "window", "42", "--toggle", "float"],
        ["yb", "-m", "window", "42", "--resize", "abs:10:20"],
        ["yb", "-m", "window", "42", "--move", "abs:1:2"],
        ["yb", "-m", "window", "42", "--focus"],
    ]
    assert calls == expected


def test_take_screenshot_no_match(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr("wskr.tty.kitty_remote.query_windows", lambda x: [])
    caplog.set_level("ERROR")
    dst = tmp_path / "out.png"
    assert take_screenshot("y", lambda w: True, dst) is False
    assert "No matching window" in caplog.text


def test_take_screenshot_success(monkeypatch, tmp_path):
    monkeypatch.setattr("wskr.tty.kitty_remote.query_windows", lambda x: [{"id": 7}])

    # stub run to simulate success
    class Res:
        returncode = 0
        stderr = b""

    def fake_run(cmd, check):
        # create file to simulate screencapture side-effect
        dst = Path(cmd[-1])
        dst.write_text("", encoding="utf-8")
        return Res()

    monkeypatch.setattr("wskr.tty.kitty_remote.run", fake_run)
    dst = tmp_path / "img.png"
    ok = take_screenshot("y", lambda w: w["id"] == 7, dst)
    assert ok


def test_take_screenshot_failure(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr("wskr.tty.kitty_remote.query_windows", lambda x: [{"id": 3}])

    # return nonzero
    class Res:
        returncode = 1
        stderr = b"fail"

    monkeypatch.setattr("wskr.tty.kitty_remote.run", lambda cmd, check: Res())
    caplog.set_level("ERROR")
    dst = tmp_path / "img2.png"
    assert take_screenshot("y", lambda w: True, dst) is False
    assert "Screenshot failed" in caplog.text


def test_close_kitty_window(monkeypatch):
    # nested sessions → one matching
    sessions = [{"tabs": [{"windows": [{"id": 1}, {"id": 99}]}]}]
    monkeypatch.setattr("wskr.tty.kitty_remote.try_json_output", lambda cmd: sessions)
    calls = []
    monkeypatch.setattr(
        "wskr.tty.kitty_remote.run",
        lambda args, check=False, **kw: calls.append(args),
    )
    close_kitty_window("kit", lambda w: w["id"] == 99)
    assert calls == [["kit", "@", "close-window", "--match", "id:99"]]


def test_close_kitty_window_no_match(monkeypatch):
    monkeypatch.setattr("wskr.tty.kitty_remote.try_json_output", lambda cmd: [])
    called = False

    def fake_run(*args, **kw):
        nonlocal called
        called = True

    monkeypatch.setattr("wskr.tty.kitty_remote.run", fake_run)
    close_kitty_window("kit", lambda w: True)
    assert not called


class DummyPopen:
    def __init__(self, args, env):
        self.args = args
        self.env = env


def test_launch_kitty_terminal(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    proc = launch_kitty_terminal("kbin", "sock", "ttl", {"A": "B"})
    assert isinstance(proc, DummyPopen)
    assert proc.args == [
        "kbin",
        "-1",
        "--title",
        "ttl",
        "--override",
        "allow_remote_control=yes",
        "--listen-on",
        "sock",
    ]
    assert proc.env == {"A": "B"}


def test_send_kitty_command(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    send_kitty_command("kb", "sock", "echo hi", {"X": "Y"})
    # last call used our DummyPopen
    # unfortunately we can't inspect calls list, but no exception means correct signature


def test_get_window_id_success(tmp_path):
    f = tmp_path / "done"
    f.write_text(" 123 \n")
    val = get_window_id(f)
    assert val == 123
    assert f.read_text()


def test_get_window_id_failure(tmp_path):
    f = tmp_path / "bad"
    f.write_text("oops")
    with pytest.raises(SystemExit):
        get_window_id(f)
    assert f.read_text()


def test_show_log_no_file(caplog, tmp_path):
    caplog.set_level("ERROR")
    show_log(tmp_path / "none")
    assert "No log file found" in caplog.text


def test_show_log_with_file(caplog, tmp_path):
    caplog.set_level("DEBUG")
    f = tmp_path / "log"
    f.write_text("line1\nline2\n")
    show_log(f)
    txt = caplog.text
    assert "BEGIN KITTY SESSION LOG" in txt
    assert "[KITTY] line1" in txt
    assert "[KITTY] line2" in txt
    assert "END KITTY SESSION LOG" in txt


def test_cleanup_temp_files(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.write_text("")
    b.write_text("")
    # c does not exist
    c = tmp_path / "c"
    cleanup_temp_files(a, b, c)
    assert not a.exists()
    assert not b.exists()


def test_terminate_process_normal():
    actions = []

    class P:
        def poll(self):
            actions.append("poll")

        def terminate(self):
            actions.append("terminate")

        def wait(self, timeout=None):
            actions.append(f"wait({timeout})")

        def kill(self):
            actions.append("kill")

    terminate_process(P())
    assert actions == ["poll", "terminate", "wait(2)"]


def test_terminate_process_timeout(monkeypatch):
    actions = []

    class P2:
        def poll(self):
            actions.append("poll")

        def terminate(self):
            actions.append("terminate")

        def wait(self, timeout=None):
            actions.append(f"wait({timeout})")
            raise subprocess.TimeoutExpired(cmd="x", timeout=timeout)

        def kill(self):
            actions.append("kill")

    terminate_process(P2())
    assert actions == ["poll", "terminate", "wait(2)", "kill", "wait(2)"]


def test_terminate_process_permission_error(caplog):
    caplog.set_level("ERROR")

    class P3:
        def poll(self):
            return None

        def terminate(self):
            msg = "nope"
            raise PermissionError(msg)

        def wait(self, timeout=None):
            pass

        def kill(self):
            pass

    # should catch and log, not re-raise
    terminate_process(P3())
    assert "Failed to terminate kitty process" in caplog.text


def test_send_startup_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "wskr.tty.kitty_remote.send_kitty_command",
        lambda kb, sock, cmd, env: calls.append((kb, sock, cmd, env)),
    )
    done_f = Path("donefile")
    send_startup_command("kb", "sock", done_f, {"Z": "1"})
    _kb, _sock, cmd, env = calls[0]
    assert "yabai -m query --windows --window" in cmd
    assert str(done_f) in cmd
    assert env == {"Z": "1"}


def test_send_payload(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "wskr.tty.kitty_remote.send_kitty_command",
        lambda kb, sock, cmd, env: calls.append((kb, sock, cmd, env)),
    )
    script = Path("script.py")
    done_f = Path("done")
    log_f = Path("log")
    send_payload("kb", "sock", {"K": "V"}, script, done_f, log_f)
    _, _, cmd, env = calls[0]
    assert f"python '{script}'" in cmd
    assert str(log_f) in cmd
    assert str(done_f) in cmd
    assert env == {"K": "V"}
