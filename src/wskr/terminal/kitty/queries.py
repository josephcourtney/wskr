"""Pure, strict Kitty XTGETTCAP codecs for runtime terminal measurements.

Kitty-specific names use the documented "kitty-query-" XTGETTCAP prefix.
Queries are read-only; frame parsing never communicates with a terminal.
"""

from __future__ import annotations

import re

QUERY_FIELDS = frozenset({
    "name",
    "font_family",
    "font_size",
    "dpi_x",
    "dpi_y",
    "foreground",
    "background",
    "background_opacity",
})
_MAX_VALUE_BYTES = 256
_CONTROL_LIMIT = ord(' ')
_DELETE_CHAR = 0x7F
_RESPONSE = re.compile(rb"^\x1bP([01])\+r([0-9A-Fa-f]+)(?:=([0-9A-Fa-f]*))?\x1b\\$")


def query_request(field: str) -> bytes:
    """Construct a read-only capability request for a known Kitty field."""
    if field not in QUERY_FIELDS:
        msg = f"Unknown or disallowed Kitty query field: {field!r}"
        raise ValueError(msg)
    name = f"kitty-query-{field}".encode("ascii").hex().encode("ascii")
    return b"\x1bP+q" + name + b"\x1b\\"


def parse_query_reply(field: str, response: bytes) -> str | None:
    """Return the exact decoded value only for the requested successful key."""
    request = query_request(field)
    if len(response) > _MAX_VALUE_BYTES:
        return None
    match = _RESPONSE.fullmatch(response)
    if match is None or match[1] != b"1":
        return None
    if match[2].lower() != request[4:-2].lower() or match[3] is None:
        return None
    try:
        value = bytes.fromhex(match[3].decode("ascii")).decode("utf-8", errors="strict")
    except (ValueError, UnicodeDecodeError):
        return None
    return value if value and not any(ord(ch) < _CONTROL_LIMIT or ord(ch) == _DELETE_CHAR for ch in value) else None


__all__ = ["QUERY_FIELDS", "parse_query_reply", "query_request"]
