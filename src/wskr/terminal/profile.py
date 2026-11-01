"""Runtime terminal measurements with explicit provenance.

Importing this module does not open or query a terminal. Only measured values
are labelled MEASURED; missing observations remain unavailable rather than
silently acquiring machine-specific display/DPI assumptions.
"""

from __future__ import annotations

import fcntl
import re
import struct
import sys
import termios
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, TypeVar

from wskr.terminal.color import RGB, parse_osc_color

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


class Source(StrEnum):
    MEASURED = "measured"
    INFERRED = "inferred"
    CONFIGURED = "configured"
    HINT = "hint"
    FALLBACK = "fallback"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Value[T]:
    value: T | None = None
    source: Source = Source.UNKNOWN

    def __post_init__(self) -> None:
        """Enforce correspondence between unknown values and provenance."""
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


_CSI_SIZE = re.compile(rb"^\x1b\[([46]);([0-9]{1,6});([0-9]{1,6})t$")


def _query_csi_pixels(query: Callable[[bytes], bytes], *, command: int, response: int) -> tuple[int, int] | None:
    """Parse only a matched CSI size reply from an input-owning caller."""
    try:
        reply = query(f"\x1b[{command}t".encode("ascii"))
        match = _CSI_SIZE.fullmatch(reply)
        if match is None or int(match[1]) != response:
            return None
        height, width = int(match[2]), int(match[3])
    except (OSError, RuntimeError, ValueError, TimeoutError):
        return None
    return (width, height) if height > 0 and width > 0 else None


def _axis_pixels(
    kernel: int, cells: int, window: int, cell: int
) -> tuple[Value[int], Value[float]]:
    """Choose measured kernel/query values, inferring only missing geometry."""
    pixel = kernel if kernel > 0 else window
    pixel_source = Source.MEASURED if pixel > 0 else Source.UNKNOWN
    cell_size = float(cell) if cell > 0 else None
    cell_source = Source.MEASURED if cell_size is not None else Source.UNKNOWN
    if pixel <= 0 and cell_size is not None:
        pixel = round(cells * cell_size)
        pixel_source = Source.INFERRED
    if cell_size is None and pixel > 0:
        cell_size = pixel / cells
        cell_source = Source.INFERRED
    pixel_value = Value(pixel, pixel_source) if pixel > 0 else Value()
    cell_value = Value(cell_size, cell_source) if cell_size is not None else Value()
    return pixel_value, cell_value


def _geometry_measurements(
    geom: Geometry, query: Callable[[bytes], bytes] | None
) -> tuple[Value[int], Value[int], Value[float], Value[float]]:
    """Apply terminal and kernel authority independently on each dimension."""
    window = (
        _query_csi_pixels(query, command=14, response=4)
        if query is not None and (geom.width_px <= 0 or geom.height_px <= 0)
        else None
    )
    cell = _query_csi_pixels(query, command=16, response=6) if query is not None else None
    width, cell_width = _axis_pixels(
        geom.width_px, geom.columns, window[0] if window else 0, cell[0] if cell else 0
    )
    height, cell_height = _axis_pixels(
        geom.height_px, geom.rows, window[1] if window else 0, cell[1] if cell else 0
    )
    return width, height, cell_width, cell_height


def probe_profile(
    *,
    geometry: Geometry | None = None,
    color_query: Callable[[bytes], bytes] | None = None,
    palette: bool = False,
    geometry_query: Callable[[bytes], bytes] | None = None,
) -> TerminalProfile:
    """Build a profile; only an explicitly supplied color callback may query.

    color_query accepts OSC requests; geometry_query accepts CSI size requests.
    The caller must own terminal input and preserve unrelated bytes. Neither
    callback is installed implicitly; no escapes are emitted by default.
    """
    geom = geometry if geometry is not None else read_geometry()
    if geom is None or geom.rows <= 0 or geom.columns <= 0:
        return TerminalProfile()

    width, height, cell_width, cell_height = _geometry_measurements(geom, geometry_query)
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
