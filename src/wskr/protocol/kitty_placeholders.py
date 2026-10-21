"""Rich-independent Unicode placeholder encoder for Kitty virtual placements.

This is an opt-in presentation primitive, not a Rich renderable. The caller
must first upload an image and create a U=1 virtual placement; terminal text
and style ownership remain with the application.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from wskr.protocol.kitty_codec import MAX_ID

MAX_VIRTUAL_PLACEMENT_ID = 0xFFFFFF
_PLACEHOLDER = "\U0010EEEE"
_TABLE = Path(__file__).with_name("rowcolumn-diacritics.txt")


@lru_cache(maxsize=1)
def diacritics() -> tuple[str, ...]:
    """Load the protocol-owned row/column combining-character table."""
    points = re.findall(r"\\U([0-9A-Fa-f]{8})", _TABLE.read_text(encoding="utf-8"))
    return tuple(chr(int(code, 16)) for code in points)


def _sgr_id(value: int, selector: int) -> str:
    """Encode the low 24 bits of an identifier as a true-color SGR sequence."""
    red = (value >> 16) & 255
    green = (value >> 8) & 255
    blue = value & 255
    return f"\x1b[{selector};2;{red};{green};{blue}m"


def placeholder_rows(
    image_id: int,
    placement_id: int,
    *,
    columns: int,
    rows: int,
) -> tuple[str, ...]:
    """Encode fixed-identity Unicode placeholders for a virtual placement.

    Explicit row and column diacritics avoid inheritance errors in layouts
    with scrolling, wrapping or overlapping images.
    """
    if not 1 <= image_id <= MAX_ID:
        msg = "Kitty placeholder image IDs must be positive 32-bit integers"
        raise ValueError(msg)
    if not 1 <= placement_id <= MAX_VIRTUAL_PLACEMENT_ID:
        msg = "Kitty placeholder placement IDs must fit in 24-bit underline color"
        raise ValueError(msg)
    table = diacritics()
    if not 1 <= columns <= len(table) or not 1 <= rows <= len(table):
        msg = "Kitty placeholder rows/columns exceed the diacritic table"
        raise ValueError(msg)
    high = image_id >> 24
    suffix = table[high] if high else ""
    prefix = _sgr_id(image_id, 38) + _sgr_id(placement_id, 58)
    return tuple(
        prefix + "".join(_PLACEHOLDER + table[row] + table[col] + suffix for col in range(columns)) + "\x1b[39;59m"
        for row in range(rows)
    )


__all__ = ["MAX_VIRTUAL_PLACEMENT_ID", "diacritics", "placeholder_rows"]
