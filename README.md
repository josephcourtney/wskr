# wskr

**Experimental Matplotlib-in-terminal rendering**, with a Kitty backend, a protocol registry, and Rich renderables.

wskr currently uses Matplotlib's Agg renderer to produce images for a graphical terminal. The project is being redesigned to take its default size, colors, typography and light/dark appearance from the **running terminal**, while keeping the public plotting API unchanged. The planned behavior is specified in [DESIGN.md](DESIGN.md); **it is not all implemented yet**.

## What works today

- A `wskr_kitty` Matplotlib backend based on `FigureCanvasAgg`/`FigureManagerBase`.
- A Kitty transport that runs the external `kitty +kitten icat` command to size/display PNGs.
- A protocol registry, terminal-size helpers and an OSC-based dark-mode detection utility.
- `RichPlot` and `RichImage` renderable implementations for Rich.
- An experimental direct Kitty transport implementation (not a production-ready substitute for `icat`).

**Limitations:** direct Kitty PNG encoding is incomplete, terminal sizing uses heuristics, theme matching is not automatic at default figure creation, and live resizing/managed placements are not established. `wskr_sixel` and `wskr_iterm2` are **stubs, not supported backends**, even though names are registered. The current generic backend can select a warning/no-op transport; do not use it as proof of graphics support. See [STATUS.md](STATUS.md).

## Requirements and local installation

This repository declares **Python >=3.13,<3.15**, Matplotlib >=3.10.1 and the dependencies in [pyproject.toml](pyproject.toml). A Kitty terminal **and the `kitty` executable on PATH** are currently required for the primary graphics transport.

From a checkout:

```sh
uv sync
```

Run the installed development environment with `uv run` (or activate its environment). The `justfile` provides wskr-specific checks and smoke tests. Runtime success still requires validation in your environment; consult [STATUS.md](STATUS.md).

## Basic Matplotlib usage

```python
import matplotlib
matplotlib.use("wskr_kitty")  # before importing pyplot

import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([0, 1, 2], [10, 20, 15], marker="o")
ax.set_title("Hello, Kitty")
plt.show()
```

Instead of selecting the backend in Python, set it externally:

```sh
MPLBACKEND=wskr_kitty uv run python example.py
```

The explicit module path may also be selected as `module://wskr.render.matplotlib.kitty`. This is a terminal-display backend: normal `fig.savefig("plot.png")` and `fig.savefig("plot.svg")` remain the ordinary Matplotlib interfaces for files.

**Current caution:** the backend's display code resizes figures to the viewport using heuristic dimensions and the backend show path may close figure managers. The intended behavior (respect explicit `figsize`/`dpi`, correct `block=...`, REPL and pandas auto-display, multi-figure management) is an adopted **requirement**, not a validated current guarantee.

## Using the current Rich adapter

```python
import matplotlib.pyplot as plt
from rich.console import Console
from wskr.render.rich.plt import RichPlot

fig, ax = plt.subplots()
ax.plot([0, 1, 2], [2, 3, 1])

Console().print(RichPlot(fig, desired_width=40, desired_height=10))
```

The current default protocol registry uses `noop` unless a transport is requested or configured. For experimental Kitty-backed Rich rendering, set `WSKR_PROTOCOL=kitty` in the environment, with Kitty's executable available. The Rich image upload/Unicode placeholder implementation still requires protocol and visual verification; it may not display correctly in all layouts. Do not use it for an unattended production dashboard yet.

## Extending transports

The current extension interface is `wskr.protocol.base.ImageProtocol`, registered by `wskr.protocol.registry.register_image_protocol(name, cls)`. It exposes `get_window_size_px()`, `send_image(png_bytes)` and `init_image(png_bytes)`; the registry can load entry points from `wskr.image_protocols`.

A transport is not considered supported merely because it is registered. The future protocol and placement lifecycle are specified in [DESIGN.md](DESIGN.md), and the migration path is in [PLAN.md](PLAN.md).

## Documentation

| Document | Role |
| --- | --- |
| [DESIGN.md](DESIGN.md) | Durable intended capabilities, interfaces and invariants |
| [PLAN.md](PLAN.md) | Phased migration and validation strategy |
| [STATUS.md](STATUS.md) | Current implementation, limitations and handoff |
| [TODO.md](TODO.md) | Immediate unfinished engineering work |
| [CHANGELOG.md](CHANGELOG.md) | Curated completed user-visible changes |
| [Architecture decisions](docs/adr/) | Rationale for durable design choices |
| [POLICY.md](POLICY.md) | Authoritative document/history policy |
| [AGENTS.md](AGENTS.md) | Contributor instructions specific to wskr |

## Testing and maturity

Test files exist under `tests/`, including unit and PTY cases and opt-in Kitty screenshot work. A full successful test run **has not been established for the current repository state**; Phase 0 adds diagnostic checks and installed-wheel probes but they still require execution in a local environment. Core local checks should use the wskr-specific `uv` environment; the existing `justfile` currently contains unrelated Cwide settings.

Development should not be declared complete based on unit or simulated terminal tests alone. Real Kitty appearance, image placement, cleanup and resize/theme behavior have distinct acceptance criteria in [PLAN.md](PLAN.md).

## License

[GPL-3.0-only](LICENSE.md).
