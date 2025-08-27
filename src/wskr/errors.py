"""Custom exceptions for ``wskr``."""

from __future__ import annotations


class FeatureUnavailableError(RuntimeError):
    """Raised when an optional feature is not available."""


class TransportError(RuntimeError):
    """Base class for transport-related errors."""


class TransportUnavailableError(TransportError):
    """Raised when a transport is unknown or disabled."""


class TransportInitError(TransportError):
    """Raised when a transport fails to initialise."""
