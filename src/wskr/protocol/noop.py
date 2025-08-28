from __future__ import annotations

from .base import ImageProtocol

__all__ = ["NoOpProtocol"]


class NoOpProtocol(ImageProtocol):
    __slots__ = ()

    def get_window_size_px(self) -> tuple[int, int]:  # noqa: PLR6301
        return (800, 600)

    def send_image(self, png_bytes: bytes) -> None:  # noqa: ARG002, PLR6301
        print("[wskr] Warning: No image protocol available (noop)")

    def init_image(self, png_bytes: bytes) -> int:  # noqa: ARG002, PLR6301
        print("[wskr] Warning: init_image() called on NoOpProtocol")
        return -1

    def close(self) -> None:  # noqa: PLR6301
        return None
