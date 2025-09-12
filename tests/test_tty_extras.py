import contextlib
import os
import termios

from wskr.terminal import io, osc


def test_write_tty_closes_fd(fake_tty):
    # ensure write_tty opens and closes the TTY fd
    io.write_tty(b"hello")
    assert fake_tty == [99]


def test_read_tty_closes_fd(fake_tty):
    # read_tty should return immediately (no data) and still close fd
    data = io.read_tty(timeout=0, min_bytes=0)
    assert data == b""
    assert fake_tty == [99]


def test_read_tty_more_predicate(monkeypatch):
    # verify the `more` predicate is invoked at least once
    monkeypatch.setattr(io, "_get_tty_fd", lambda: 42)
    monkeypatch.setattr(os, "close", lambda fd: None)
    monkeypatch.setattr(io, "tty_attributes", lambda *a, **k: contextlib.nullcontext())
    monkeypatch.setattr(io, "select", lambda r, w, x, t: ([], [], []))
    called: list[bytes] = []

    def more(data: bytes) -> bool:
        called.append(data)
        return False

    assert io.read_tty(timeout=1, more=more) == b""
    assert called == [b""]


def test_query_tty_single_fd(monkeypatch, tmp_path):
    # validate open/close lifecycle and the fd passed to TTY_IO.read
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

    monkeypatch.setattr(io.TTY_IO, "read", fake_read_tty)

    resp = osc.query_tty(b"req", more=lambda b: False, timeout=0)
    assert resp == b"resp"
    assert opens == [1]
    assert closes == [fake_fd]
    assert called_fd == [fake_fd]


def test_tty_attributes_roundtrip(monkeypatch):
    fake_attr = [0, 0, 0, 0, 0, 0, [0] * 32]
    calls = []
    monkeypatch.setattr(termios, "tcgetattr", lambda fd: fake_attr.copy())
    monkeypatch.setattr(termios, "tcsetattr", lambda fd, when, attr: calls.append(attr.copy()))
    with io.tty_attributes(1, min_bytes=1, echo=True):
        pass
    # two calls: set new attributes then restore original
    assert len(calls) == 2
    new_attr = calls[0]
    assert new_attr[6][termios.VMIN] == 1
    assert new_attr[3] & termios.ECHO
    assert calls[1][3] == fake_attr[3]


def test_read_tty_variants(monkeypatch):
    monkeypatch.setattr(io, "_get_tty_fd", lambda: 99)
    monkeypatch.setattr(os, "close", lambda fd: None)
    monkeypatch.setattr(termios, "tcdrain", lambda fd: None)
    monkeypatch.setattr(io, "tty_attributes", lambda *a, **k: contextlib.nullcontext())

    # timeout None branch
    reads = [b"a", b"b", b""]
    monkeypatch.setattr(os, "read", lambda fd, n: reads.pop(0) if reads else b"")
    monkeypatch.setattr(
        io,
        "select",
        lambda r, w, x, t: ([99], [], []) if reads else ([], [], []),
    )
    assert io.read_tty(timeout=None, min_bytes=0) == b"ab"

    # timeout with min_bytes branch
    reads2 = [b"X", b"Y"]
    monkeypatch.setattr(os, "read", lambda fd, n: b"Z" if n > 1 else (reads2.pop(0) if reads2 else b""))
    monkeypatch.setattr(
        io,
        "select",
        lambda r, w, x, t: ([99], [], []) if reads2 else ([], [], []),
    )
    out = io.read_tty(timeout=0.1, min_bytes=2, more=lambda b: len(b) < 4)
    assert out.startswith(b"Z")


def test_query_tty(monkeypatch):
    monkeypatch.setattr(io, "_get_tty_fd", lambda: 55)
    writes = []
    monkeypatch.setattr(os, "write", lambda fd, data: writes.append((fd, data)))
    monkeypatch.setattr(termios, "tcdrain", lambda fd: None)
    monkeypatch.setattr(os, "close", lambda fd: None)
    monkeypatch.setattr(io.TTY_IO, "read", lambda *, fd=None, timeout=None, more=None, echo=False: b"resp")
    resp = osc.query_tty(b"req", more=lambda b: True)
    assert resp == b"resp"
    assert writes == [(55, b"req")]
