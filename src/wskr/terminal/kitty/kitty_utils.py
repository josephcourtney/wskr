"""Utilities for querying colour information from Kitty terminals."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wskr.terminal.core.ttyools import query_tty

if TYPE_CHECKING:
    from collections.abc import Iterable

OSC = "\x1b]"
ST = "\x07"

KITTY_COLOR_KEYS = (
    "foreground",
    "background",
    "selection_foreground",
    "selection_background",
    "cursor",
    "cursor_text",
    "visual_bell",
    *[f"transparent_background_color{n}" for n in range(1, 8)],
    *[str(k) for k in range(16)],
)

_RESP_RE = re.compile(rb"(?:\]21;|;)([^=]+)=rgb:([0-9A-Fa-f]{2})/([0-9A-Fa-f]{2})/([0-9A-Fa-f]{2})")


def _parse_response(resp: bytes) -> dict[str, tuple[int, int, int] | None]:
    result: dict[str, tuple[int, int, int] | None] = {}
    for match in _RESP_RE.finditer(resp):
        key = match.group(1).decode()
        r, g, b = (int(p, 16) for p in match.groups()[1:])
        result[key] = (r, g, b)
    return result


def query_colors(
    keys: Iterable[str] = KITTY_COLOR_KEYS,
    *,
    timeout: float | None = None,
) -> dict[str, tuple[int, int, int] | None]:
    """Query Kitty for the given colour ``keys``.

    Returns a mapping of key to ``(r, g, b)`` tuples in 0-255 range. Missing
    keys yield ``None`` values.
    """
    body = ";".join(f"{k}=?" for k in keys)
    req = f"{OSC}21;{body}{ST}".encode()
    resp = query_tty(req, more=lambda b: not b.endswith(ST.encode()), timeout=timeout)
    if not resp:
        return {}
    return _parse_response(resp)


def query_kitty_color(
    key: str,
    *,
    timeout: float | None = None,
) -> tuple[int, int, int] | None:
    """Return the Kitty colour for ``key`` or ``None`` if unavailable."""
    return query_colors([key], timeout=timeout).get(key)


__all__ = ["KITTY_COLOR_KEYS", "query_colors", "query_kitty_color"]
