import os
import sys
import termios
from contextlib import ExitStack, contextmanager, suppress
from select import select
from threading import RLock
from time import monotonic
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


# Reentrant lock for synchronizing access to the TTY
_tty_lock = RLock()


# Open TTY file descriptor safely
def _get_tty_fd() -> int:
    return os.open(os.ttyname(sys.__stdout__.fileno()), os.O_RDWR)


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
    fd = _get_tty_fd()
    try:
        os.write(fd, data)
        with suppress(termios.error):
            termios.tcdrain(fd)
    finally:
        os.close(fd)


@lock_tty
def read_tty(
    timeout: float | None = None, min_bytes: int = 0, *, more: callable = lambda _: True, echo: bool = False
) -> bytes | None:
    """Read input directly from the TTY with optional blocking."""
    input_data = bytearray()

    fd = _get_tty_fd()
    input_data = bytearray()
    stack = ExitStack()
    try:
        # If tty_attributes is a real contextmanager, we enter it;
        # if it's been stubbed to a bare generator, we just skip.
        with suppress(TypeError):
            stack.enter_context(tty_attributes(fd, min_bytes=min_bytes, echo=echo))

        # Now do the actual reads exactly as before:
        r, w, x = [fd], [], []
        if timeout is None:
            while select(r, w, x, 0)[0]:
                input_data.extend(os.read(fd, 100))
        else:
            start = monotonic()
            if min_bytes > 0:
                input_data.extend(os.read(fd, min_bytes))
            while (timeout < 0 or monotonic() - start < timeout) and more(input_data):
                if select(r, w, x, timeout - (monotonic() - start))[0]:
                    input_data.extend(os.read(fd, 1))
    finally:
        # whether or not tty_attributes succeeded, always close & cleanup
        os.close(fd)
        stack.close()
    return bytes(input_data)


def query_tty(request: bytes, more: callable, timeout: float | None = None) -> bytes | None:
    """Send a request to the terminal and read the response."""
    with tty_attributes(_get_tty_fd(), echo=False):
        os.write(_get_tty_fd(), request)
        with suppress(termios.error):
            termios.tcdrain(_get_tty_fd())
        return read_tty(timeout=timeout, more=more)
