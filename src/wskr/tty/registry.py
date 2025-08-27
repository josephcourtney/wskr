import importlib.metadata
import logging
import os
from dataclasses import dataclass
from enum import StrEnum

from wskr import config
from wskr.errors import TransportInitError, TransportUnavailableError
from wskr.tty.base import ImageTransport
from wskr.tty.base import ImageTransport as _Base

logger = logging.getLogger(__name__)


class TransportName(StrEnum):
    """Enumerated transport names to avoid typos."""

    KITTY = "kitty"
    KITTY_PY = "kitty_py"
    NOOP = "noop"


@dataclass
class _TransportEntry:
    cls: type[ImageTransport]
    enabled: bool = True


_IMAGE_TRANSPORTS: dict[str, _TransportEntry] = {}
_ENTRYPOINTS_LOADED = False


def register_image_transport(
    name: str | TransportName,
    cls: type[ImageTransport],
    *,
    enabled: bool = True,
) -> None:
    """Register an :class:`ImageTransport` implementation."""
    name_str = name.value if isinstance(name, TransportName) else name
    if not isinstance(name_str, str) or not name_str.strip():
        msg = f"Transport name must be a non-empty string, got {name!r}"
        raise ValueError(msg)

    if not isinstance(cls, type) or not issubclass(cls, _Base):
        msg = f"Transport class must subclass ImageTransport, got {cls!r}"
        raise TypeError(msg)

    _IMAGE_TRANSPORTS[name_str] = _TransportEntry(cls, enabled)


def _load_entry_points() -> None:
    global _ENTRYPOINTS_LOADED  # noqa: PLW0603
    if _ENTRYPOINTS_LOADED:
        return
    _ENTRYPOINTS_LOADED = True
    try:
        eps = importlib.metadata.entry_points(group="wskr.image_transports")
    except Exception as e:  # noqa: BLE001  pragma: no cover - defensive
        logger.debug("entry point loading failed: %s", e)
        return
    for ep in eps:
        try:
            cls = ep.load()
            register_image_transport(ep.name, cls)
        except Exception as e:  # noqa: BLE001  pragma: no cover - defensive
            logger.warning("Failed to load transport %s: %s", ep.name, e)


def get_image_transport(name: str | TransportName | None = None) -> ImageTransport:
    """Return an initialised transport instance.

    Raises :class:`TransportUnavailableError` for unknown or disabled
    transports and :class:`TransportInitError` if initialisation fails.
    """
    _load_entry_points()
    key = name.value if isinstance(name, TransportName) else name
    key = key or os.getenv("WSKR_TRANSPORT", TransportName.NOOP.value)

    try:
        entry = _IMAGE_TRANSPORTS[key]
    except KeyError:
        err: Exception = TransportUnavailableError(f"Unknown transport {key!r}")
    else:
        if not entry.enabled:
            err = TransportUnavailableError(f"Transport {key!r} is disabled")
        else:
            try:
                return entry.cls()
            except Exception as e:  # noqa: BLE001  pragma: no cover - guard
                err = TransportInitError(f"Transport {key!r} failed to initialise: {e}")

    policy = config.FALLBACK.lower()
    if policy == "noop":
        logger.warning("%s; falling back to NoOpTransport", err)
        return _IMAGE_TRANSPORTS[TransportName.NOOP.value].cls()
    raise err


__all__ = [
    "TransportName",
    "get_image_transport",
    "register_image_transport",
]
