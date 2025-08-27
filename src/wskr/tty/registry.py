import logging
import os
from enum import StrEnum

from wskr.tty.base import ImageTransport
from wskr.tty.base import ImageTransport as _Base

logger = logging.getLogger(__name__)


class TransportName(StrEnum):
    """Enumerated transport names to avoid typos."""

    KITTY = "kitty"
    NOOP = "noop"


_IMAGE_TRANSPORTS: dict[str, type[ImageTransport]] = {}


def register_image_transport(name: str | TransportName, cls: type[ImageTransport]) -> None:
    # Name must be a non-empty string
    name_str = name.value if isinstance(name, TransportName) else name
    if not isinstance(name_str, str) or not name_str.strip():
        msg = f"Transport name must be a non-empty string, got {name!r}"
        raise ValueError(msg)
    # cls must be a subclass of ImageTransport

    if not isinstance(cls, type) or not issubclass(cls, _Base):
        msg = f"Transport class must subclass ImageTransport, got {cls!r}"
        raise TypeError(msg)

    _IMAGE_TRANSPORTS[name_str] = cls


def get_image_transport(name: str | TransportName | None = None) -> ImageTransport:
    key = name.value if isinstance(name, TransportName) else name
    key = key or os.getenv("WSKR_TRANSPORT", TransportName.NOOP.value)
    try:
        return _IMAGE_TRANSPORTS[key]()
    except KeyError:
        logger.warning("Unknown transport %r, using fallback NoOpTransport", key)
    except (TypeError, ValueError, RuntimeError) as e:
        logger.warning("Transport %r failed: %s. Falling back to NoOpTransport.", key, e)
    return _IMAGE_TRANSPORTS[TransportName.NOOP.value]()


__all__ = ["TransportName", "get_image_transport", "register_image_transport"]
