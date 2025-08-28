import os
import sys
import termios
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator
from contextlib import ExitStack, contextmanager, suppress
from select import select
from threading import RLock
from time import monotonic

# Predicate used to determine whether more bytes should be read
MorePredicate = Callable[[bytes], bool]


# Reentrant lock for synchronizing access to the TTY
_tty_lock = RLock()


# Open TTY file descriptor safely
def _get_tty_fd() -> int:
    stdout_fn = sys.__stdout__
    if stdout_fn is None:
        msg = "failed to get stdout file descriptor"
        raise RuntimeError(msg)
    return os.open(os.ttyname(stdout_fn.fileno()), os.O_RDWR)


@contextmanager
def tty_attributes(fd: int, min_bytes: int = 0, *, echo: bool = False) -> Generator:
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


class TtyIO(ABC):
    """Interface for terminal I/O operations."""

    @abstractmethod
    def write(self, data: bytes) -> None:
        """Write ``data`` to the terminal."""

    @abstractmethod
    def read(
        self,
        *,
        timeout: float | None = None,
        min_bytes: int = 0,
        more: MorePredicate = lambda _b: True,
        echo: bool = False,
        fd: int | None = None,
    ) -> bytes:
        """Read data from the terminal."""

    def query(self, request: bytes, more: MorePredicate, timeout: float | None = None) -> bytes:
        """Send ``request`` then read the response."""
        self.write(request)
        return self.read(timeout=timeout, more=more)


class PosixTtyIO(TtyIO):
    """POSIX implementation of :class:`TtyIO`."""

    @lock_tty
    def write(self, data: bytes) -> None:
        _ = self
        fd = _get_tty_fd()
        try:
            os.write(fd, data)
            with suppress(termios.error):
                termios.tcdrain(fd)
        finally:
            os.close(fd)

    @lock_tty
    def read(
        self,
        *,
        timeout: float | None = None,
        min_bytes: int = 0,
        more: MorePredicate = lambda _b: True,
        echo: bool = False,
        fd: int | None = None,
    ) -> bytes:
        _ = self
        input_data = bytearray()

        owns_fd = fd is None
        if fd is None:
            fd = _get_tty_fd()
        stack = ExitStack()
        try:
            with suppress(TypeError):
                stack.enter_context(tty_attributes(fd, min_bytes=min_bytes, echo=echo))

            r, w, x = [fd], [], []
            if timeout is None:
                while select(r, w, x, 0)[0]:
                    input_data.extend(os.read(fd, 100))
            else:
                start = monotonic()
                if min_bytes > 0:
                    input_data.extend(os.read(fd, min_bytes))
                while (timeout < 0 or monotonic() - start < timeout) and more(bytes(input_data)):
                    if select(r, w, x, timeout - (monotonic() - start))[0]:
                        input_data.extend(os.read(fd, 1))
        finally:
            if owns_fd:
                os.close(fd)
            stack.close()
        return bytes(input_data)

    @lock_tty
    def query(self, request: bytes, more: MorePredicate, timeout: float | None = None) -> bytes:
        fd = _get_tty_fd()
        try:
            os.write(fd, request)
            with suppress(termios.error):
                termios.tcdrain(fd)
            return self.read(timeout=timeout, more=more, fd=fd)
        finally:
            os.close(fd)


TTY_IO = PosixTtyIO()


def write_tty(data: bytes) -> None:
    """Write data to the TTY using the default :class:`TtyIO`."""
    TTY_IO.write(data)


def read_tty(
    timeout: float | None = None,
    min_bytes: int = 0,
    *,
    more: MorePredicate = lambda _b: True,
    echo: bool = False,
    fd: int | None = None,
) -> bytes:
    """Read input directly from the TTY with optional blocking."""
    return TTY_IO.read(timeout=timeout, min_bytes=min_bytes, more=more, echo=echo, fd=fd)


__all__ = [
    "TTY_IO",
    "MorePredicate",
    "PosixTtyIO",
    "TtyIO",
    "lock_tty",
    "read_tty",
    "tty_attributes",
    "write_tty",
]
