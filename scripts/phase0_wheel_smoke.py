"""Build-free wheel-install smoke test in a fresh environment.

Run after: uv build --no-sources
Then:      uv run python scripts/phase0_wheel_smoke.py

Dependency acquisition may require access to a configured package index.
No live Kitty output is attempted; actual terminal graphics remain a separate test.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - isolated wheel-install subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed argv, no shell
        cmd,
        check=False,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    if completed.returncode != 0:
        msg = f"{' '.join(cmd)} failed ({completed.returncode})\n{completed.stdout}\n{completed.stderr}"
        raise RuntimeError(msg)
    if completed.stdout:
        print(completed.stdout.strip())


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("uv is not installed", file=sys.stderr)
        return 2
    wheels = sorted(Path("dist").glob("wskr-*.whl"))
    if len(wheels) != 1:
        print(
            "Expected exactly one current wskr wheel in dist/; clear stale wheels and run just build",
            file=sys.stderr,
        )
        return 2
    wheel = str(wheels[0].resolve())

    with tempfile.TemporaryDirectory(prefix="wskr-phase0-wheel-") as temp:
        venv = Path(temp) / "venv"
        run([uv, "venv", "--python", sys.executable, str(venv)])
        interpreter = str(venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        run([uv, "pip", "install", "--python", interpreter, wheel])
        # Remove any checkout Python path; run outside repository to avoid local import shadowing.
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.pop("WSKR_FIT", None)
        env.pop("WSKR_SCALE", None)
        env["PYTHONNOUSERSITE"] = "1"
        env["MPLCONFIGDIR"] = str(Path(temp) / "mplconfig")
        script = """
import importlib.metadata
import io
import json
import os
import struct

import matplotlib
import matplotlib.pyplot as plt

from matplotlib.backends.backend_agg import FigureCanvasAgg
from wskr.render.matplotlib.kitty import KittyFigureCanvas

entries = {
    ep.name: ep.value
    for ep in importlib.metadata.entry_points(group='matplotlib.backend')
    if ep.name.startswith('wskr')
}
expected = {
    'wskr': 'wskr.render.matplotlib.core',
    'wskr_kitty': 'wskr.render.matplotlib.kitty',
    'wskr_sixel': 'wskr.render.matplotlib.sixel',
    'wskr_iterm2': 'wskr.render.matplotlib.iterm2',
}
assert all(entries.get(name) == target for name, target in expected.items()), entries

requested = os.environ['MPLBACKEND']
assert matplotlib.get_backend().lower() == requested.lower(), (
    matplotlib.get_backend(), requested
)
fig, ax = plt.subplots(figsize=(4, 2), dpi=100)
if requested == 'Agg':
    assert isinstance(fig.canvas, FigureCanvasAgg)
else:
    assert isinstance(fig.canvas, KittyFigureCanvas), type(fig.canvas)
ax.plot([0, 1, 2], [1, 3, 2])
assert tuple(fig.get_size_inches()) == (4.0, 2.0)
assert fig.dpi == 100

png = io.BytesIO()
fig.savefig(png, format='png')
image = png.getvalue()
assert image.startswith(bytes.fromhex('89504e470d0a1a0a'))
assert struct.unpack('>II', image[16:24]) == (400, 200)

svg = io.BytesIO()
fig.savefig(svg, format='svg')
assert b'<svg' in svg.getvalue()
assert tuple(fig.get_size_inches()) == (4.0, 2.0)
assert fig.dpi == 100
plt.close(fig)

print(json.dumps({
    'installed_version': importlib.metadata.version('wskr'),
    'backend': requested,
    'canvas': type(fig.canvas).__name__,
    'png_export': '400x200',
    'svg_export': 'ok',
    'backend_entries': entries,
}))
"""
        for backend in ("Agg", "wskr_kitty", "module://wskr.render.matplotlib.kitty"):
            # Each invocation is a separate interpreter outside the checkout;
            # source imports cannot accidentally satisfy the wheel test.
            env["MPLBACKEND"] = backend
            completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed argv, no shell
                [interpreter, "-c", script],
                cwd=temp,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            if completed.returncode:
                msg = f"Installed-wheel backend {backend} failed:\n{completed.stdout}\n{completed.stderr}"
                raise RuntimeError(msg)
            print(completed.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
