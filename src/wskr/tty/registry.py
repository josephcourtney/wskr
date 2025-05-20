import logging
import os

from wskr.tty.base import ImageTransport
from wskr.tty.base import ImageTransport as _Base

logger = logging.getLogger(__name__)

_IMAGE_TRANSPORTS: dict[str, type[ImageTransport]] = {}


def register_image_transport(name: str, cls: type[ImageTransport]) -> None:
    # Name must be a non-empty string
    if not isinstance(name, str) or not name.strip():
        msg = f"Transport name must be a non-empty string, got {name!r}"
        raise ValueError(msg)
    # cls must be a subclass of ImageTransport

    if not isinstance(cls, type) or not issubclass(cls, _Base):
        msg = f"Transport class must subclass ImageTransport, got {cls!r}"
        raise TypeError(msg)

    _IMAGE_TRANSPORTS[name] = cls


def get_image_transport(name: str | None = None) -> ImageTransport:
    key = name or os.getenv("WSKR_TRANSPORT", "noop")
    try:
        return _IMAGE_TRANSPORTS[key]()
    except KeyError:
        logger.warning("Unknown transport %r, using fallback NoOpTransport", key)
    except (TypeError, ValueError, RuntimeError) as e:
        logger.warning("Transport %r failed: %s. Falling back to NoOpTransport.", key, e)
    return _IMAGE_TRANSPORTS["noop"]()
