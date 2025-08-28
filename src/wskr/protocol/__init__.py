"""Graphics protocols (kitty, sixel, …)."""

from .base import ImageProtocol
from .registry import get_image_protocol, load_entry_points, register_image_protocol

__all__ = [
    "ImageProtocol",
    "get_image_protocol",
    "load_entry_points",
    "register_image_protocol",
]
