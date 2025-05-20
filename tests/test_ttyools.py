import os
import termios

import pytest

from wskr import ttyools


class DummyFD:
    """Simulate a real TTY fd with minimal behavior."""

    def __init__(self):
        self.buffer = bytearray()
        self.drained = False

    def fileno(self):
        return 0


@pytest.fixture(autouse=True)
def fake_tty(monkeypatch, tmp_path):
    # Always return a fake file name for os.ttyname
    monkeypatch.setattr(os, "ttyname", lambda fd: str(tmp_path / "tty"))
    # Monkeypatch os.open to return a dummy fd number
    fake_fd = 99
    monkeypatch.setattr(os, "open", lambda *args, **kwargs: fake_fd)
    # Record closes
    closed = []
    monkeypatch.setattr(os, "close", closed.append)
    # Monkeypatch os.write so it doesn't error
    monkeypatch.setattr(os, "write", lambda fd, data: len(data))
    # Monkeypatch termios.tcdrain to be a no-op
    monkeypatch.setattr(termios, "tcdrain", lambda fd: None)
    # Monkeypatch tty_attributes to be a simple context
    monkeypatch.setattr(ttyools, "tty_attributes", lambda *args, **kwargs: (yield from []))
    # For select, always say no data
    monkeypatch.setattr("select.select", lambda r, w, x, t: ([], [], []))
    return closed


def test_write_tty_closes_fd(fake_tty):
    ttyools.write_tty(b"hello")
    assert fake_tty == [99], "write_tty should close its fd"


def test_read_tty_closes_fd(fake_tty):
    # read_tty returns immediately (no data), but must close
    data = ttyools.read_tty(timeout=0, min_bytes=0)
    assert data == b""  # no data read
    assert fake_tty == [99], "read_tty should close its fd"
