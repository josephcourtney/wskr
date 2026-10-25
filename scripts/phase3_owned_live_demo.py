"""Manual foreground Kitty demo of explicitly owned, repainted Matplotlib output.

Run: WSKR_FIT=contain MPLBACKEND=wskr_kitty uv run python scripts/phase3_owned_live_demo.py
Resize the Kitty window while the colors and title change. Ctrl-C restores
the original shell screen without preserving an inline plot in history.
"""

from __future__ import annotations

import time

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from wskr.render.matplotlib.live import owned_viewport


def main() -> None:
    fig = Figure(figsize=(9, 4), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    bars = ax.bar([1, 2], [3, 4], color=("red", "blue"))
    ax.set(xlim=(0.2, 2.8), ylim=(0, 5))
    with owned_viewport(fig) as view:
        for step in range(240):
            if step % 10 == 0:
                bars[0].set_height(1 + (step % 50) / 15)
                bars[1].set_height(4 - (step % 50) / 15)
                ax.set_title(f"Owned live Kitty viewport — frame {step // 10}")
                view.refresh()
            view.poll_resize()
            time.sleep(0.05)


if __name__ == "__main__":
    main()
