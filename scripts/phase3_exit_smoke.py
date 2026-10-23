"""Render ordinary Matplotlib output, exit Python, and leave Kitty history visible.

The completion marker is written by the earliest atexit callback, after
Matplotlib's registered figure-manager cleanup has finished. Kitty --hold
keeps the window available for a screenshot after the Python process exits.
"""

from __future__ import annotations

import argparse
import atexit
from contextlib import nullcontext
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    """Draw a deterministic colored chart and exit without calling plt.close."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--fit-file", type=Path, help="Record verified real-Kitty viewport containment")
    args = parser.parse_args(argv)

    # This callback is registered *before* importing Matplotlib, so it runs
    # after Gcf.destroy_all and the backend's shutdown marker.
    atexit.register(args.ready_file.write_text, "python-exited\n", encoding="utf-8")

    import matplotlib as mpl  # ruff: ignore[import-outside-top-level]

    mpl.use("module://wskr.render.matplotlib.kitty")
    import matplotlib.pyplot as plt  # ruff: ignore[import-outside-top-level]
    from PIL import Image  # ruff: ignore[import-outside-top-level]

    from wskr.protocol.kitty_native import NativeKittyTransport  # ruff: ignore[import-outside-top-level]

    source = (6, 6) if args.fit_file is not None else (4, 3)
    dpi = 300 if args.fit_file is not None else 110
    _, ax = plt.subplots(figsize=source, dpi=dpi)
    ax.bar([1, 2, 3], [1.5, 2.5, 2], color=("cyan", "magenta", "yellow"))
    ax.set(xlim=(0.5, 3.5), ylim=(0, 3), title="wskr: persistent output after Python exit")

    send = NativeKittyTransport.send_anchored_image

    def inspect_and_send(transport: NativeKittyTransport, png_bytes: bytes) -> None:
        if args.fit_file is not None:
            viewport = transport.get_window_size_px()
            with Image.open(BytesIO(png_bytes)) as image:
                output = image.size
            if not (0 < output[0] <= viewport[0] and 0 < output[1] <= viewport[1]):
                msg = f"Kitty display {output} exceeded measured viewport {viewport}"
                raise AssertionError(msg)
        send(transport, png_bytes)
        if args.fit_file is not None:
            args.fit_file.write_text(f"{output[0]}x{output[1]} of {viewport[0]}x{viewport[1]}\n", encoding="utf-8")

    context = (
        patch.object(NativeKittyTransport, "send_anchored_image", inspect_and_send) if args.fit_file else nullcontext()
    )
    with context:
        plt.show()
    print("Rendered ordinary Matplotlib output; Python is exiting.")


if __name__ == "__main__":
    main()
