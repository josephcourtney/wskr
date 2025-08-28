import os
import sys
from pathlib import Path

from wskr.protocol.kgp.kgp import KittyTransport


def main():
    img_path = Path(__file__).parent / "test.png"
    if not img_path.exists():
        print(f"[DEBUG] ERROR: demo image not found at {img_path}", file=sys.stderr)
        sys.exit(1)

    png = img_path.read_bytes()
    transport = KittyTransport()

    try:
        transport.send_image(png)
    except RuntimeError as e:
        print(f"[DEBUG] ✖ Failed to send image: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print("[DEBUG] ✔ Image sent successfully.", file=sys.stderr)

    if done_file := os.environ.get("KITTY_DEMO_DONE_FILE"):
        Path(done_file).write_text("done", encoding="utf-8")


if __name__ == "__main__":
    main()
