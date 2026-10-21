"""Managed direct Kitty graphics transport shared by Matplotlib and future Rich.

Image data, physical placements, virtual placements and disposal have separate
operations. The Rich adapter must not claim support for placeholders until
its layout protocol is implemented in Phase 4.
"""

from __future__ import annotations

import os
import secrets
import sys
from typing import TYPE_CHECKING

from wskr.core.errors import TransportRuntimeError, TransportUnavailableError
from wskr.protocol.base import ImageProtocol
from wskr.protocol.kitty_codec import MAX_ID, delete, placement, probe_request, transmit
from wskr.protocol.kitty_placeholders import MAX_VIRTUAL_PLACEMENT_ID
from wskr.protocol.kitty_io import query_support, send_frames
from wskr.terminal.profile import read_geometry

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

type WriteFrames = Callable[[Iterable[bytes]], None]


class KittyImageManager:
    """Own uploaded images and their individually addressable placements."""

    def __init__(self, writer: WriteFrames) -> None:
        self._writer = writer
        self._images: dict[int, set[int]] = {}
        self._closed = False

    def _ensure_open(self) -> None:
        if self._closed:
            raise TransportRuntimeError("Kitty image manager has been closed")

    def _id(self, occupied: set[int], *, limit: int = MAX_ID) -> int:
        for _ in range(64):
            candidate = secrets.randbelow(limit) + 1
            if candidate not in occupied:
                return candidate
        raise TransportRuntimeError("Unable to allocate a fresh Kitty graphics identifier")

    def upload(self, png: bytes) -> int:
        """Upload PNG data without creating a visible placement."""
        self._ensure_open()
        image_id = self._id(set(self._images))
        self._writer(transmit(png, image_id))
        self._images[image_id] = set()
        return image_id

    def display(self, png: bytes) -> int:
        """Transmit and display a PNG in one atomic transfer transaction."""
        self._ensure_open()
        image_id = self._id(set(self._images))
        placement_id = self._id(set())
        self._writer(transmit(png, image_id, display=True, placement_id=placement_id))
        self._images[image_id] = {placement_id}
        return image_id

    def place(
        self,
        image_id: int,
        *,
        columns: int,
        rows: int,
        placement_id: int | None = None,
        virtual: bool = False,
    ) -> int:
        """Create or replace a placement; virtual placements are Rich-ready."""
        self._ensure_open()
        if image_id not in self._images:
            raise TransportRuntimeError("Image is not owned by this Kitty manager")
        occupied = self._images[image_id]
        if virtual and placement_id is not None and not 1 <= placement_id <= MAX_VIRTUAL_PLACEMENT_ID:
            raise ValueError("Virtual placement IDs must fit into a 24-bit underline color")
        limit = MAX_VIRTUAL_PLACEMENT_ID if virtual else MAX_ID
        pid = placement_id if placement_id is not None else self._id(occupied, limit=limit)
        self._writer((placement(image_id, pid, columns, rows, virtual=virtual),))
        occupied.add(pid)
        return pid

    def remove_placement(self, image_id: int, placement_id: int) -> None:
        """Delete one owned placement without invalidating the image upload."""
        self._ensure_open()
        if placement_id not in self._images.get(image_id, set()):
            raise TransportRuntimeError("Placement is not owned by this Kitty manager")
        self._writer((delete(image_id, placement_id=placement_id),))
        self._images[image_id].remove(placement_id)

    def remove_image(self, image_id: int) -> None:
        """Free only the image and placements owned by this manager."""
        self._ensure_open()
        if image_id not in self._images:
            raise TransportRuntimeError("Image is not owned by this Kitty manager")
        self._writer((delete(image_id, free=True),))
        del self._images[image_id]

    def close(self) -> None:
        """Release all owned uploads; never issue a global-screen delete."""
        if self._closed:
            return
        for image_id in tuple(self._images):
            self.remove_image(image_id)
        self._closed = True


class NativeKittyTransport(ImageProtocol):
    """PNG graphics backend using direct Kitty framing, without icat.

    Explicit selection under TERM=xterm-kitty is an environment *hint*, not a
    negotiated guarantee. A caller with exclusive input ownership can call
    probe() to confirm support. All normal uploads are quiet to protect REPL
    input; unsupported graphics must be reported through explicit probing or
    real-terminal visual qualification, not guessed from a successful write.
    """

    supports_inline_placement = False
    supports_virtual_placement = True

    def __init__(self, writer: WriteFrames | None = None) -> None:
        if writer is None:
            if sys.stdout is None or not sys.stdout.isatty():
                raise TransportUnavailableError("Native Kitty graphics requires a foreground TTY")
            if os.getenv("TERM") != "xterm-kitty":
                raise TransportUnavailableError("Native Kitty graphics requires direct xterm-kitty terminal access")
        self.manager = KittyImageManager(writer or send_frames)
        self.confirmed: bool | None = None

    def probe(
        self,
        *,
        owns_input: bool = False,
        on_unmatched: Callable[[bytes], None] | None = None,
        timeout: float = 0.35,
    ) -> bool:
        """Confirm graphics support through an isolated one-pixel Kitty query."""
        image_id = secrets.randbelow(MAX_ID) + 1
        self.confirmed = query_support(
            probe_request(image_id),
            expected_id=image_id,
            owns_input=owns_input,
            on_unmatched=on_unmatched,
            timeout=timeout,
        )
        return self.confirmed

    def get_window_size_px(self) -> tuple[int, int]:
        """Return measured terminal pixels rather than fabricated monitor DPI."""
        geometry = read_geometry()
        if geometry is None or geometry.width_px <= 0 or geometry.height_px <= 0:
            raise TransportUnavailableError("Terminal pixel dimensions are not available")
        return geometry.width_px, geometry.height_px

    def send_image(self, png_bytes: bytes) -> None:
        """Display one image; do not preempt an unrelated Kitty placement."""
        self.manager.display(png_bytes)

    def init_image(self, png_bytes: bytes) -> int:
        """Upload image without placing; retained for ImageProtocol compatibility."""
        return self.manager.upload(png_bytes)

    def place_image(
        self,
        image_id: int,
        *,
        columns: int,
        rows: int,
        placement_id: int | None = None,
        virtual: bool = False,
    ) -> int:
        """Create a scoped physical or virtual placement of an uploaded image."""
        return self.manager.place(image_id, columns=columns, rows=rows, placement_id=placement_id, virtual=virtual)

    def delete_image(self, image_id: int) -> None:
        """Delete only this transport's owned image and its placements."""
        self.manager.remove_image(image_id)

    def close(self) -> None:
        """Release all images uploaded by this transport instance."""
        self.manager.close()


__all__ = ["KittyImageManager", "NativeKittyTransport"]
