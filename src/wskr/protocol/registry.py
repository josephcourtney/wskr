from __future__ import annotations

import importlib.metadata
import logging
import os
from dataclasses import dataclass

from wskr.core.errors import TransportInitError, TransportUnavailableError

from .base import ImageProtocol

logger = logging.getLogger(__name__)


@dataclass
class _ProtocolEntry:
    cls: type[ImageProtocol]
    enabled: bool = True


_IMAGE_PROTOCOLS: dict[str, _ProtocolEntry] = {}
_ENTRYPOINTS_LOADED = False


def register_image_protocol(name: str, cls: type[ImageProtocol], *, enabled: bool = True) -> None:
    """Register an :class:`ImageProtocol` implementation under ``name``.

    This API mirrors the existing transport registry but lives under the
    protocol layer to decouple protocol selection from terminal detection.
    """
    if not isinstance(name, str) or not name.strip():
        msg = f"Protocol name must be a non-empty string, got {name!r}"
        raise ValueError(msg)
    if not isinstance(cls, type) or not issubclass(cls, ImageProtocol):
        msg = f"Protocol class must subclass ImageProtocol, got {cls!r}"
        raise TypeError(msg)
    _IMAGE_PROTOCOLS[name] = _ProtocolEntry(cls, enabled)


def _load_entry_points() -> None:
    global _ENTRYPOINTS_LOADED  # noqa: PLW0603
    if _ENTRYPOINTS_LOADED:
        return
    _ENTRYPOINTS_LOADED = True
    try:
        eps = importlib.metadata.entry_points(group="wskr.image_protocols")
    except Exception:  # noqa: BLE001 - defensive guard
        logger.debug("protocol entry point discovery failed", exc_info=True)
        return
    for ep in eps:
        try:
            cls = ep.load()
            register_image_protocol(ep.name, cls)
        except Exception:  # noqa: BLE001 - defensive guard
            logger.warning("failed to load protocol %s", ep.name, exc_info=True)


def load_entry_points() -> None:
    """Public wrapper to load ``wskr.image_protocols`` entry points."""
    _load_entry_points()


def _ensure_builtin_protocols() -> None:
    # Ensure `noop` exists for safe defaults
    if "noop" not in _IMAGE_PROTOCOLS:
        try:  # pragma: no cover - tiny import guard
            from .noop import NoOpProtocol  # noqa: PLC0415

            register_image_protocol("noop", NoOpProtocol)
        except Exception:  # noqa: BLE001 - defensive guard
            logger.debug("failed to auto-register NoOpProtocol", exc_info=True)


def get_image_protocol(name: str | None = None) -> ImageProtocol:
    """Return an initialised protocol instance.

    Resolution order: explicit ``name`` → ``$WSKR_PROTOCOL`` → ``"noop"``.
    Raises :class:`TransportUnavailableError` for unknown/disabled protocols and
    :class:`TransportInitError` if initialisation fails.
    """
    _ensure_builtin_protocols()
    _load_entry_points()
    key = name or os.getenv("WSKR_PROTOCOL", "noop")
    logger.debug("get_image_protocol: requested=%r", key)

    try:
        entry = _IMAGE_PROTOCOLS[key]
    except KeyError:
        err: Exception = TransportUnavailableError(f"Unknown protocol {key!r}")
    else:
        if not entry.enabled:
            err = TransportUnavailableError(f"Protocol {key!r} is disabled")
        else:
            try:
                return entry.cls()
            except Exception as e:  # noqa: BLE001 - defensive guard
                err = TransportInitError(f"Protocol {key!r} failed to initialise: {e}")
    # Fallback to noop if available
    if "noop" in _IMAGE_PROTOCOLS:
        logger.warning("%s; falling back to NoOpProtocol", err)
        return _IMAGE_PROTOCOLS["noop"].cls()
    raise err


__all__ = [
    "get_image_protocol",
    "load_entry_points",
    "register_image_protocol",
]
