import shutil
import subprocess
import sys
from io import BytesIO

import pytest

from wskr.tty import kitty
from wskr.tty.kitty import KittyTransport


def test_kitty_transport_init_fails(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="not available"):
        kitty.KittyTransport()


def test_send_chunk_chunked_mode(monkeypatch):
    class FakeStdout:
        def __init__(self):
            self.buffer = BytesIO()
            self.written = []

        def flush(self):
            self.buffer.seek(0)

        def write(self, text):
            self.written.append(text)

    fake_stdout = FakeStdout()
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    KittyTransport._send_chunk(1, b"abc", final=True)

    output = fake_stdout.buffer.getvalue()
    assert output.startswith(b"\x1b_G")
    assert b"abc" in output


def test_send_chunk_writes(monkeypatch):
    class FakeStdout:
        def __init__(self):
            self.buffer = BytesIO()

        def flush(self):
            self.buffer.seek(0)

    monkeypatch.setattr(sys, "stdout", FakeStdout())
    KittyTransport._send_chunk(1, b"abc", final=True)


class DummyProc:
    def __init__(self, stdout):
        self.stdout = stdout


def test_get_window_size_px_caches_and_computes(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    calls = []

    def fake_run(args, capture_output=None, text=None, check=None, timeout=None, **kwargs):
        calls.append(args)
        return type("P", (), {"stdout": "80x120"})()

    monkeypatch.setattr(subprocess, "run", fake_run)

    kt = KittyTransport()
    first = kt.get_window_size_px()
    second = kt.get_window_size_px()
    assert first == second
    assert len(calls) == 1
    assert first == (80, 120 - (3 * 120) // 24)


def test_tput_lines_failure(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(cmd, capture_output=None, text=None, check=None, timeout=None, **kwargs):
        if "+kitten" in cmd:
            return type("P", (), {"stdout": "10x20"})()
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    kt2 = KittyTransport()
    size = kt2.get_window_size_px()
    assert size == (10, 20 - (3 * 20) // 24)


@pytest.fixture(autouse=True)
def fake_which(monkeypatch):
    # ensure kitty binary is “found”
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")


def test_get_window_size_px_uses_timeout(monkeypatch):
    def fake_run(args, capture_output, text, check, timeout):
        # we expect our 1.0s timeout
        assert timeout == 1.0
        # return something parseable
        return type("P", (), {"stdout": "100x200"})()

    monkeypatch.setattr(subprocess, "run", fake_run)
    kt = KittyTransport()
    w, _h = kt.get_window_size_px()
    assert w == 100


def test_send_image_uses_timeout(monkeypatch):
    seen = {}

    def fake_run(cmd, input=None, stdout=None, check=None, timeout=None, **kwargs):  # noqa: A002
        # ensure timeout was passed
        seen["t"] = timeout

    monkeypatch.setattr(subprocess, "run", fake_run)
    kt = KittyTransport()
    kt.send_image(b"foo")
    assert seen.get("t") == 1.0


def test_get_window_size_px_fallback(monkeypatch):
    def bad_run(*a, **k):
        raise subprocess.CalledProcessError(1, a[0])

    monkeypatch.setattr(subprocess, "run", bad_run)
    kt = KittyTransport()
    assert kt.get_window_size_px() == (800, 600)


def test_get_window_size_px_bad_output(monkeypatch):
    def fake_run(*a, **k):
        return type("P", (), {"stdout": "oops"})()

    monkeypatch.setattr(subprocess, "run", fake_run)
    kt = KittyTransport()
    assert kt.get_window_size_px() == (800, 600)


def test_tput_lines_not_found(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert KittyTransport._tput_lines() == 24


def test_tput_lines_parse_error(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(*a, **k):
        return type("P", (), {"stdout": "bad"})()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert KittyTransport._tput_lines() == 24


def test_send_image_logs_error(monkeypatch, caplog):
    def bad_run(*a, **k):
        raise subprocess.CalledProcessError(1, a[0])

    monkeypatch.setattr(subprocess, "run", bad_run)
    kt = KittyTransport()
    with caplog.at_level("ERROR"):
        kt.send_image(b"foo")
    assert any("Error sending image" in r.message for r in caplog.records)


def test_init_image_success(monkeypatch, dummy_png):
    sent = []
    monkeypatch.setattr(KittyTransport, "_send_chunk", lambda self, n, c, final=False: sent.append((n, c, final)))
    monkeypatch.setattr("wskr.tty.kitty.query_tty", lambda *a, **k: b"\x1b_Gi=5,i=1;OK\x1b\\")
    kt = KittyTransport()
    img_id = kt.init_image(dummy_png)
    assert img_id == 5
    assert sent[-1][2] is True


def test_init_image_no_response(monkeypatch, dummy_png):
    monkeypatch.setattr(KittyTransport, "_send_chunk", lambda *a, **k: None)
    monkeypatch.setattr("wskr.tty.kitty.query_tty", lambda *a, **k: b"")
    kt = KittyTransport()
    with pytest.raises(RuntimeError, match="No response"):
        kt.init_image(dummy_png)


def test_init_image_bad_response(monkeypatch, dummy_png):
    monkeypatch.setattr(KittyTransport, "_send_chunk", lambda *a, **k: None)
    monkeypatch.setattr("wskr.tty.kitty.query_tty", lambda *a, **k: b"\x1b_Gi=7,i=2;FAIL\x1b\\")
    kt = KittyTransport()
    with pytest.raises(RuntimeError, match="Unexpected"):
        kt.init_image(dummy_png)
