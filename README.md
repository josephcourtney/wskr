# wskr

A modular, pluggable Matplotlib “image‐in‐terminal” backend.

## What is wskr?

wskr lets you render Matplotlib figures as inline images in terminals that support Kitty, iTerm2, or Sixel protocols. It cleanly separates:

- **Transports** (`wskr.tty.*`): how to talk to the terminal (e.g. Kitty image protocol, Sixel, etc.).
- **Backends** (`wskr.mpl.*`): a generic Matplotlib FigureCanvas/FigureManager that uses a Transport to size and send a PNG.
- **Rich integration** (`wskr.rich.*`): display plots in a `rich` console using the same transport layer.

## Features

- **Kitty backend** out of the box (via `KittyTransport`)
- Planned support for iTerm2 & Sixel
- Registry of transports so you can add new protocols without touching Matplotlib code
- Automatic resizing to fill your terminal viewport while preserving aspect ratio
- `rich` renderables for embedding plots in TUI applications

## Installation

```bash
pip install wskr
```

## Quick start

```python
import matplotlib
# choose one of: wskr (generic), wskr_kitty, wskr_sixel, wskr_iterm2
matplotlib.use("wskr_kitty")
import matplotlib.pyplot as plt

# make a simple plot...
plt.plot([0, 1, 2], [10, 20, 15], marker="o")
plt.title("Hello, terminal!")
plt.show()   # renders inline via Kitty protocol
```

## Using with Rich

```python
from rich.console import Console
from wskr.plot import make_plot_grid
from wskr.rich.plt import RichPlot

console = Console()
fig, ax = make_plot_grid(1, 1)
ax.plot([0,1,2], [2,3,1], c="w")
rich_plot = RichPlot(fig, desired_width=40, desired_height=10)
console.print(rich_plot)
```

## Extending to new protocols

1. Subclass `wskr.tty.base.ImageTransport` and implement:

   - `get_window_size_px()`
   - `send_image(png_bytes: bytes)`
   - `init_image(png_bytes: bytes) -> int`

2. Register your transport:

   ```python
   from wskr.tty import register_image_transport
   register_image_transport("myproto", MyProtoTransport)
   ```

3. Use it via environment variable or explicit name:

   ```bash
   export WSKR_TRANSPORT=myproto
   matplotlib.use("wskr")
   ```

## Testing

```bash
pytest
```

## License

GPL-3.0-only

```

Feel free to expand with detailed examples or tie into your project’s CI/workflows.
```
