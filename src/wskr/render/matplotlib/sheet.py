"""Pure contact-sheet composition for a foreground Kitty figure session.

Individual Matplotlib figures own their geometry and exports. This module
produces a separate display-only raster, never changing any Figure property.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.backends.backend_agg import FigureCanvasAgg

    from wskr.terminal.profile import Geometry


def contact_sheet(canvases: Sequence[FigureCanvasAgg], geometry: Geometry, *, scale: float = 1.0) -> bytes:
    """Render independent Agg canvases within nonoverlapping viewport tiles.

    Reserve two terminal rows for an explicit prompt and rounding. The
    contact sheet is a single Kitty placement, preventing competing figure
    managers from relying on terminal cursor motion for their layout.
    """
    count = len(canvases)
    if count < 2 or geometry.rows < 4 or geometry.width_px <= 0 or geometry.height_px <= 0:
        msg = "Contact sheet requires multiple figures and measured terminal geometry"
        raise ValueError(msg)
    columns = 2 if geometry.width_px >= geometry.height_px * 1.15 else 1
    rows = (count + columns - 1) // columns
    available_h = geometry.height_px * (geometry.rows - 2) // geometry.rows
    margin = min(12, max(2, geometry.width_px // 150))
    tile_w = (geometry.width_px - margin * (columns + 1)) // columns
    tile_h = (available_h - margin * (rows + 1)) // rows
    if tile_w < 2 or tile_h < 2:
        msg = "Terminal is too small for a multi-figure contact sheet"
        raise ValueError(msg)

    sheet = Image.new("RGBA", (geometry.width_px, available_h))
    for index, canvas in enumerate(canvases):
        raster = BytesIO()
        canvas.print_png(raster)
        with Image.open(BytesIO(raster.getvalue())) as source:
            pixel_scale = min(scale, tile_w / source.width, tile_h / source.height)
            width = max(1, round(source.width * pixel_scale))
            height = max(1, round(source.height * pixel_scale))
            panel = source.convert("RGBA")
            if panel.size != (width, height):
                panel = panel.resize((width, height), Image.Resampling.LANCZOS)
            col = index % columns
            row = index // columns
            x = margin + col * (tile_w + margin) + (tile_w - width) // 2
            y = margin + row * (tile_h + margin) + (tile_h - height) // 2
            sheet.alpha_composite(panel, (x, y))

    output = BytesIO()
    sheet.save(output, format="PNG")
    return output.getvalue()
