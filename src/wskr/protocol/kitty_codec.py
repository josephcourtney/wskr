"""Pure Kitty graphics-protocol framing and response parsing.

No terminal I/O occurs in this module. This codec is shared by plain
Matplotlib rendering and future Rich virtual/Unicode placements.
"""

from __future__ import annotations

import base64
import re
from typing import TYPE_CHECKING

from wskr.core.errors import TransportRuntimeError

if TYPE_CHECKING:
    from collections.abc import Iterator

ESC = b"\x1b"
APC = ESC + b"_G"
ST = ESC + b"\\"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_CHUNK = 4096
MAX_ID = 0xFFFFFFFF
_ACK = re.compile(rb"^\x1b_G([^;]{1,160});([^\x1b]{1,512})\x1b\\$")


def _identifier(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= MAX_ID:
        raise ValueError("Kitty image and placement IDs must be integers from 1 to 2**32-1")
    return value


def _dimension(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
        raise ValueError("Kitty placement dimensions must be in [1, 65535]")
    return value


def command(**fields: str | int) -> bytes:
    """Frame a control-only Kitty graphics command."""
    return APC + ",".join(f"{key}={value}" for key, value in fields.items()).encode("ascii") + b";" + ST


def transmit(
    png: bytes,
    image_id: int,
    *,
    display: bool = False,
    placement_id: int | None = None,
    quiet: int = 2,
) -> Iterator[bytes]:
    """Yield a complete, non-interleavable sequence of Base64 PNG chunks.

    The first chunk supplies f=100 and image metadata; continuation chunks
    supply only m and (optionally) q. Every chunk payload is at most 4096 bytes.
    """
    _identifier(image_id)
    if not png.startswith(PNG_SIGNATURE):
        raise ValueError("Kitty PNG upload requires PNG signature")
    if placement_id is not None:
        _identifier(placement_id)
        if not display:
            raise ValueError("A placement ID requires display=True")
    if quiet not in (0, 1, 2):
        raise ValueError("Invalid Kitty quiet mode")
    payload = base64.b64encode(png)
    chunks = [payload[i : i + MAX_CHUNK] for i in range(0, len(payload), MAX_CHUNK)]
    for i, chunk in enumerate(chunks):
        m = int(i < len(chunks) - 1)
        if i == 0:
            fields: dict[str, str | int] = {
                "a": "T" if display else "t", "f": 100, "t": "d",
                "i": image_id, "q": quiet,
            }
            if placement_id is not None:
                fields["p"] = placement_id
            fields["m"] = m
        else:
            fields = {"m": m, "q": quiet}
        yield APC + ",".join(f"{k}={v}" for k, v in fields.items()).encode("ascii") + b";" + chunk + ST


def placement(
    image_id: int,
    placement_id: int,
    columns: int,
    rows: int,
    *,
    virtual: bool = False,
    quiet: int = 2,
) -> bytes:
    """Create or replace a placement; virtual placements do not move the cursor."""
    _identifier(image_id)
    _identifier(placement_id)
    _dimension(columns)
    _dimension(rows)
    if quiet not in (0, 1, 2):
        raise ValueError("Invalid Kitty quiet mode")
    fields: dict[str, str | int] = {
        "a": "p", "i": image_id, "p": placement_id,
        "c": columns, "r": rows,
    }
    if virtual:
        fields["U"] = 1
    else:
        fields["C"] = 1
    fields["q"] = quiet
    return command(**fields)


def delete(image_id: int, *, placement_id: int | None = None, free: bool = False) -> bytes:
    """Delete only the caller-owned image or placement, never the entire screen."""
    _identifier(image_id)
    fields: dict[str, str | int] = {"a": "d", "d": "I" if free else "i", "i": image_id}
    if placement_id is not None:
        _identifier(placement_id)
        fields["p"] = placement_id
    fields["q"] = 2
    return command(**fields)


def probe_request(image_id: int) -> bytes:
    """Create an isolated, one-pixel query requiring a real Kitty ACK."""
    _identifier(image_id)
    # Kitty a=q accepts a one-pixel RGBA sample with explicit dimensions.
    return APC + f"a=q,f=32,s=1,v=1,i={image_id},t=d;".encode() + base64.b64encode(b"\0\0\0\0") + ST


def parse_response(reply: bytes, *, expected_id: int | None = None) -> tuple[int, int | None]:
    """Validate a complete Kitty ACK, returning (image ID, optional placement ID).

    A negative status or a mismatched ID is not capability evidence.
    """
    match = _ACK.fullmatch(reply)
    if match is None:
        raise TransportRuntimeError("Malformed or incomplete Kitty graphics acknowledgement")
    fields: dict[bytes, bytes] = {}
    for pair in match.group(1).split(b","):
        if b"=" not in pair:
            raise TransportRuntimeError("Malformed Kitty graphics acknowledgement field")
        key, value = pair.split(b"=", 1)
        fields[key] = value
    try:
        image_id = _identifier(int(fields[b"i"]))
        placement_id = _identifier(int(fields[b"p"])) if b"p" in fields else None
    except (ValueError, KeyError) as exc:
        raise TransportRuntimeError("Invalid Kitty graphics acknowledgement identity") from exc
    if expected_id is not None and image_id != expected_id:
        raise TransportRuntimeError("Kitty graphics acknowledgement belongs to another image")
    if match.group(2) != b"OK":
        detail = match.group(2).decode("ascii", errors="replace")
        raise TransportRuntimeError(f"Kitty graphics operation rejected: {detail}")
    return image_id, placement_id


__all__ = [
    "MAX_CHUNK", "MAX_ID", "command", "delete", "parse_response", "placement",
    "probe_request", "transmit",
]
