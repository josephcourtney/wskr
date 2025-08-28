import contextlib
import os
import termios

from wskr.terminal.core import ttyools


def test_tty_attributes_roundtrip(monkeypatch):
    fake_attr = [0, 0, 0, 0, 0, 0, [0] * 32]
    calls = []
    monkeypatch.setattr(termios, "tcgetattr", lambda fd: fake_attr.copy())
    monkeypatch.setattr(termios, "tcsetattr", lambda fd, when, attr: calls.append(attr.copy()))
    with ttyools.tty_attributes(1, min_bytes=1, echo=True):
        pass
    # two calls: set new attributes then restore original
    assert len(calls) == 2
    new_attr = calls[0]
    assert new_attr[6][termios.VMIN] == 1
    assert new_attr[3] & termios.ECHO
    assert calls[1][3] == fake_attr[3]


def test_read_tty_variants(monkeypatch):
    monkeypatch.setattr(ttyools, "_get_tty_fd", lambda: 99)
    monkeypatch.setattr(os, "close", lambda fd: None)
    monkeypatch.setattr(termios, "tcdrain", lambda fd: None)
    monkeypatch.setattr(ttyools, "tty_attributes", lambda *a, **k: contextlib.nullcontext())

    # timeout None branch
    reads = [b"a", b"b", b""]
    monkeypatch.setattr(os, "read", lambda fd, n: reads.pop(0) if reads else b"")
    monkeypatch.setattr(
        ttyools,
        "select",
        lambda r, w, x, t: ([99], [], []) if reads else ([], [], []),
    )
    assert ttyools.read_tty(timeout=None, min_bytes=0) == b"ab"

    # timeout with min_bytes branch
    reads2 = [b"X", b"Y"]
    monkeypatch.setattr(os, "read", lambda fd, n: b"Z" if n > 1 else (reads2.pop(0) if reads2 else b""))
    monkeypatch.setattr(
        ttyools,
        "select",
        lambda r, w, x, t: ([99], [], []) if reads2 else ([], [], []),
    )
    out = ttyools.read_tty(timeout=0.1, min_bytes=2, more=lambda b: len(b) < 4)
    assert out.startswith(b"Z")


def test_query_tty(monkeypatch):
    monkeypatch.setattr(ttyools, "_get_tty_fd", lambda: 55)
    writes = []
    monkeypatch.setattr(os, "write", lambda fd, data: writes.append((fd, data)))
    monkeypatch.setattr(termios, "tcdrain", lambda fd: None)
    monkeypatch.setattr(os, "close", lambda fd: None)
    monkeypatch.setattr(
        ttyools.TTY_IO, "read", lambda *, fd=None, timeout=None, more=None, echo=False: b"resp"
    )
    resp = ttyools.query_tty(b"req", more=lambda b: True)
    assert resp == b"resp"
    assert writes == [(55, b"req")]
