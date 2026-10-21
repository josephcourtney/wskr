"""Bounded, serialized Kitty graphics I/O over the caller's real TTY.

Transactions never write escapes to redirected stdout and never consume
keyboard input unless the caller explicitly owns the terminal input stream.
"""

from __future__ import annotations

import os
import select
import sys
import termios
from threading import RLock
from time import monotonic
from typing import TYPE_CHECKING

from wskr.core.errors import TransportRuntimeError, TransportUnavailableError
from wskr.protocol.kitty_codec import parse_response

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

_TTY_LOCK = RLock()
_MAX_WRITE_TIMEOUT = 30.0
_MAX_QUERY_TIMEOUT = 5.0
_MAX_QUERY_REQUEST_BYTES = 512
_MAX_QUERY_BYTES = 4096
_MAX_APC_BYTES = 1024


def _require_tty() -> None:
    if sys.stdout is None or not sys.stdout.isatty():
        msg = "Native Kitty graphics requires TTY stdout; redirects are unsupported"
        raise TransportUnavailableError(msg)


def _open() -> int:
    """Open the same TTY that is attached to stdout, not another controlling TTY."""
    try:
        name = os.ttyname(sys.stdout.fileno())
        return os.open(name, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    except (AttributeError, OSError, ValueError) as exc:
        msg = "Cannot open the terminal attached to stdout"
        raise TransportUnavailableError(msg) from exc


def _send(fd: int, frame: bytes, deadline: float) -> None:
    remaining = memoryview(frame)
    while remaining:
        left = deadline - monotonic()
        if left <= 0 or not select.select([], [fd], [], left)[1]:
            msg = "Kitty graphics write deadline expired"
            raise TimeoutError(msg)
        try:
            count = os.write(fd, remaining)
        except BlockingIOError:
            continue
        if count <= 0:
            msg = "Kitty graphics write made no progress"
            raise TransportRuntimeError(msg)
        remaining = remaining[count:]


def send_frames(frames: Iterable[bytes], *, timeout: float = 5.0) -> None:
    """Write a complete frame sequence atomically relative to other wskr writers."""
    _require_tty()
    if not 0 < timeout <= _MAX_WRITE_TIMEOUT:
        msg = "Kitty write deadline must be in (0, 30]"
        raise ValueError(msg)
    with _TTY_LOCK:
        fd = _open()
        try:
            deadline = monotonic() + timeout
            for frame in frames:
                _send(fd, frame, deadline)
        finally:
            os.close(fd)


def _read_reply(fd: int, deadline: float, unmatched: bytearray, pending: bytearray) -> bytes:
    """Find one bounded APC reply without swallowing unrelated terminal bytes."""
    consumed = 0
    while consumed < _MAX_QUERY_BYTES:
        left = deadline - monotonic()
        if left <= 0 or not select.select([fd], [], [], left)[0]:
            msg = "Kitty graphics query timed out"
            raise TimeoutError(msg)
        try:
            ch = os.read(fd, 1)
        except BlockingIOError:
            continue
        if not ch:
            continue
        consumed += 1
        pending.extend(ch)
        if not b"\x1b_G".startswith(pending) and not pending.startswith(b"\x1b_G"):
            unmatched.extend(pending)
            pending.clear()
        elif pending.startswith(b"\x1b_G") and pending.endswith(b"\x1b\\"):
            response = bytes(pending)
            pending.clear()
            return response
        elif len(pending) > _MAX_APC_BYTES:
            unmatched.extend(pending)
            pending.clear()
    if pending:
        unmatched.extend(pending)
        pending.clear()
    msg = "Kitty graphics reply exceeded bounded input limit"
    raise TransportRuntimeError(msg)


def query_support(
    request: bytes,
    *,
    expected_id: int,
    owns_input: bool = False,
    on_unmatched: Callable[[bytes], None] | None = None,
    timeout: float = 0.35,
) -> bool:
    """Confirm support only with an ACK, routing unrelated bytes to their owner.

    The caller must own the input stream and supply a way to preserve
    unrelated bytes. No query occurs by default.
    """
    if not owns_input or on_unmatched is None:
        msg = "Kitty probing requires exclusive input ownership and a byte handler"
        raise TransportUnavailableError(msg)
    _require_tty()
    if not 0 < timeout <= _MAX_QUERY_TIMEOUT:
        msg = "Kitty query deadline must be in (0, 5]"
        raise ValueError(msg)
    if not request.startswith(b"\x1b_Ga=q,") or not request.endswith(b"\x1b\\") or len(request) > _MAX_QUERY_REQUEST_BYTES:
        msg = "Only bounded Kitty graphics capability queries are permitted"
        raise ValueError(msg)
    with _TTY_LOCK:
        fd = _open()
        previous = None
        unmatched = bytearray()
        pending = bytearray()
        try:
            previous = termios.tcgetattr(fd)
            attrs = termios.tcgetattr(fd)
            attrs[3] &= ~(termios.ICANON | termios.ECHO)
            attrs[6][termios.VMIN] = 0
            attrs[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            deadline = monotonic() + timeout
            _send(fd, request, deadline)
            while True:
                response = _read_reply(fd, deadline, unmatched, pending)
                try:
                    header = response.removeprefix(b"\x1b_G").split(b";", 1)[0]
                    identities = [part[2:] for part in header.split(b",") if part.startswith(b"i=")]
                    image_id = int(identities[0])
                except (IndexError, ValueError):
                    unmatched.extend(response)
                    continue
                if image_id != expected_id:
                    unmatched.extend(response)
                    continue
                # A negative response from the requested image is a
                # definitive rejection, not unrelated terminal input.
                parse_response(response, expected_id=expected_id)
                return True
        finally:
            try:
                if previous is not None:
                    termios.tcsetattr(fd, termios.TCSANOW, previous)
            finally:
                os.close(fd)
                if pending:
                    unmatched.extend(pending)
                if unmatched:
                    on_unmatched(bytes(unmatched))


__all__ = ["query_support", "send_frames"]
