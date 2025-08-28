import logging
import shutil
import sys
import time

from wskr.core.config import CACHE_TTL_S, DEFAULT_TTY_ROWS, IMAGE_CHUNK_SIZE, TIMEOUT_S
from wskr.core.errors import CommandRunnerError, TransportUnavailableError
from wskr.protocol.kgp.parser import KittyChunkParser
from wskr.terminal.core.base import ImageTransport
from wskr.terminal.core.command import CommandRunner
from wskr.terminal.core.registry import TransportName, register_image_transport
from wskr.terminal.core.ttyools import query_tty

logger = logging.getLogger(__name__)


class KittyTransport(ImageTransport):
    __slots__ = ("_cache_time", "_cached_size", "_kitty", "_next_img", "_runner")

    def __init__(self) -> None:
        self._kitty = shutil.which("kitty")
        if not self._kitty:
            msg = "[wskr] Kitty transport not available: 'kitty' binary not found."
            raise TransportUnavailableError(msg)
        logger.debug("KittyTransport.__init__: kitty=%s timeout=%s", self._kitty, TIMEOUT_S)
        self._next_img = 1
        self._cached_size: tuple[int, int] | None = None
        self._cache_time = 0.0
        self._runner = CommandRunner(timeout=TIMEOUT_S)

    def invalidate_cache(self) -> None:
        """Drop any cached window-size information."""
        self._cached_size = None
        self._cache_time = 0.0

    def get_window_size_px(self) -> tuple[int, int]:
        logger.debug(
            "KittyTransport.get_window_size_px: cached_size=%r age=%.2f",
            self._cached_size,
            time.time() - self._cache_time,
        )
        if self._cached_size is not None and (time.time() - self._cache_time) < CACHE_TTL_S:
            return self._cached_size
        try:
            proc = self._runner.run(
                [self._kitty, "+kitten", "icat", "--print-window-size"],
                capture_output=True,
                text=True,
                check=True,
            )
            w_px, h_px = map(int, proc.stdout.strip().split("x"))
        except (CommandRunnerError, ValueError):
            logger.warning("KittyTransport.get_window_size_px failed", exc_info=True)
            size = (800, 600)
            logger.debug("KittyTransport.get_window_size_px: using fallback size=%r", size)
        else:
            # terminals are typically 24 rows tall
            rows = DEFAULT_TTY_ROWS
            size = (w_px, h_px - (3 * h_px) // rows)
        self._cached_size = size
        self._cache_time = time.time()
        logger.debug("KittyTransport.get_window_size_px: computed_size=%r", size)
        return size

    @staticmethod
    def _tput_lines() -> int:
        tput = shutil.which("tput")
        if not tput:
            logger.debug("KittyTransport._tput_lines: tput not found, defaulting to 24")
            return 24
        try:
            proc = CommandRunner().run(
                [tput, "lines"],
                capture_output=True,
                text=True,
                check=True,
            )
            out = proc.stdout.strip()
            try:
                return int(out or "24")
            except ValueError:
                logger.warning("KittyTransport._tput_lines parse failed: %r", out, exc_info=True)
                return 24
        except CommandRunnerError:
            logger.warning("KittyTransport._tput_lines failed", exc_info=True)
            return 24

    def send_image(self, png_bytes: bytes) -> None:
        logger.debug(
            "KittyTransport.send_image: kitty=%s timeout=%s bytes=%d",
            self._kitty,
            self._runner.timeout,
            len(png_bytes),
        )
        try:
            self._runner.run(
                [self._kitty, "+kitten", "icat", "--align", "center"],
                input=png_bytes,
                stdout=sys.stderr,
                check=True,
            )
        except CommandRunnerError:
            logger.exception("Error sending image via kitty icat")

    def init_image(self, png_bytes: bytes) -> int:
        img_num = self._next_img
        self._next_img += 1

        logger.debug("KittyTransport.init_image: img=%d bytes=%d", img_num, len(png_bytes))

        for i in range(0, len(png_bytes), IMAGE_CHUNK_SIZE):
            KittyChunkParser.send_chunk(img_num, png_bytes[i : i + IMAGE_CHUNK_SIZE])
        KittyChunkParser.send_chunk(img_num, b"", final=True)

        resp = query_tty(
            f"\x1b_Ga=t,q=0,f=32,i={img_num},m=0;\x1b\\".encode(),
            more=lambda b: not b.endswith(b"\x1b\\"),
            timeout=TIMEOUT_S,
        )
        return KittyChunkParser.parse_init_response(img_num, resp)

    def close(self) -> None:
        """Clear any cached data."""
        self.invalidate_cache()


class KittyPyTransport(ImageTransport):
    """Experimental pure-Python Kitty transport."""

    __slots__ = ("_next_img",)

    def __init__(self) -> None:
        self._next_img = 1

    def get_window_size_px(self) -> tuple[int, int]:  # noqa: PLR6301
        return (800, 600)

    def send_image(self, png_bytes: bytes) -> None:
        self.init_image(png_bytes)

    def init_image(self, png_bytes: bytes) -> int:
        img_num = self._next_img
        self._next_img += 1
        for i in range(0, len(png_bytes), IMAGE_CHUNK_SIZE):
            KittyChunkParser.send_chunk(img_num, png_bytes[i : i + IMAGE_CHUNK_SIZE])
        KittyChunkParser.send_chunk(img_num, b"", final=True)
        return img_num


register_image_transport(TransportName.KITTY, KittyTransport)
register_image_transport(TransportName.KITTY_PY, KittyPyTransport)


__all__ = ["KittyTransport"]
