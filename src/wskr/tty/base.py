from abc import ABC, abstractmethod
from types import TracebackType


class ImageTransport(ABC):
    """Abstract interface for any terminal-graphics protocol."""

    @abstractmethod
    def get_window_size_px(self) -> tuple[int, int]:
        """Return (width_px, height_px) of terminal's image viewport."""
        ...

    @abstractmethod
    def send_image(self, png_bytes: bytes) -> None:
        """Display the given PNG image (one-off)."""
        ...

    @abstractmethod
    def init_image(self, png_bytes: bytes) -> int:
        """Upload a PNG once and return its kitty-assigned image ID.

        Subsequent renders use that ID.
        """
        ...

    def close(self) -> None:  # noqa: B027
        """Release any acquired resources."""

    def __enter__(self) -> "ImageTransport":
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
