"""Runtime terminal measurements with explicit provenance.

Importing this module does not open or query a terminal. Only measured values
are labelled MEASURED; missing observations remain unavailable rather than
silently acquiring machine-specific display/DPI assumptions.
"""

from __future__ import annotations

import fcntl
import struct
import sys
import termios
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

from wskr.terminal.color import RGB, parse_osc_color

T = TypeVar("T")


class Source(StrEnum):
    MEASURED = "measured"
    INFERRED = "inferred"
    CONFIGURED = "configured"
    HINT = "hint"
    FALLBACK = "fallback"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Value(Generic[T]):
    value: T | None = None
    source: Source = Source.UNKNOWN

    def __post_init__(self) -> None:
        if (self.value is None) != (self.source == Source.UNKNOWN):
            msg = "A missing value must have unknown provenance and vice versa"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Geometry:
    rows: int
    columns: int
    width_px: int = 0
    height_px: int = 0


@dataclass(frozen=True, slots=True)
class TerminalProfile:
    rows: Value[int] = Value()
    columns: Value[int] = Value()
    width_px: Value[int] = Value()
    height_px: Value[int] = Value()
    cell_width_px: Value[float] = Value()
    cell_height_px: Value[float] = Value()
    foreground: Value[RGB] = Value()
    background: Value[RGB] = Value()
    ansi_palette: Value[tuple[RGB | None, ...]] = Value()
    font_family: Value[str] = Value()
    font_size_pt: Value[float] = Value()
    dpi_x: Value[float] = Value()
    dpi_y: Value[float] = Value()
    opacity: Value[float] = Value()
    graphics: Value[str] = Value()

    @property
    def is_dark(self) -> bool | None:
        return self.background.value.is_dark if self.background.value is not None else None


def read_geometry() -> Geometry | None:
    """Read kernel terminal geometry without transmitting escape sequences.

    Redirected stdout is not interrogated, even if a controlling TTY exists.
    """
    stream = sys.stdout
    try:
        if stream is None or not stream.isatty():
            return None
        fd = stream.fileno()
        packed = fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\x00" * 8)
        rows, cols, width, height = struct.unpack("HHHH", packed)
    except (OSError, ValueError, struct.error):
        return None
    if rows <= 0 or cols <= 0:
        return None
    return Geometry(rows, cols, width, height)


def probe_profile(
    *,
    geometry: Geometry | None = None,
    color_query: Callable[[bytes], bytes] | None = None,
    palette: bool = False,
) -> TerminalProfile:
    """Build a profile; only an explicitly supplied color callback may query.

    color_query is a callable accepting an OSC request and returning response
    bytes. Callers must own the input stream; see query.query_osc for a guarded
    implementation. No terminal query is initiated by default.
    """
    geom = geometry if geometry is not None else read_geometry()
    if geom is None or geom.rows <= 0 or geom.columns <= 0:
        return TerminalProfile()

    width = Value(geom.width_px, Source.MEASURED) if geom.width_px > 0 else Value()
    height = Value(geom.height_px, Source.MEASURED) if geom.height_px > 0 else Value()
    cell_width = Value(geom.width_px / geom.columns, Source.INFERRED) if geom.width_px > 0 else Value()
    cell_height = Value(geom.height_px / geom.rows, Source.INFERRED) if geom.height_px > 0 else Value()
    colors: dict[int, RGB] = {}
    if color_query is not None:
        indices = [(10, None), (11, None)]
        if palette:
            indices.extend((4, i) for i in range(16))
        for code, index in indices:
            request = f"\x1b]{code};{index};?\x07".encode() if index is not None else f"\x1b]{code};?\x07".encode()
            try:
                response = color_query(request)
                rgb = parse_osc_color(response, code, index)
            except (OSError, RuntimeError, ValueError, TimeoutError):
                continue
            colors[code if index is None else 100 + index] = rgb
    fg = colors.get(10)
    bg = colors.get(11)
    entries = tuple(colors.get(100 + i) for i in range(16))
    return TerminalProfile(
        rows=Value(geom.rows, Source.MEASURED),
        columns=Value(geom.columns, Source.MEASURED),
        width_px=width,
        height_px=height,
        cell_width_px=cell_width,
        cell_height_px=cell_height,
        foreground=Value(fg, Source.MEASURED) if fg is not None else Value(),
        background=Value(bg, Source.MEASURED) if bg is not None else Value(),
        ansi_palette=Value(entries, Source.MEASURED) if any(e is not None for e in entries) else Value(),
    )


__all__ = ["Geometry", "Source", "TerminalProfile", "Value", "probe_profile", "read_geometry"]
