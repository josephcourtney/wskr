"""End-to-end native Kitty packet delivery to a real POSIX pseudo-terminal.

No GUI terminal is required: collect the exact stream the emulator would
receive and validate upload, virtual placement, and scoped disposal together.
"""

from __future__ import annotations

import base64
import os
import select
import sys
import threading
from io import BytesIO

import pytest
from PIL import Image

from wskr.protocol.kitty_native import NativeKittyTransport

pytestmark = pytest.mark.medium
_ST = b"\x1b\\"
_APC = b"\x1b_G"


class _TTYStream:
    def __init__(self, fd: int) -> None:
        self.fd = fd

    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return self.fd


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (12, 8), (0, 180, 240, 255)).save(buffer, "PNG")
    return buffer.getvalue()


def test_native_upload_virtual_place_and_dispose_across_real_pty(monkeypatch) -> None:
    master, slave = os.openpty()
    fragments: list[bytes] = []
    done = threading.Event()
    errors: list[Exception] = []

    def drain() -> None:
        try:
            while not done.is_set() or select.select([master], [], [], 0.01)[0]:
                if select.select([master], [], [], 0.01)[0]:
                    fragments.append(os.read(master, 65536))
        except OSError as exc:
            errors.append(exc)

    reader = threading.Thread(target=drain)
    try:
        with monkeypatch.context() as patched:
            patched.setenv("TERM", "xterm-kitty")
            patched.setattr(sys, "stdout", _TTYStream(slave))
            reader.start()
            transport = NativeKittyTransport()
            source = _png()
            image_id = transport.init_image(source)
            placement_id = transport.place_image(image_id, columns=5, rows=3, virtual=True)
            transport.manager.remove_placement(image_id, placement_id)
            transport.close()
    finally:
        done.set()
        reader.join(timeout=2)
        os.close(master)
        os.close(slave)

    assert not reader.is_alive()
    assert not errors
    raw = b"".join(fragments)
    assert not source in raw  # PNG data must be Base64, not binary bytes.
    frames = raw.split(_ST)
    assert frames[-1] == b""
    assert len(frames) == 5
    assert all(part.startswith(_APC) for part in frames[:-1])

    upload, placement, removal, cleanup = frames[:-1]
    assert upload.startswith(f"\x1b_Ga=t,f=100,t=d,i={image_id},q=2,m=0;".encode())
    assert base64.b64decode(upload.split(b";", 1)[1]) == source
    assert f"a=p,i={image_id},p={placement_id},c=5,r=3,U=1,q=2".encode() in placement
    assert f"a=d,d=i,i={image_id},p={placement_id},q=2".encode() in removal
    assert f"a=d,d=I,i={image_id},q=2".encode() in cleanup
