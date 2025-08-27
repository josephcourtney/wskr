from wskr.config import IMAGE_CHUNK_SIZE
from wskr.tty.base import ImageTransport
from wskr.tty.kitty import KittyTransport
from wskr.tty.kitty_parser import KittyChunkParser
from wskr.tty.registry import TransportName, register_image_transport

__all__ = ["KittyPyTransport", "NoOpTransport"]


class NoOpTransport(ImageTransport):
    __slots__ = ()

    def get_window_size_px(self) -> tuple[int, int]:  # noqa: PLR6301
        return (800, 600)

    def send_image(self, png_bytes: bytes) -> None:  # noqa: ARG002, PLR6301
        print("[wskr] Warning: No terminal image transport available")

    def init_image(self, png_bytes: bytes) -> int:  # noqa: ARG002, PLR6301
        print("[wskr] Warning: init_image() called on NoOpTransport")
        return -1

    def close(self) -> None:  # noqa: PLR6301
        return None


class KittyPyTransport(ImageTransport):
    """Experimental pure-Python Kitty transport."""

    __slots__ = ("_next_img",)

    def __init__(self) -> None:
        self._next_img = 1

    def get_window_size_px(self) -> tuple[int, int]:  # noqa: PLR6301
        return (800, 600)

    def send_image(self, png_bytes: bytes) -> None:
        self.init_image(png_bytes)

    def init_image(self, png_bytes: bytes) -> int:
        img_num = self._next_img
        self._next_img += 1
        for i in range(0, len(png_bytes), IMAGE_CHUNK_SIZE):
            KittyChunkParser.send_chunk(img_num, png_bytes[i : i + IMAGE_CHUNK_SIZE])
        KittyChunkParser.send_chunk(img_num, b"", final=True)
        return img_num


register_image_transport(TransportName.KITTY, KittyTransport)
register_image_transport(TransportName.KITTY_PY, KittyPyTransport)
register_image_transport(TransportName.NOOP, NoOpTransport)
