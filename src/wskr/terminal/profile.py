"""Runtime terminal measurements with explicit provenance.

Importing this module does not open or query a terminal. Only measured values
are labelled MEASURED; missing observations remain unavailable rather than
silently acquiring machine-specific display/DPI assumptions.
"""

from __future__ import annotations

import fcntl
import math
import os
import re
import struct
import sys
import termios
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, TypeVar

from wskr.terminal.color import RGB, parse_osc_color
from wskr.terminal.kitty.queries import parse_query_reply
from wskr.terminal.query import TerminalQueryError, query_csi, query_kitty_field, query_osc

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

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


def _axis_pixels(kernel: int, cells: int, window: int, cell: int) -> tuple[Value[int], Value[float]]:
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
    width, cell_width = _axis_pixels(geom.width_px, geom.columns, window[0] if window else 0, cell[0] if cell else 0)
    height, cell_height = _axis_pixels(geom.height_px, geom.rows, window[1] if window else 0, cell[1] if cell else 0)
    return width, height, cell_width, cell_height


_PROFILE_CONTEXT: ContextVar[TerminalProfile | None] = ContextVar("wskr_terminal_profile", default=None)


def current_profile() -> TerminalProfile | None:
    """Return an explicitly supplied profile in this execution context, if any."""
    return _PROFILE_CONTEXT.get()


@contextmanager
def use_profile(profile: TerminalProfile) -> Generator[None]:
    """Scope measured appearance to normal pyplot figure construction.

    This never changes global rcParams and does not query the terminal.
    """
    token = _PROFILE_CONTEXT.set(profile)
    try:
        yield
    finally:
        _PROFILE_CONTEXT.reset(token)


_KITTY_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_MAX_KITTY_FONT_NAME = 128
_KITTY_NUMERIC_LIMITS = {
    "font_size": (2.0, 100.0),
    "dpi_x": (20.0, 1000.0),
    "dpi_y": (20.0, 1000.0),
    "background_opacity": (0.0, 1.0),
}
_KITTY_FIELDS = ("font_family", "font_size", "dpi_x", "dpi_y", "background_opacity", "foreground", "background")


def _kitty_value(field: str, raw: str) -> Value | None:
    """Interpret only plausible Kitty numeric, font, and RGB measurements."""
    if field in {"foreground", "background"}:
        if _KITTY_COLOR.fullmatch(raw):
            return Value(RGB(*(int(raw[i : i + 2], 16) for i in (1, 3, 5))), Source.MEASURED)
        return None
    if field == "font_family":
        return Value(raw, Source.MEASURED) if len(raw) <= _MAX_KITTY_FONT_NAME else None
    limits = _KITTY_NUMERIC_LIMITS.get(field)
    if limits is None:
        return None
    try:
        number = float(raw)
    except ValueError:
        return None
    return Value(number, Source.MEASURED) if math.isfinite(number) and limits[0] <= number <= limits[1] else None


def _kitty_measurements(query: Callable[[str], bytes] | None) -> dict[str, Value]:
    """Validate read-only Kitty capability results without fabricating values."""
    if query is None:
        return {}
    measurements: dict[str, Value] = {}
    for field in _KITTY_FIELDS:
        try:
            raw = parse_query_reply(field, query(field))
        except (OSError, RuntimeError, ValueError, TimeoutError):
            continue
        candidate = _kitty_value(field, raw) if raw is not None else None
        if candidate is not None:
            measurements[field] = candidate
    return measurements


def _foreground_tty_owned() -> bool:
    """Reject mismatched, redirected and background foreground terminal inputs."""
    if sys.stdin is None or sys.stdout is None:
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    try:
        input_fd = sys.stdin.fileno()
        return os.ttyname(input_fd) == os.ttyname(sys.stdout.fileno()) and os.tcgetpgrp(input_fd) == os.getpgrp()
    except (OSError, ValueError):
        return False


def probe_owned_profile(
    *,
    owns_input: bool = False,
    on_unmatched: Callable[[bytes], None] | None = None,
    palette: bool = True,
    timeout: float = 0.15,
) -> TerminalProfile:
    """Actively read runtime geometry and Kitty appearance ONLY with input ownership.

    The caller must own the foreground terminal and replay every unmatched
    byte into its application input queue. Standard pyplot never calls this.
    """
    if not owns_input or on_unmatched is None:
        msg = "Terminal profile probing requires exclusive input ownership and an unmatched-byte handler"
        raise TerminalQueryError(msg)
    if not _foreground_tty_owned():
        msg = "Terminal profile probing requires foreground stdin/stdout on the same TTY"
        raise TerminalQueryError(msg)

    def osc(request: bytes) -> bytes:
        return query_osc(request, owns_input=True, on_unmatched=on_unmatched, timeout=timeout)

    def csi(request: bytes) -> bytes:
        return query_csi(request, owns_input=True, on_unmatched=on_unmatched, timeout=timeout)

    def kitty(field: str) -> bytes:
        return query_kitty_field(field, owns_input=True, on_unmatched=on_unmatched, timeout=timeout)

    return probe_profile(color_query=osc, geometry_query=csi, kitty_query=kitty, palette=palette)


def probe_profile(
    *,
    geometry: Geometry | None = None,
    color_query: Callable[[bytes], bytes] | None = None,
    palette: bool = False,
    geometry_query: Callable[[bytes], bytes] | None = None,
    kitty_query: Callable[[str], bytes] | None = None,
) -> TerminalProfile:
    """Build a profile; only an explicitly supplied color callback may query.

    All query callbacks are supplied explicitly by an input owner.
    kitty_query accepts a Kitty XTGETTCAP field name and returns its raw DCS
    reply. Neither callback nor any terminal query is installed implicitly.
    """
    geom = geometry if geometry is not None else read_geometry()
    valid_geom = geom is not None and geom.rows > 0 and geom.columns > 0
    width, height, cell_width, cell_height = (
        _geometry_measurements(geom, geometry_query)
        if valid_geom and geom is not None
        else (Value(), Value(), Value(), Value())
    )
    kitty = _kitty_measurements(kitty_query)
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
    # Both are live observations; prefer standard OSC for portability.
    foreground = Value(fg, Source.MEASURED) if fg is not None else kitty.get("foreground", Value())
    background = Value(bg, Source.MEASURED) if bg is not None else kitty.get("background", Value())
    entries = tuple(colors.get(100 + i) for i in range(16))
    return TerminalProfile(
        rows=Value(geom.rows, Source.MEASURED) if valid_geom and geom is not None else Value(),
        columns=Value(geom.columns, Source.MEASURED) if valid_geom and geom is not None else Value(),
        width_px=width,
        height_px=height,
        cell_width_px=cell_width,
        cell_height_px=cell_height,
        foreground=foreground,
        background=background,
        ansi_palette=Value(entries, Source.MEASURED) if any(e is not None for e in entries) else Value(),
        font_family=kitty.get("font_family", Value()),
        font_size_pt=kitty.get("font_size", Value()),
        dpi_x=kitty.get("dpi_x", Value()),
        dpi_y=kitty.get("dpi_y", Value()),
        opacity=kitty.get("background_opacity", Value()),
    )


__all__ = [
    "Geometry",
    "Source",
    "TerminalProfile",
    "Value",
    "current_profile",
    "probe_owned_profile",
    "probe_profile",
    "read_geometry",
    "use_profile",
]
