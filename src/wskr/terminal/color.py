"""Strict OSC color response parsing and perceptual luminance."""

from __future__ import annotations

import re
from dataclasses import dataclass

_COLOR = re.compile(
    rb"^\x1b\](4|10|11);(?:(\d{1,2});)?rgb:"
    rb"([0-9a-fA-F]{1,4})/([0-9a-fA-F]{1,4})/([0-9a-fA-F]{1,4})"
    rb"(?:\x07|\x1b\\)$"
)


@dataclass(frozen=True, slots=True)
class RGB:
    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        if any(not 0 <= v <= 255 for v in (self.red, self.green, self.blue)):
            msg = "RGB channels must be in [0, 255]"
            raise ValueError(msg)

    @property
    def luminance(self) -> float:
        def linear(channel: int) -> float:
            value = channel / 255
            return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

        return 0.2126 * linear(self.red) + 0.7152 * linear(self.green) + 0.0722 * linear(self.blue)

    @property
    def is_dark(self) -> bool:
        return self.luminance < 0.179

    def to_hex(self) -> str:
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"


def parse_osc_color(data: bytes, code: int, index: int | None = None) -> RGB:
    """Accept a complete, correctly identified OSC 4/10/11 response.

    Kitty and other terminals can send BEL or ST terminators, and one-, two-,
    three-, or four-digit RGB channels. They are scaled by channel bit depth.
    """
    if len(data) > 128:
        msg = "Oversized OSC color reply"
        raise ValueError(msg)
    match = _COLOR.fullmatch(data)
    if match is None:
        msg = "Unexpected OSC color response"
        raise ValueError(msg)
    received_code, received_index, *channels = match.groups()
    if int(received_code) != code:
        msg = "Unexpected OSC color selector"
        raise ValueError(msg)
    if (int(received_index) if received_index is not None else None) != index:
        msg = "Unexpected OSC palette index"
        raise ValueError(msg)
    rgb = tuple(round(int(channel, 16) * 255 / (16 ** len(channel) - 1)) for channel in channels)
    return RGB(*rgb)


__all__ = ["RGB", "parse_osc_color"]
