"""Real Kitty physical and virtual placement smoke checks for Phase 2.

This script is run in a dedicated Kitty terminal by the evidence collector.
No terminal graphics result is called visually correct until an OS screenshot
has been inspected independently.
"""

from __future__ import annotations

import argparse
import sys
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from wskr.protocol.kitty_native import NativeKittyTransport
from wskr.protocol.kitty_placeholders import placeholder_rows

if TYPE_CHECKING:
    from collections.abc import Sequence

_COLUMNS = 34
_ROWS = 12


def _png() -> bytes:
    """Build a high-contrast reference with distinguishable graphics."""
    fig = Figure(figsize=(4.4, 1.9), dpi=120, facecolor="white")
    canvas = FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.set_facecolor("black")
    ax.bar([2, 5, 8], [1.5, 3.5, 2.5], width=1.8, color=["cyan", "magenta", "yellow"])
    ax.set_title("Direct Kitty graphics", color="black")
    ax.set_yticks([])
    buf = BytesIO()
    canvas.print_png(buf)
    return buf.getvalue()


def main(argv: Sequence[str] | None = None) -> None:
    """Run one reproducible native Kitty display and report its image IDs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("native-physical", "native-virtual"), required=True)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--pause", action="store_true")
    args = parser.parse_args(argv)

    data = _png()
    if args.reference is not None:
        args.reference.parent.mkdir(parents=True, exist_ok=True)
        args.reference.write_bytes(data)

    transport = NativeKittyTransport()
    print(f"Scenario: {args.mode} | direct f=100 upload | {_COLUMNS} columns x {_ROWS} rows")
    image_id = transport.init_image(data)
    placement_id = transport.place_image(
        image_id, columns=_COLUMNS, rows=_ROWS, virtual=args.mode == "native-virtual"
    )
    if args.mode == "native-virtual":
        for line in placeholder_rows(image_id, placement_id, columns=_COLUMNS, rows=_ROWS):
            print(line)
    else:
        # Physical placement has C=1; reserve its rectangle explicitly.
        for _ in range(_ROWS):
            print()
    print(f"Kitty image id: {image_id}; placement id: {placement_id}; inspect reference PNG.")
    sys.stdout.flush()
    if args.ready_file is not None:
        args.ready_file.write_text("render-complete\\n", encoding="utf-8")
    if args.pause:
        input("Inspect/capture this owned Kitty window, then press Enter to exit: ")


if __name__ == "__main__":
    main()
