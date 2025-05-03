import re
import shutil
import subprocess  # noqa: S404
import sys

from wskr.ttyools import query_tty

from .base import ImageTransport


class KittyTransport(ImageTransport):
    """Implmentation of Kitty Image Protocol as a transport layer.

    Unified Kitty protocol:
    - send_image() → one-off `kitty +kitten icat`
    - init_image() → low-level ESC_G upload, return image ID.
    """

    def __init__(self) -> None:
        self._kitty = shutil.which("kitty")
        if not self._kitty:
            msg = "[wskr] Kitty transport not available: 'kitty' binary not found."
            raise RuntimeError(msg)
        self._next_img = 1

    def get_window_size_px(self) -> tuple[int, int]:
        proc = subprocess.run(  # noqa: S603
            [self._kitty, "+kitten", "icat", "--print-window-size"],
            capture_output=True,
            text=True,
            check=False,
        )
        w_px, h_px = map(int, proc.stdout.strip().split("x"))
        rows = self._tput_lines()
        # subtract a few lines for prompt etc.
        return w_px, h_px - (3 * h_px) // rows

    @staticmethod
    def _tput_lines() -> int:
        tput = shutil.which("tput")
        if not tput:
            return 24
        proc = subprocess.run([tput, "lines"], capture_output=True, text=True, check=False)  # noqa: S603
        return int(proc.stdout.strip() or 24)

    def send_image(self, png_bytes: bytes) -> None:
        """Send image to display via kitty +kitten icat."""
        subprocess.run(  # noqa: S603
            [self._kitty, "+kitten", "icat", "--align", "center"],
            input=png_bytes,
            stdout=sys.stderr,
            check=False,
        )

    def init_image(self, png_bytes: bytes) -> int:
        """Upload PNG in 4K chunks via ESC_G; parse Kitty's reply for an image ID."""
        img_num = self._next_img
        self._next_img += 1

        # send in 4K chunks with m=1
        for i in range(0, len(png_bytes), 4096):
            chunk = png_bytes[i : i + 4096]
            header = f"\x1b_Ga=t,q=0,f=32,i={img_num},m=1;"
            sys.stdout.buffer.write(header.encode("ascii") + chunk + b"\x1b\\")
            sys.stdout.flush()

        # terminate upload (m=0) and read response
        term = f"\x1b_Ga=t,q=0,f=32,i={img_num},m=0;\x1b\\"
        resp = query_tty(term.encode("ascii"), more=lambda b: not b.endswith(b"\x1b\\"), timeout=1.0)
        if not resp:
            msg = "No response from kitty on image init"
            raise RuntimeError(msg)
        text = resp.decode("ascii")
        m = re.match(r"\x1b_Gi=(\d+),i=(\d+);OK\x1b\\", text)
        if not m or int(m.group(2)) != img_num:
            msg = f"Unexpected kitty response: {text!r}"
            raise RuntimeError(msg)
        return int(m.group(1))

    def render_image(self, image_id: int, width: int, height: int) -> None:  # noqa: PLR6301
        """Paint a previously uploaded image at the given cell dimensions."""
        seq = f"\x1b_Ga=p,q=2,i={image_id},c={width},r={height}\x1b\\"
        sys.stdout.write(seq)
        sys.stdout.flush()
