import logging
import re
import shutil
import subprocess  # noqa: S404
import sys
import time

from wskr.config import CACHE_TTL_S, DEFAULT_TTY_ROWS, IMAGE_CHUNK_SIZE
from wskr.ttyools import query_tty

from .base import ImageTransport

logger = logging.getLogger(__name__)


class KittyTransport(ImageTransport):
    __slots__ = ("_cache_time", "_cached_size", "_kitty", "_next_img")

    def __init__(self) -> None:
        self._kitty = shutil.which("kitty")
        if not self._kitty:
            msg = "[wskr] Kitty transport not available: 'kitty' binary not found."
            raise RuntimeError(msg)
        self._next_img = 1
        self._cached_size: tuple[int, int] | None = None
        self._cache_time = 0.0

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
            proc = subprocess.run(  # noqa: S603
                [self._kitty, "+kitten", "icat", "--print-window-size"],
                capture_output=True,
                text=True,
                check=True,
                timeout=1.0,
            )
            w_px, h_px = map(int, proc.stdout.strip().split("x"))
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.warning("KittyTransport.get_window_size_px failed: %s", e)
            size = (800, 600)
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
            return 24
        try:
            proc = subprocess.run(  # noqa: S603
                [tput, "lines"],
                capture_output=True,
                text=True,
                check=True,
            )
            out = proc.stdout.strip()
            try:
                return int(out or "24")
            except ValueError:
                logger.warning("KittyTransport._tput_lines parse failed: %r", out)
                return 24
        except subprocess.CalledProcessError as e:
            logger.warning("KittyTransport._tput_lines failed: %s", e)
            return 24

    def send_image(self, png_bytes: bytes) -> None:
        try:
            subprocess.run(  # noqa: S603
                [self._kitty, "+kitten", "icat", "--align", "center"],
                input=png_bytes,
                stdout=sys.stderr,
                check=True,
                timeout=1.0,
            )
        except subprocess.CalledProcessError:
            logger.exception("Error sending image via kitty icat")

    @staticmethod
    def _send_chunk(img_num: int, chunk: bytes, *, final: bool = False) -> None:
        m_flag = "0" if final else "1"
        logger.debug(
            "KittyTransport._send_chunk: img=%d, bytes=%d, final=%s",
            img_num,
            len(chunk),
            final,
        )
        header = f"\x1b_Ga=t,q=0,f=32,i={img_num},m={m_flag};"
        sys.stdout.buffer.write(header.encode("ascii") + chunk + b"\x1b\\")
        sys.stdout.flush()

    def init_image(self, png_bytes: bytes) -> int:
        img_num = self._next_img
        self._next_img += 1

        for i in range(0, len(png_bytes), IMAGE_CHUNK_SIZE):
            self._send_chunk(img_num, png_bytes[i : i + IMAGE_CHUNK_SIZE])
        self._send_chunk(img_num, b"", final=True)

        resp = query_tty(
            f"\x1b_Ga=t,q=0,f=32,i={img_num},m=0;\x1b\\".encode(),
            more=lambda b: not b.endswith(b"\x1b\\"),
            timeout=1.0,
        )
        if not resp:
            msg = "No response from kitty on image init"
            raise RuntimeError(msg)
        text = resp.decode("ascii")
        m = re.match(r"\x1b_Gi=(\d+),i=(\d+);OK\x1b\\", text)
        if not m or int(m.group(2)) != img_num:
            msg = f"Unexpected kitty response: {text!r}"
            raise RuntimeError(msg)
        return int(m.group(1))

    def close(self) -> None:
        """Clear any cached data."""
        self.invalidate_cache()
