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

_MIN_FIGURES = 2
_MIN_TERMINAL_ROWS = 4
_MIN_TILE_PX = 2
_LANDSCAPE_THRESHOLD = 1.15


def _place_panel(
    sheet: Image.Image,
    canvas: FigureCanvasAgg,
    *,
    tile_origin: tuple[int, int],
    tile_size: tuple[int, int],
    scale: float,
) -> None:
    """Draw one source figure within its own tile, without editing the figure."""
    raster = BytesIO()
    canvas.print_png(raster)
    with Image.open(BytesIO(raster.getvalue())) as source:
        pixel_scale = min(scale, tile_size[0] / source.width, tile_size[1] / source.height)
        width = max(1, round(source.width * pixel_scale))
        height = max(1, round(source.height * pixel_scale))
        panel = source.convert("RGBA")
        if panel.size != (width, height):
            panel = panel.resize((width, height), Image.Resampling.LANCZOS)
        x = tile_origin[0] + (tile_size[0] - width) // 2
        y = tile_origin[1] + (tile_size[1] - height) // 2
        sheet.alpha_composite(panel, (x, y))


def contact_sheet(canvases: Sequence[FigureCanvasAgg], geometry: Geometry, *, scale: float = 1.0) -> bytes:
    """Render independent Agg canvases within nonoverlapping viewport tiles.

    Reserve two terminal rows for an explicit prompt and rounding. The
    contact sheet is a single Kitty placement, preventing competing figure
    managers from relying on terminal cursor motion for their layout.
    """
    count = len(canvases)
    if count < _MIN_FIGURES or geometry.rows < _MIN_TERMINAL_ROWS or geometry.width_px <= 0 or geometry.height_px <= 0:
        msg = "Contact sheet requires multiple figures and measured terminal geometry"
        raise ValueError(msg)
    columns = 2 if geometry.width_px >= geometry.height_px * _LANDSCAPE_THRESHOLD else 1
    rows = (count + columns - 1) // columns
    available_h = geometry.height_px * (geometry.rows - 2) // geometry.rows
    margin = min(12, max(2, geometry.width_px // 150))
    tile_w = (geometry.width_px - margin * (columns + 1)) // columns
    tile_h = (available_h - margin * (rows + 1)) // rows
    if tile_w < _MIN_TILE_PX or tile_h < _MIN_TILE_PX:
        msg = "Terminal is too small for a multi-figure contact sheet"
        raise ValueError(msg)

    sheet = Image.new("RGBA", (geometry.width_px, available_h))
    for index, canvas in enumerate(canvases):
        _place_panel(
            sheet,
            canvas,
            tile_origin=(margin + index % columns * (tile_w + margin), margin + index // columns * (tile_h + margin)),
            tile_size=(tile_w, tile_h),
            scale=scale,
        )

    output = BytesIO()
    sheet.save(output, format="PNG")
    return output.getvalue()
