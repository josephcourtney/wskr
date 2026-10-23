"""Managed direct Kitty graphics transport shared by Matplotlib and future Rich.

Image data, physical placements, virtual placements and disposal have separate
operations. The Rich adapter must not claim support for placeholders until
its layout protocol is implemented in Phase 4.
"""

from __future__ import annotations

import base64
import math
import os
import secrets
import sys
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image

from wskr.core.errors import TransportRuntimeError, TransportUnavailableError
from wskr.protocol.base import ImageProtocol
from wskr.protocol.kitty_codec import MAX_ID, delete, placement, probe_request, transmit
from wskr.protocol.kitty_io import query_support, send_frames
from wskr.protocol.kitty_placeholders import MAX_VIRTUAL_PLACEMENT_ID
from wskr.terminal.profile import read_geometry

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

type WriteFrames = Callable[[Iterable[bytes]], None]

# Transparent 1x1 RGBA PNG used as an invisible physical placement anchor.
_ANCHOR_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg=="
)


def _placement_cells(png: bytes) -> tuple[int, int] | None:
    """Measure figure cell footprint; never invent pixel or terminal geometry."""
    geometry = read_geometry()
    if geometry is None or min(geometry.width_px, geometry.height_px, geometry.rows, geometry.columns) <= 0:
        return None
    with Image.open(BytesIO(png)) as source:
        width, height = source.size
    columns = max(1, min(geometry.columns, math.ceil(width * geometry.columns / geometry.width_px)))
    rows = max(1, min(geometry.rows, math.ceil(height * geometry.rows / geometry.height_px)))
    return columns, rows


