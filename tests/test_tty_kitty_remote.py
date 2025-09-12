import shutil
import subprocess
from pathlib import Path

import pytest

from wskr.terminal.kitty import kitty_remote
from wskr.terminal.kitty.kitty_remote import (
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


@pytest.mark.parametrize(
    ("present", "name", "expect_error"),
    [
        (True, "foo", False),
        (False, "missing", True),
    ],
)
def test_find_executable(monkeypatch, caplog, present, name, expect_error):
    monkeypatch.setattr(shutil, "which", lambda n: f"/usr/bin/{n}" if present else None)
    if expect_error:
        caplog.set_level("ERROR")
        with pytest.raises(FileNotFoundError):
            find_executable(name)
        assert "not found in PATH" in caplog.text
    else:
        assert find_executable(name) == f"/usr/bin/{name}"


@pytest.mark.parametrize(
    ("capture_output", "check", "patch_attr", "ret"),
    [
        (True, False, "check_output", b"stdout"),
        (
            False,
            True,
            "run",
            subprocess.CompletedProcess(args=["x"], returncode=0),
        ),
    ],
)
def test_run_dispatch(monkeypatch, capture_output, check, patch_attr, ret):
    monkeypatch.setattr(kitty_remote.runner, patch_attr, lambda *a, **k: ret)
    res = run(["cmd"], capture_output=capture_output, check=check, timeout=0.1)
    assert res == ret


@pytest.mark.parametrize(
    ("payload", "expect_none"),
    [(b'[{"id":1}]', False), (b"not json", True)],
)
def test_try_json_output(monkeypatch, caplog, payload, expect_none):
    monkeypatch.setattr(
        "wskr.terminal.kitty.kitty_remote.run",
        lambda cmd, capture_output, **kw: payload,
    )
    if expect_none:
        caplog.set_level("DEBUG")
        assert try_json_output(["cmd"]) is None
        assert "JSON parsing failed" in caplog.text
    else:
        result = try_json_output(["cmd"])
        assert isinstance(result, list)
        assert result[0]["id"] == 1


def test_abort_raises_system_exit():
    with pytest.raises(SystemExit):
        _abort("fatal error")


@pytest.mark.parametrize(
    ("exists", "has_content", "exc"),
    [
        (True, True, None),
        (False, False, TimeoutError),
    ],
)
def test_wait_for_file_with_content(tmp_path, exists, has_content, exc):
    p = tmp_path / "f"
    if exists:
        p.write_text("content" if has_content else "")
    if exc is None:
        wait_for_file_with_content(p, timeout=1.0)
    else:
        with pytest.raises(exc):
            wait_for_file_with_content(p, timeout=0.0)


@pytest.mark.parametrize(("present", "exc"), [(True, None), (False, SystemExit)])
def test_wait_for_file_to_exist(tmp_path, present, exc):
    p = tmp_path / "exists"
    if present:
        p.write_text("x")
    if exc is None:
        wait_for_file_to_exist(p, timeout=0.1)
    else:
        with pytest.raises(exc):
            wait_for_file_to_exist(p, timeout=0.0)


def test_query_windows(monkeypatch):
    monkeypatch.setattr("wskr.terminal.kitty.kitty_remote.try_json_output", lambda cmd: [{"a": 1}])
    assert query_windows("yabai") == [{"a": 1}]
    monkeypatch.setattr("wskr.terminal.kitty.kitty_remote.try_json_output", lambda cmd: None)
    assert query_windows("yabai") == []


def test_configure_window_all_options(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "wskr.terminal.kitty.kitty_remote.run",
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


@pytest.mark.parametrize(
    ("mode", "expect_ok", "expect_log"),
    [
        ("no_match", False, "No matching window"),
        ("success", True, None),
        ("failure", False, "Screenshot failed"),
    ],
)
def test_take_screenshot_variants(monkeypatch, tmp_path, caplog, mode, expect_ok, expect_log):
    if mode == "no_match":
        monkeypatch.setattr("wskr.terminal.kitty.kitty_remote.query_windows", lambda x: [])
    else:
        monkeypatch.setattr("wskr.terminal.kitty.kitty_remote.query_windows", lambda x: [{"id": 7}])

    if mode == "success":

        class Res:
            returncode = 0
            stderr = b""

        def fake_run(cmd, check):
            Path(cmd[-1]).write_text("", encoding="utf-8")
            return Res()

        monkeypatch.setattr("wskr.terminal.kitty.kitty_remote.run", fake_run)
    elif mode == "failure":

        class Res:
            returncode = 1
            stderr = b"fail"

        monkeypatch.setattr("wskr.terminal.kitty.kitty_remote.run", lambda cmd, check: Res())

    if expect_log:
        caplog.set_level("ERROR")

    dst = tmp_path / "img.png"
    ok = take_screenshot("y", lambda w: True if mode != "success" else w["id"] == 7, dst)
    assert ok is expect_ok
    if expect_log:
        assert expect_log in caplog.text


@pytest.mark.parametrize("has_match", [True, False])
def test_close_kitty_window_variants(monkeypatch, has_match):
    sessions = [{"tabs": [{"windows": [{"id": 1}, {"id": 99}]}]}] if has_match else []
    monkeypatch.setattr("wskr.terminal.kitty.kitty_remote.try_json_output", lambda cmd: sessions)
    calls = []
    monkeypatch.setattr("wskr.terminal.kitty.kitty_remote.run", lambda args, **kw: calls.append(args))
    close_kitty_window("kit", lambda w: w.get("id") == 99)
    if has_match:
        assert calls == [["kit", "@", "close-window", "--match", "id:99"]]
    else:
        assert calls == []


def test_launch_kitty_terminal(monkeypatch, popen_recorder):
    proc = launch_kitty_terminal("kbin", Path("sock"), "ttl", {"A": "B"})
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
    assert popen_recorder["calls"][0][1] == {"A": "B"}


def test_send_kitty_command(popen_recorder):
    send_kitty_command("kb", Path("sock"), "echo hi", {"X": "Y"})


@pytest.mark.parametrize(("content", "raises"), [(" 123 \n", None), ("oops", SystemExit)])
def test_get_window_id_variants(tmp_path, content, raises):
    f = tmp_path / "done"
    f.write_text(content)
    if raises is None:
        assert get_window_id(f) == 123
    else:
        with pytest.raises(raises):
            get_window_id(f)
    assert f.read_text()


@pytest.mark.parametrize("present", [False, True])
def test_show_log_variants(caplog, tmp_path, present):
    if not present:
        caplog.set_level("ERROR")
        show_log(tmp_path / "none")
        assert "No log file found" in caplog.text
    else:
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


@pytest.mark.parametrize(
    ("mode", "expected_actions"),
    [
        ("normal", ["poll", "terminate", "wait(2)"]),
        ("timeout", ["poll", "terminate", "wait(2)", "kill", "wait(2)"]),
    ],
)
def test_terminate_process_actions(mode, expected_actions):
    actions: list[str] = []

    if mode == "normal":

        class P:
            def poll(self):
                actions.append("poll")

            def terminate(self):
                actions.append("terminate")

            def wait(self, timeout=None):
                actions.append(f"wait({timeout})")

            def kill(self):
                actions.append("kill")

        terminate_process(P())  # type:ignore[invalid-argument-type]
    else:

        class P2:
            def poll(self):
                actions.append("poll")

            def terminate(self):
                actions.append("terminate")

            def wait(self, timeout=None):
                actions.append(f"wait({timeout})")
                raise subprocess.TimeoutExpired(cmd="x", timeout=float(timeout))

            def kill(self):
                actions.append("kill")

        terminate_process(P2())  # type:ignore[invalid-argument-type]

    assert actions == expected_actions


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

    terminate_process(P3())  # type:ignore[invalid-argument-type]
    assert "Failed to terminate kitty process" in caplog.text


def test_send_startup_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "wskr.terminal.kitty.kitty_remote.send_kitty_command",
        lambda kb, sock, cmd, env: calls.append((kb, sock, cmd, env)),
    )
    done_f = Path("donefile")
    send_startup_command("kb", Path("sock"), done_f, {"Z": "1"})
    _kb, _sock, cmd, env = calls[0]
    assert "yabai -m query --windows --window" in cmd
    assert str(done_f) in cmd
    assert env == {"Z": "1"}


def test_send_payload(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "wskr.terminal.kitty.kitty_remote.send_kitty_command",
        lambda kb, sock, cmd, env: calls.append((kb, sock, cmd, env)),
    )
    script = Path("script.py")
    done_f = Path("done")
    log_f = Path("log")
    send_payload("kb", Path("sock"), {"K": "V"}, script, done_f, log_f)
    _, _, cmd, env = calls[0]
    assert f"python '{script}'" in cmd
    assert str(log_f) in cmd
    assert str(done_f) in cmd
    assert env == {"K": "V"}
