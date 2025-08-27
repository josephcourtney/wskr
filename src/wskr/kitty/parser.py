"""Helpers for streaming kitty graphics protocol chunks."""

from __future__ import annotations

import logging
import re
import sys

from wskr.errors import TransportRuntimeError

logger = logging.getLogger(__name__)


class KittyChunkParser:
    """Low-level utilities for kitty chunk framing and responses."""

    _RESP_RE = re.compile(r"\x1b_Gi=(\d+),i=(\d+);OK\x1b\\")

    @staticmethod
    def send_chunk(img_num: int, chunk: bytes, *, final: bool = False) -> None:
        """Emit a kitty graphics chunk to ``stdout``."""
        m_flag = "0" if final else "1"
        logger.debug(
            "KittyChunkParser.send_chunk: img=%d, bytes=%d, final=%s",
            img_num,
            len(chunk),
            final,
        )
        header = f"\x1b_Ga=t,q=0,f=32,i={img_num},m={m_flag};"
        sys.stdout.buffer.write(header.encode("ascii") + chunk + b"\x1b\\")
        sys.stdout.flush()

    @classmethod
    def parse_init_response(cls, img_num: int, resp: bytes) -> int:
        """Validate and extract the kitty image ID from ``resp``."""
        if not resp:
            msg = "No response from kitty on image init"
            raise TransportRuntimeError(msg)
        text = resp.decode("ascii")
        m = cls._RESP_RE.match(text)
        if not m or int(m.group(2)) != img_num:
            msg = f"Unexpected kitty response: {text!r}"
            raise TransportRuntimeError(msg)
        return int(m.group(1))