class KittyImageManager:
    """Own uploaded images and their individually addressable placements."""

    def __init__(self, writer: WriteFrames) -> None:
        self._writer = writer
        self._images: dict[int, set[int]] = {}
        self._closed = False

    def _ensure_open(self) -> None:
        if self._closed:
            msg = "Kitty image manager has been closed"
            raise TransportRuntimeError(msg)

    @staticmethod
    def _id(occupied: set[int], *, limit: int = MAX_ID) -> int:
        for _ in range(64):
            candidate = secrets.randbelow(limit) + 1
            if candidate not in occupied:
                return candidate
        msg = "Unable to allocate a fresh Kitty graphics identifier"
        raise TransportRuntimeError(msg)

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

    def reserve_anchor(self, *, columns: int, rows: int) -> tuple[int, int]:
        """Reserve a normal cursor-advancing rectangle with invisible pixels."""
        self._ensure_open()
        image_id = self._id(set(self._images))
        placement_id = self._id(set())
        self._writer(
            transmit(
                _ANCHOR_PNG,
                image_id,
                display=True,
                placement_id=placement_id,
                columns=columns,
                rows=rows,
            )
        )
        self._images[image_id] = {placement_id}
        return image_id, placement_id

    def place(
        self,
        image_id: int,
        *,
        columns: int | None = None,
        rows: int | None = None,
        placement_id: int | None = None,
        virtual: bool = False,
        parent: tuple[int, int] | None = None,
    ) -> int:
        """Create or replace a placement; virtual placements are Rich-ready."""
        self._ensure_open()
        if image_id not in self._images:
            msg = "Image is not owned by this Kitty manager"
            raise TransportRuntimeError(msg)
        occupied = self._images[image_id]
        if virtual and placement_id is not None and not 1 <= placement_id <= MAX_VIRTUAL_PLACEMENT_ID:
            msg = "Virtual placement IDs must fit into a 24-bit underline color"
            raise ValueError(msg)
        limit = MAX_VIRTUAL_PLACEMENT_ID if virtual else MAX_ID
        pid = placement_id if placement_id is not None else self._id(occupied, limit=limit)
        self._writer((placement(image_id, pid, columns, rows, virtual=virtual, parent=parent),))
        occupied.add(pid)
        return pid

    def remove_placement(self, image_id: int, placement_id: int) -> None:
        """Delete one owned placement without invalidating the image upload."""
        self._ensure_open()
        if placement_id not in self._images.get(image_id, set()):
            msg = "Placement is not owned by this Kitty manager"
            raise TransportRuntimeError(msg)
        self._writer((delete(image_id, placement_id=placement_id),))
        self._images[image_id].remove(placement_id)

    def relinquish_image(self, image_id: int) -> None:
        """Keep a displayed image in Kitty without deleting it.

        The manager stops owning this identifier. It must only be used for a
        static final display that should remain part of terminal history.
        """
        self._ensure_open()
        if image_id not in self._images:
            msg = "Image is not owned by this Kitty manager"
            raise TransportRuntimeError(msg)
        del self._images[image_id]

    def remove_image(self, image_id: int) -> None:
        """Free only the image and placements owned by this manager."""
        self._ensure_open()
        if image_id not in self._images:
            msg = "Image is not owned by this Kitty manager"
            raise TransportRuntimeError(msg)
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
                msg = "Native Kitty graphics requires a foreground TTY"
                raise TransportUnavailableError(msg)
            if os.getenv("TERM") != "xterm-kitty":
                msg = "Native Kitty graphics requires direct xterm-kitty terminal access"
                raise TransportUnavailableError(msg)
        self.manager = KittyImageManager(writer or send_frames)
        self._display_image_id: int | None = None
        self._anchor: tuple[int, int] | None = None
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

    def get_window_size_px(self) -> tuple[int, int]:  # ruff: ignore[no-self-use] - ImageProtocol instance method
        """Return measured terminal pixels rather than fabricated monitor DPI."""
        geometry = read_geometry()
        if geometry is None or geometry.width_px <= 0 or geometry.height_px <= 0:
            msg = "Terminal pixel dimensions are not available"
            raise TransportUnavailableError(msg)
        return geometry.width_px, geometry.height_px

    def send_image(self, png_bytes: bytes) -> None:
        """Replace this transport's previous display without leaking images.

        A fresh upload is shown before the prior image is deleted, preserving
        the most recent result if a transmission fails.
        """
        image_id = self.manager.display(png_bytes)
        previous = self._display_image_id
        self._display_image_id = image_id
        if previous is not None:
            self.manager.remove_image(previous)
        if self._anchor is not None:
            self.manager.remove_image(self._anchor[0])
            self._anchor = None

    def send_anchored_image(self, png_bytes: bytes) -> None:
        """Replace a fitted figure relative to its original terminal placement.

        The first, transparent parent reserves exactly one normal image region
        and advances the terminal cursor. Later children are relative to that
        parent and never follow the moved shell/REPL cursor. This uses Kitty's
        P/Q relative-placement semantics, not terminal cursor addressing.
        """
        cells = _placement_cells(png_bytes)
        if cells is None:
            self.send_image(png_bytes)  # No invented geometry or anchor.
            return
        new_anchor = self._anchor is None
        if new_anchor:
            self._anchor = self.manager.reserve_anchor(columns=cells[0], rows=cells[1])
        image_id: int | None = None
        try:
            image_id = self.manager.upload(png_bytes)
            self.manager.place(image_id, parent=self._anchor)
        except BaseException:
            if image_id is not None:
                self.manager.remove_image(image_id)
            if new_anchor and self._anchor is not None:
                self.manager.remove_image(self._anchor[0])
                self._anchor = None
            raise
        previous = self._display_image_id
        self._display_image_id = image_id
        if previous is not None:
            self.manager.remove_image(previous)

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

    def retain_display(self) -> None:
        """Leave only the final one-off display visible after process exit."""
        if self._display_image_id is not None:
            self.manager.relinquish_image(self._display_image_id)
            self._display_image_id = None
            if self._anchor is not None:
                self.manager.relinquish_image(self._anchor[0])
                self._anchor = None

    def close(self) -> None:
        """Delete still-managed images; retained terminal history survives."""
        self.manager.close()
        self._display_image_id = None
        self._anchor = None


__all__ = ["KittyImageManager", "NativeKittyTransport"]
