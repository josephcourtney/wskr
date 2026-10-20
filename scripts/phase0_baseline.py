"""Read-only diagnostic baseline of wskr's current terminal backend.

Does not attempt to transmit terminal graphics or claim visual validation.
Run: uv run python scripts/phase0_baseline.py
"""

from __future__ import annotations

import importlib
import importlib.metadata
import io
import json
import os
import platform
import shutil
import sys

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from wskr.protocol.registry import get_image_protocol

BASELINE_FIGURE_DPI = 120

EXPECTED_BACKENDS = {
    "wskr": "wskr.render.matplotlib.core",
    "wskr_kitty": "wskr.render.matplotlib.kitty",
    "wskr_sixel": "wskr.render.matplotlib.sixel",
    "wskr_iterm2": "wskr.render.matplotlib.iterm2",
}


def baseline() -> dict[str, object]:
    """Capture reproducible runtime facts without contacting a terminal."""
    # Avoid triggering a graphics backend through pyplot.
    matplotlib.use("Agg", force=True)
    result: dict[str, object] = {
        "schema": "wskr-phase0-baseline-v1",
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "stdout_is_tty": os.isatty(sys.stdout.fileno()),
        "kitty_executable": bool(shutil.which("kitty")),
        "tty_graphics_verified": False,
        "live_kitty_validation": "not-run",
    }

    fig = Figure(figsize=(3.25, 1.75), dpi=BASELINE_FIGURE_DPI)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.plot([0, 1, 2], [2, 1, 3])
    png, svg = io.BytesIO(), io.BytesIO()
    fig.savefig(png, format="png")
    fig.savefig(svg, format="svg")
    result["agg_export"] = {
        "png_signature": png.getvalue().startswith(b"\x89PNG\r\n\x1a\n"),
        "svg_signature": b"<svg" in svg.getvalue(),
        "preserved_figsize": tuple(fig.get_size_inches()) == (3.25, 1.75),
        "preserved_dpi": fig.dpi == BASELINE_FIGURE_DPI,
    }

    eps = importlib.metadata.entry_points(group="matplotlib.backend")
    registered = {ep.name: ep.value for ep in eps if ep.name in EXPECTED_BACKENDS}
    result["entry_points"] = registered
    result["entry_points_match"] = registered == EXPECTED_BACKENDS

    modules = {
        "matplotlib_core": "wskr.render.matplotlib.core",
        "matplotlib_kitty": "wskr.render.matplotlib.kitty",
        "rich_image": "wskr.render.rich.img",
        "rich_plot": "wskr.render.rich.plt",
        "protocol_registry": "wskr.protocol.registry",
    }
    result["module_imports"] = {}
    for label, path in modules.items():
        try:
            importlib.import_module(path)
        except Exception as exc:  # ruff: ignore[blind-except] - capture all import failures
            result["module_imports"][label] = f"{type(exc).__name__}: {exc}"
        else:
            result["module_imports"][label] = "ok"

    old_protocol = os.environ.pop("WSKR_PROTOCOL", None)
    try:
        default_protocol = get_image_protocol()
        result["default_protocol"] = type(default_protocol).__name__
        default_protocol.close()
    finally:
        if old_protocol is not None:
            os.environ["WSKR_PROTOCOL"] = old_protocol

    return result


if __name__ == "__main__":
    report = baseline()
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["entry_points_match"] or not all(value == "ok" for value in report["module_imports"].values()):
        raise SystemExit(1)
    if not all(report["agg_export"].values()):
        raise SystemExit(1)
