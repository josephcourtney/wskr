"""Explicit-ownership, bounded terminal OSC query transactions.

Raw terminal replies and user keystrokes share an input stream. There is no
portable way to put consumed bytes back, so callers must explicitly own input
and supply a handler for unrelated input before this function opens a TTY.
"""

from __future__ import annotations

import os
import select
import sys
import termios
from threading import RLock
from time import monotonic
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class TerminalQueryError(RuntimeError):
    """Terminal ownership, framing or deadline could not be established."""


_QUERY_LOCK = RLock()
_MAX_TIMEOUT_SECONDS = 5.0
_MAX_QUERY_BYTES = 4096
_ESCAPE_BYTE = 0x1B
_OSC_HEADER_LENGTH = len(b"\x1b]")


def _open_tty() -> int:
    return os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)


def _stdout_is_tty() -> bool:
    return sys.stdout is not None and sys.stdout.isatty()


def query_osc(
    request: bytes,
    *,
    owns_input: bool = False,
    on_unmatched: Callable[[bytes], None] | None = None,
    timeout: float = 0.15,
    max_bytes: int = 256,
) -> bytes:
    """Issue one OSC query only when the caller owns and can route TTY input.

    Uses /dev/tty (not redirected stdout); restores termios before closing the
    descriptor, including on timeout, interruption and malformed data.
    Unrelated input is reported through on_unmatched rather than discarded.
    """
    if not owns_input or on_unmatched is None:
        msg = "OSC queries require exclusive input ownership and an unmatched-byte handler"
        raise TerminalQueryError(msg)
    if not _stdout_is_tty():
        msg = "OSC queries require an attached terminal output stream"
        raise TerminalQueryError(msg)
    if not 0 < timeout <= _MAX_TIMEOUT_SECONDS or not 1 <= max_bytes <= _MAX_QUERY_BYTES:
        msg = "Invalid terminal query timeout or maximum reply size"
        raise ValueError(msg)
    if not (request.startswith(b"\x1b]") and request.endswith((b"\x07", b"\x1b\\"))):
        msg = "Only complete OSC requests are permitted"
        raise ValueError(msg)

    with _QUERY_LOCK:
        return _transaction(request, on_unmatched=on_unmatched, timeout=timeout, max_bytes=max_bytes)


def _write_request(fd: int, request: bytes, deadline: float) -> None:
    """Write the entire OSC request without extending the transaction deadline."""
    offset = 0
    while offset < len(request):
        remaining = deadline - monotonic()
        if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
            msg = "Terminal query write timed out"
            raise TimeoutError(msg)
        written = os.write(fd, request[offset:])
        if written <= 0:
            msg = "Terminal query write made no progress"
            raise TerminalQueryError(msg)
        offset += written


def _next_reply_byte(fd: int, deadline: float) -> bytes:
    """Read at most one byte before the transaction's shared deadline."""
    remaining = deadline - monotonic()
    if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
        msg = "Terminal query response timed out"
        raise TimeoutError(msg)
    try:
        return os.read(fd, 1)
    except BlockingIOError:
        return b""


def _receive_reply(
    fd: int,
    expected: bytes,
    deadline: float,
    max_bytes: int,
    unmatched: bytearray,
    partial: bytearray,
) -> bytes:
    """Read bounded input, forwarding unrelated frames to the owner's buffer."""
    received = 0
    while received < max_bytes:
        chunk = _next_reply_byte(fd, deadline)
        if not chunk:
            continue
        received += len(chunk)
        if not partial and chunk[0] != _ESCAPE_BYTE:
            unmatched.extend(chunk)
            continue
        partial.extend(chunk)
        if len(partial) == _OSC_HEADER_LENGTH and partial != b"\x1b]":
            unmatched.extend(partial)
            partial.clear()
            continue
        if partial.endswith((b"\x07", b"\x1b\\")):
            if partial.startswith(expected):
                response = bytes(partial)
                partial.clear()
                return response
            unmatched.extend(partial)
            partial.clear()
    msg = "Terminal response exceeded size limit"
    raise TerminalQueryError(msg)


def _transaction(
    request: bytes,
    *,
    on_unmatched: Callable[[bytes], None],
    timeout: float,
    max_bytes: int,
) -> bytes:
    fd = _open_tty()
    previous = None
    unmatched = bytearray()
    partial = bytearray()
    marker = request.removeprefix(b"\x1b]").split(b";?", 1)[0] + b";"
    expected = b"\x1b]" + marker
    try:
        previous = termios.tcgetattr(fd)
        attributes = termios.tcgetattr(fd)
        attributes[3] &= ~(termios.ICANON | termios.ECHO)
        attributes[6][termios.VMIN] = 0
        attributes[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, attributes)
        deadline = monotonic() + timeout
        _write_request(fd, request, deadline)
        return _receive_reply(fd, expected, deadline, max_bytes, unmatched, partial)
    finally:
        try:
            if previous is not None:
                termios.tcsetattr(fd, termios.TCSANOW, previous)
        finally:
            os.close(fd)
            if partial:
                unmatched.extend(partial)
            if unmatched:
                on_unmatched(bytes(unmatched))


__all__ = ["TerminalQueryError", "query_osc"]
