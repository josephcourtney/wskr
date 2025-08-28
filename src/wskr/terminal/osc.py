from __future__ import annotations

from .io import TTY_IO, MorePredicate


def query_tty(request: bytes, more: MorePredicate, timeout: float | None = None) -> bytes:
    """Send a request to the terminal and read the response."""
    return TTY_IO.query(request, more, timeout)


__all__ = ["query_tty"]
