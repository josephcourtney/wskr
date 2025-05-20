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

    def fake_run(cmd, input=None, stdout=None, check=None, timeout=None, **kwargs):
        # ensure timeout was passed
        seen["t"] = timeout

    monkeypatch.setattr(subprocess, "run", fake_run)
    kt = KittyTransport()
    kt.send_image(b"foo")
    assert seen.get("t") == 1.0
