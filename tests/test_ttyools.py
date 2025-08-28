import os
import termios

import pytest

from wskr.terminal.core import ttyools


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
    monkeypatch.setattr(ttyools, "select", lambda r, w, x, t: ([], [], []))
    return closed


def test_write_tty_closes_fd(fake_tty):
    ttyools.write_tty(b"hello")
    assert fake_tty == [99], "write_tty should close its fd"


def test_read_tty_closes_fd(fake_tty):
    # read_tty returns immediately (no data), but must close
    data = ttyools.read_tty(timeout=0, min_bytes=0)
    assert data == b""  # no data read
    assert fake_tty == [99], "read_tty should close its fd"


def test_read_tty_more_predicate(monkeypatch):
    monkeypatch.setattr(ttyools, "_get_tty_fd", lambda: 42)
    monkeypatch.setattr(os, "close", lambda fd: None)
    monkeypatch.setattr(ttyools, "tty_attributes", lambda *a, **k: (yield from []))
    monkeypatch.setattr(ttyools, "select", lambda r, w, x, t: ([], [], []))
    called = []

    def more(data: bytes) -> bool:
        called.append(data)
        return False

    assert ttyools.read_tty(timeout=1, more=more) == b""
    assert called == [b""]


def test_query_tty_single_fd(monkeypatch, tmp_path):
    fake_fd = 77
    opens: list[int] = []
    closes: list[int] = []

    monkeypatch.setattr(os, "ttyname", lambda fd: str(tmp_path / "tty"))
    monkeypatch.setattr(os, "open", lambda *a, **k: (opens.append(1), fake_fd)[1])
    monkeypatch.setattr(os, "close", closes.append)
    monkeypatch.setattr(os, "write", lambda fd, data: len(data))
    monkeypatch.setattr(termios, "tcdrain", lambda fd: None)

    called_fd: list[int | None] = []

    def fake_read_tty(*, fd: int | None, **kwargs: object) -> bytes:
        called_fd.append(fd)
        return b"resp"

    monkeypatch.setattr(ttyools.TTY_IO, "read", fake_read_tty)

    resp = ttyools.query_tty(b"req", more=lambda b: False, timeout=0)
    assert resp == b"resp"
    assert opens == [1]
    assert closes == [fake_fd]
    assert called_fd == [fake_fd]
