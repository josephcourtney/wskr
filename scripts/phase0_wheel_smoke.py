"""Build-free wheel-install smoke test in a fresh environment.

Run after: uv build --no-sources
Then:      uv run python scripts/phase0_wheel_smoke.py

Dependency acquisition may require access to a configured package index.
No live Kitty output is attempted; actual terminal graphics remain a separate test.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - isolated wheel-install subprocess
import sys
import tempfile


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed argv, no shell
        cmd, check=False, env=env, text=True, capture_output=True, timeout=180
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{' '.join(cmd)} failed ({completed.returncode})\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
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
        env["MPLBACKEND"] = "Agg"
        env["MPLCONFIGDIR"] = str(Path(temp) / "mplconfig")
        script = """
import importlib, importlib.metadata, io, json, matplotlib
eps = {ep.name:ep.value for ep in importlib.metadata.entry_points(group='matplotlib.backend') if ep.name.startswith('wskr')}
assert eps.get('wskr_kitty') == 'wskr.render.matplotlib.kitty', eps
importlib.import_module('wskr.render.matplotlib.kitty')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
f=Figure(figsize=(4,2),dpi=100)
FigureCanvasAgg(f)
f.subplots().plot([0,1],[1,0])
p=io.BytesIO()
f.savefig(p,format='png')
assert p.getvalue().startswith(b'\\x89PNG\\r\\n\\x1a\\n')
print(json.dumps({'installed_version':importlib.metadata.version('wskr'),'backend_entries':eps,'png_export':'ok','kitty_import':'ok'}))
"""
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed argv, no shell
            [interpreter, "-c", script], cwd=temp, env=env,
            capture_output=True, text=True, check=False, timeout=120,
        )
        if completed.returncode:
            msg = f"Installed-wheel smoke failed: {completed.stderr}"
            raise RuntimeError(msg)
        print(completed.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
