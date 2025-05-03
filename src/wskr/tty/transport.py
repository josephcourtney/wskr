import os
import sys

from wskr.tty.base import ImageTransport
from wskr.tty.kitty import KittyTransport

__all__ = ["get_image_transport", "register_image_transport"]

# registry of name → ImageTransport class
_IMAGE_TRANSPORTS: dict[str, type[ImageTransport]] = {}


def register_image_transport(name: str, cls: type[ImageTransport]) -> None:
    """
    Register a new tty image transport under `name`.

    e.g. register_image_transport("sixel", SixelTransport).
    """
    _IMAGE_TRANSPORTS[name] = cls


register_image_transport("kitty", KittyTransport)


class NoOpTransport(ImageTransport):
    """Fallback transport that logs a warning but does nothing."""

    def get_window_size_px(self) -> tuple[int, int]:  # noqa: PLR6301
        return (800, 600)  # default dimensions

    def send_image(self, png_bytes: bytes) -> None:  # noqa: ARG002, PLR6301
        print("[wskr] Warning: No terminal image transport available", file=sys.stderr)

    def init_image(self, png_bytes: bytes) -> int:  # noqa: ARG002, PLR6301
        print("[wskr] Warning: init_image() called on NoOpTransport", file=sys.stderr)
        return -1


register_image_transport("noop", NoOpTransport)


def get_image_transport(name: str | None = None) -> ImageTransport:
    """Instantiate an ImageTransport by name.

    Falls back to WSKR_TRANSPORT env var or "kitty".
    """
    key = name or os.getenv("WSKR_TRANSPORT", "kitty")
    try:
        cls = _IMAGE_TRANSPORTS[key]
        return cls()
    except KeyError:
        print(f"[wskr] Unknown transport '{key}', using fallback (noop)", file=sys.stderr)
        return _IMAGE_TRANSPORTS["noop"]()
    except (TypeError, ValueError, RuntimeError) as e:
        print(f"[wskr] Transport '{key}' failed: {e}. Falling back to NoOpTransport.", file=sys.stderr)
        return _IMAGE_TRANSPORTS["noop"]()
