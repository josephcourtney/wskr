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

import matplotlib.pyplot as plt

```python
from rich.console import Console
from wskr.rich.plt import RichPlot

console = Console()
fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot([0,1,2], [2,3,1], c="w")
rich_plot = RichPlot(fig, desired_width=40, desired_height=10)
console.print(rich_plot)
```

## Extending to new protocols

To add a new terminal protocol (e.g. `MyTerm`) for inline Matplotlib rendering:

### ✅ Step 1: Implement a Custom Transport

Create a class that inherits from `ImageTransport` and implements:

```python
from wskr.tty.base import ImageTransport

class MyTermTransport(ImageTransport):
    def get_window_size_px(self) -> tuple[int, int]:
        # return (width_px, height_px)
        ...

    def send_image(self, png_bytes: bytes) -> None:
        # display image in terminal
        ...

    def init_image(self, png_bytes: bytes) -> int:
        # optional: upload image once, return an ID
        ...
```

Then register it:

```python
from wskr.tty.registry import register_image_transport
register_image_transport("myterm", MyTermTransport)
```

---

### ✅ Step 2: Define a Matplotlib Backend

Use the shared base classes for minimal boilerplate:

```python
import matplotlib.pyplot as plt
from matplotlib import _api
from matplotlib.backend_bases import _Backend
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib._pylab_helpers import Gcf

from wskr.mpl.base_backend import BaseFigureManager
from myterm_module import MyTermTransport  # your transport from Step 1

plt.style.use("dark_background")


class MyTermFigureManager(BaseFigureManager):
    def __init__(self, canvas: FigureCanvasAgg, num: int = 1):
        super().__init__(canvas, num, MyTermTransport)


class MyTermFigureCanvas(FigureCanvasAgg):
    manager_class = _api.classproperty(lambda _: MyTermFigureManager)


@_Backend.export
class _BackendMyTermAgg(_Backend):
    FigureCanvas = MyTermFigureCanvas
    FigureManager = MyTermFigureManager

    @classmethod
    def draw_if_interactive(cls):
        manager = Gcf.get_active()
        if manager and manager.canvas.figure.get_axes():
            cls.show()

    @classmethod
    def show(cls, *args, **kwargs):
        manager = Gcf.get_active()
        if manager:
            manager.show(*args, **kwargs)
            Gcf.destroy_all()
```

---

### ✅ Step 3: Add It to `pyproject.toml`

```toml
[project.entry-points."matplotlib.backends"]
wskr_myterm = "your_module_path"
```

---

### ✅ Step 4: Use It

```python
import matplotlib
matplotlib.use("wskr_myterm")

import matplotlib.pyplot as plt
plt.plot([1, 2, 3])
plt.show()
```

## Testing

```bash
pytest
```

## License

GPL-3.0-only
