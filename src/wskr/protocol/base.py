from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from types import TracebackType


class ImageProtocol(ABC):
    """Abstract interface for any terminal graphics protocol.

    Mirrors the existing ``ImageTransport`` API to enable a non-breaking
    migration. Implementations may be adapted from current transports.
    """

    @abstractmethod
    def get_window_size_px(self) -> tuple[int, int]:
        """Return ``(width_px, height_px)`` of the drawable viewport."""
        ...

    @abstractmethod
    def send_image(self, png_bytes: bytes) -> None:
        """Display the given PNG image (one-off)."""
        ...

    @abstractmethod
    def init_image(self, png_bytes: bytes) -> int:
        """Upload a PNG once and return its assigned image ID.

        Subsequent renders may use that ID for faster updates.
        """
        ...

    def close(self) -> None:  # noqa: B027
        """Release any acquired resources (optional)."""

    def __enter__(self) -> Self:
        """Return ``self`` for context manager usage."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        """Run :meth:`close` when leaving a context manager block."""
        self.close()
        return False


__all__ = ["ImageProtocol"]
