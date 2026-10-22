"""PTY-based native Kitty graphics I/O integration tests.

These test real kernel terminal descriptors and termios behavior without
requiring an installed Kitty emulator or GUI session.
"""

from __future__ import annotations

import os
import select
import sys
import termios
import threading
from typing import TYPE_CHECKING

import pytest

from wskr.core.errors import TransportRuntimeError
from wskr.protocol import kitty_io
from wskr.protocol.kitty_codec import probe_request

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.medium


class _TtyOutput:
    def __init__(self, fd: int) -> None:
        self.fd = fd

    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return self.fd


@pytest.fixture
def owned_pty(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[int, int]]:
    master, slave = os.openpty()
    monkeypatch.setattr(kitty_io, "_require_tty", lambda: None)
    monkeypatch.setattr(kitty_io, "_open", lambda: os.dup(slave))
    try:
        yield master, slave
    finally:
        os.close(master)
        os.close(slave)


def _reply(image_id: int, status: bytes = b"OK") -> bytes:
    return b"\x1b_Gi=" + str(image_id).encode() + b";" + status + b"\x1b\\"


def _assert_effective_attributes_restored(slave: int, before: list) -> None:
    """Ignore PENDIN, a kernel-managed pending-input state on BSD/macOS."""
    after = termios.tcgetattr(slave)
    previous = before.copy()
    pending = getattr(termios, "PENDIN", 0)
    after[3] &= ~pending
    previous[3] &= ~pending
    assert after == previous


def test_bound_image_writer_uses_stdout_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    """A writer must target the terminal attached to stdout, never another TTY."""
    master, slave = os.openpty()
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(sys, "stdout", _TtyOutput(slave))
            fd = kitty_io._open()
        try:
            assert os.ttyname(fd) == os.ttyname(slave)
        finally:
            os.close(fd)
    finally:
        os.close(master)
        os.close(slave)


def test_actual_pty_frame_write(owned_pty: tuple[int, int]) -> None:
    master, _ = owned_pty
    frame = b"\x1b_Ga=p,i=3,p=7,c=3,r=2,U=1\x1b\\"
    kitty_io.send_frames((frame,))
    assert select.select([master], [], [], 1.0)[0]
    assert os.read(master, 4096) == frame


def test_owned_query_forwards_unmatched_and_restores_attributes(owned_pty: tuple[int, int]) -> None:
    master, slave = owned_pty
    before = termios.tcgetattr(slave)
    request = probe_request(99)
    observed: list[bytes] = []

    def responder() -> None:
        observed.append(os.read(master, 4096))
        os.write(master, b"t" + _reply(1) + _reply(99))

    worker = threading.Thread(target=responder)
    worker.start()
    unmatched: list[bytes] = []
    try:
        assert kitty_io.query_support(
            request, expected_id=99, owns_input=True, on_unmatched=unmatched.append, timeout=2.0
        )
    finally:
        worker.join(timeout=2.0)
    assert not worker.is_alive()
    assert observed == [request]
    assert unmatched == [b"t" + _reply(1)]
    _assert_effective_attributes_restored(slave, before)


def test_negative_ack_restores_attributes(owned_pty: tuple[int, int]) -> None:
    master, slave = owned_pty
    before = termios.tcgetattr(slave)

    def responder() -> None:
        os.read(master, 4096)
        os.write(master, _reply(99, b"ENOENT:not found"))

    worker = threading.Thread(target=responder)
    worker.start()
    try:
        with pytest.raises(TransportRuntimeError, match="rejected"):
            kitty_io.query_support(
                probe_request(99),
                expected_id=99,
                owns_input=True,
                on_unmatched=lambda _data: None,
                timeout=2.0,
            )
    finally:
        worker.join(timeout=2.0)
    assert not worker.is_alive()
    _assert_effective_attributes_restored(slave, before)


def test_timeout_preserves_partial_reply(owned_pty: tuple[int, int]) -> None:
    master, slave = owned_pty
    before = termios.tcgetattr(slave)
    partial = b"\x1b_Gi=99;OK"

    def responder() -> None:
        os.read(master, 4096)
        os.write(master, partial)

    worker = threading.Thread(target=responder)
    worker.start()
    unmatched: list[bytes] = []
    try:
        with pytest.raises(TimeoutError):
            kitty_io.query_support(
                probe_request(99),
                expected_id=99,
                owns_input=True,
                on_unmatched=unmatched.append,
                timeout=0.5,
            )
    finally:
        worker.join(timeout=2.0)
    assert not worker.is_alive()
    assert unmatched == [partial]
    _assert_effective_attributes_restored(slave, before)
