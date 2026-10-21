# wskr

**Experimental Matplotlib-in-terminal rendering**, with a Kitty backend, a protocol registry, and Rich renderables.

wskr currently uses Matplotlib's Agg renderer to produce images for a graphical terminal. The project is being redesigned to take its default size, colors, typography and light/dark appearance from the **running terminal**, while keeping the public plotting API unchanged. The planned behavior is specified in [DESIGN.md](DESIGN.md); **it is not all implemented yet**.

## What works today

- Phase 1's immutable terminal profile, safe optional OSC queries and figure-local default styling are merged and validated.
- On the **Phase 2 feature branch only**, `wskr_kitty` and `WSKR_PROTOCOL=kitty` use a direct Kitty `f=100` PNG codec with bounded Base64 framing. The code is **awaiting macOS/Kitty acceptance**, not yet a validated release.
- The native image manager provides uploads, physical and virtual placements, scoped deletion, and an explicitly input-owned capability probe. The former external `kitty +kitten icat` transport is available as `kitty_legacy` for comparison.
- `RichPlot` and `RichImage` retain safe text fallbacks. Actual inline graphics are **not yet implemented**; protocol-level Unicode placeholder encoding is prepared for Phase 4.

**Limitations:** viewport fitting, lifecycle redraw/resize and terminal-dependent contrast are Phase 3 work. Rich virtual placeholder composition and ConsoleOptions sizing are Phase 4 work. `wskr_sixel` and `wskr_iterm2` remain unsupported stubs. See [STATUS.md](STATUS.md).

## Requirements and local installation

This repository declares **Python >=3.13,<3.15**, Matplotlib >=3.10.1 and the dependencies in [pyproject.toml](pyproject.toml). The Phase 2 native implementation requires a directly attached `xterm-kitty` TTY for output; it no longer invokes `kitty icat` for the primary display path. The legacy comparison transport still requires the `kitty` executable on PATH.

From a checkout:

```sh
uv sync
```

Run the installed development environment with `uv run` (or activate its environment). The `justfile` provides wskr-specific checks and smoke tests. Runtime success still requires validation in your environment; consult [STATUS.md](STATUS.md).

## Terminal discovery (Phase 1, accepted)

The development branch introduces immutable `TerminalProfile` measurements and pure default styling. Kernel geometry is read from an attached terminal without escape sequences; unknown font, physical DPI and colors remain explicitly unavailable. Live OSC color interrogation requires **exclusive ownership of terminal input** and a callback that routes any unrelated bytes back to the application. Importing `wskr` no longer changes global Matplotlib `text.usetex`.

```python
from wskr.terminal import probe_profile
from wskr.render.matplotlib.theme import resolve_rc_defaults

profile = probe_profile()  # geometry only; no terminal escape queries
defaults = resolve_rc_defaults(profile)
print(profile.columns.value, profile.cell_width_px.source, defaults)
```

Only backend-owned **initial** figure defaults can use measured terminal dimensions. The legacy display path still resizes figures, and unattended automatic OSC color probing is deliberately disabled until input ownership is available. This is not the final live-theme/resize design.

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

The current default protocol registry uses `noop` unless a transport is requested or configured. Without an image transport, `RichPlot` now displays a visible text fallback, not an image. Setting `WSKR_PROTOCOL=kitty` on the Phase 2 branch selects the direct native transport when a Kitty TTY is available. **Rich inline graphics remain unavailable** by design: the adapter still displays an explicit diagnostic instead of emitting unverified placeholders. The Phase 2 manager and placeholder encoder are prepared for Phase 4's actual Rich placement implementation. Do not use it for an unattended production dashboard yet.

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

## Automated run-specific evidence

For one reproducible output containing validation logs, Matplotlib, Rich, and native physical/virtual placement screenshots, reference PNGs, a manifest and SHA-256 hashes:

```sh
just evidence
```

The command prints the generated `artifacts/evidence/<run-id>.zip` path. It launches uniquely titled Kitty windows and captures each using macOS's window-scoped screenshot facility. Captures require a GUI session and appropriate macOS permissions. Missing screenshots remain explicit failures; captured screenshots must still be reviewed. See the [complete guide](docs/phase1-evidence-bundles.md).

## Phase 1 visual checks (experimental)

Use `just visual-smoke matplotlib` inside Kitty to exercise ordinary pyplot, `WSKR_PROTOCOL=kitty just visual-smoke rich` to examine a Rich panel and table, and `just visual-smoke noop` to verify the intentional text-only fallback. These are manual tests: a zero exit status does not guarantee that an image was displayed. [Detailed screenshot procedure](docs/phase1-visual-procedure.md).

The Phase 1 figure-local defaults apply when terminal measurements are available. Color OSC interrogation is opt-in and requires explicitly owned terminal input; unattended pyplot currently obtains geometry but not queried foreground/background colors. Figures using user-selected Figure/axes subclasses and explicit artist styling remain authoritative.

## Testing and maturity

Phase 1 acceptance succeeded at `5e35aa6`: full `just check` (200 passed, 3 skipped), Phase 1 (55 passed, 1 skipped), PTY (35 passed), and live Kitty (5 passed). The subsequent Phase 2 code has **not yet passed** those checks and needs its own real Kitty evidence. Execute `just check`, `just phase2`, and `just evidence`, then inspect the captured screens. See [Phase 2 validation](docs/phase2-validation.md).

Development should not be declared complete based on unit or simulated terminal tests alone. Real Kitty appearance, image placement, cleanup and resize/theme behavior have distinct acceptance criteria in [PLAN.md](PLAN.md).

## License

[GPL-3.0-only](LICENSE.md).
