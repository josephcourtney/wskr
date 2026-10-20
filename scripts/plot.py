import matplotlib.pyplot as plt
from rich.console import Console

import wskr.protocol.kitty  # ruff: ignore[unused-import]
from wskr.render.rich.plt import RichPlot

# 1) build a matplotlib figure
fig, ax = plt.subplots()
ax.plot([0, 1, 2, 3], [0, 1, 0, 1], marker="o")
ax.set_title("wskr → Rich demo")
ax.set_xlabel("x")
ax.set_ylabel("y")

# 2) wrap the figure as a Rich renderable
#    desired_width/height are in terminal character cells.
renderable = RichPlot(fig, desired_width=80, desired_height=24, dpi=110, zoom=1.0)

# 3) print to the terminal via Rich
Console().print(renderable)
