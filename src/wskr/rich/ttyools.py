# ruff: noqa: PLW3201
import os
import sys
import termios
from contextlib import contextmanager, suppress
from select import select
from threading import RLock
from time import monotonic
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


# Reentrant lock for synchronizing access to the TTY
_tty_lock = RLock()

# Open TTY file descriptor safely
_tty_fd = os.open(os.ttyname(sys.__stdout__.fileno()), os.O_RDWR)


@contextmanager
def tty_attributes(fd: int, min_bytes: int = 0, *, echo: bool = False) -> None:
    """Context manager to set and reset terminal attributes."""
    old_attr = termios.tcgetattr(fd)
    new_attr = termios.tcgetattr(fd)

    # Disable canonical mode, set VMIN, VTIME, and echo
    new_attr[3] &= ~termios.ICANON  # Disable canonical mode
    new_attr[6][termios.VTIME] = 0  # Disable time-based blocking
    new_attr[6][termios.VMIN] = min_bytes  # Min bytes to read

    if echo:
        new_attr[3] |= termios.ECHO  # Enable echo
    else:
        new_attr[3] &= ~termios.ECHO  # Disable echo

    try:
        termios.tcsetattr(fd, termios.TCSANOW, new_attr)
        yield
    finally:
        # Restore terminal attributes
        termios.tcsetattr(fd, termios.TCSANOW, old_attr)


def lock_tty(func):
    """Decorate function to lock access to TTY."""

    def wrapper(*args, **kwargs):
        with _tty_lock:
            return func(*args, **kwargs)

    return wrapper


@lock_tty
def write_tty(data: bytes) -> None:
    """Write data to the TTY."""
    os.write(_tty_fd, data)
    with suppress(termios.error):
        termios.tcdrain(_tty_fd)


@lock_tty
def read_tty(
    timeout: float | None = None, min_bytes: int = 0, *, more: callable = lambda _: True, echo: bool = False
) -> bytes | None:
    """Read input directly from the TTY with optional blocking."""
    input_data = bytearray()

    with tty_attributes(_tty_fd, min_bytes=min_bytes, echo=echo):
        r, w, x = [_tty_fd], [], []

        # Read without blocking
        if timeout is None:
            while select(r, w, x, 0)[0]:
                input_data.extend(os.read(_tty_fd, 100))
        else:
            # Start the timeout-based reading
            start = monotonic()
            duration = 0

            # Read min_bytes initially if required
            if min_bytes > 0:
                input_data.extend(os.read(_tty_fd, min_bytes))

            while (timeout < 0 or duration < timeout) and more(input_data):
                if select(r, w, x, timeout - duration)[0]:
                    input_data.extend(os.read(_tty_fd, 1))
                duration = monotonic() - start

    return bytes(input_data)


def query_tty(request: bytes, more: callable, timeout: float | None = None) -> bytes | None:
    """Send a request to the terminal and read the response."""
    with tty_attributes(_tty_fd, echo=False):
        os.write(_tty_fd, request)
        with suppress(termios.error):
            termios.tcdrain(_tty_fd)
        return read_tty(timeout=timeout, more=more)
