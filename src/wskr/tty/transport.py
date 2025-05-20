from wskr.tty.base import ImageTransport
from wskr.tty.kitty import KittyTransport
from wskr.tty.registry import register_image_transport

__all__ = ["NoOpTransport"]


class NoOpTransport(ImageTransport):
    def get_window_size_px(self) -> tuple[int, int]:  # noqa: PLR6301
        return (800, 600)

    def send_image(self, png_bytes: bytes) -> None:  # noqa: ARG002, PLR6301
        print("[wskr] Warning: No terminal image transport available")

    def init_image(self, png_bytes: bytes) -> int:  # noqa: ARG002, PLR6301
        print("[wskr] Warning: init_image() called on NoOpTransport")
        return -1


register_image_transport("kitty", KittyTransport)
register_image_transport("noop", NoOpTransport)
