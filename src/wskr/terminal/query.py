"""Explicit-ownership, bounded terminal OSC query transactions.

Raw terminal replies and user keystrokes share an input stream. There is no
portable way to put consumed bytes back, so callers must explicitly own input
and supply a handler for unrelated input before this function opens a TTY.
"""

from __future__ import annotations

import os
import select
import termios
from collections.abc import Callable
from time import monotonic


class TerminalQueryError(RuntimeError):
    """Terminal ownership, framing or deadline could not be established."""


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
        raise TerminalQueryError("OSC queries require exclusive input ownership and an unmatched-byte handler")
    if not 0 < timeout <= 5 or not 1 <= max_bytes <= 4096:
        raise ValueError("Invalid terminal query timeout or maximum reply size")
    if not (request.startswith(b"\x1b]") and request.endswith((b"\x07", b"\x1b\\"))):
        raise ValueError("Only complete OSC requests are permitted")

    fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    old = None
    unmatched = bytearray()
    result = bytearray()
    try:
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] &= ~(termios.ICANON | termios.ECHO)
        new[6][termios.VMIN] = 0
        new[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, new)
        pending = memoryview(request)
        while pending:
            writable = select.select([], [fd], [], timeout)[1]
            if not writable:
                raise TimeoutError("Terminal query write timed out")
            pending = pending[os.write(fd, pending):]
        deadline = monotonic() + timeout
        while len(result) < max_bytes:
            left = deadline - monotonic()
            if left <= 0:
                raise TimeoutError("Terminal query response timed out")
            if not select.select([fd], [], [], left)[0]:
                raise TimeoutError("Terminal query response timed out")
            chunk = os.read(fd, 1)
            if not chunk:
                continue
            byte = chunk[0]
            if not result and byte != 0x1B:
                unmatched.extend(chunk)
                continue
            result.append(byte)
            if len(result) == 2 and result != b"\x1b]":
                unmatched.extend(result)
                result.clear()
                continue
            if result.endswith((b"\x07", b"\x1b\\")):
                if not result.startswith(b"\x1b]"):
                    raise TerminalQueryError("Unexpected terminal response")
                return bytes(result)
        raise TerminalQueryError("Terminal response exceeded size limit")
    finally:
        try:
            if old is not None:
                termios.tcsetattr(fd, termios.TCSANOW, old)
        finally:
            os.close(fd)
            if unmatched:
                on_unmatched(bytes(unmatched))


__all__ = ["TerminalQueryError", "query_osc"]
