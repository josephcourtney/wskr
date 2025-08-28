from wskr.tty.base import ImageTransport
from wskr.tty.registry import TransportName, register_image_transport

__all__ = ["NoOpTransport"]


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


register_image_transport(TransportName.NOOP, NoOpTransport)
