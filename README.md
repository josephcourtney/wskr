# wskr

**Experimental Matplotlib-in-terminal rendering**, with a Kitty backend, a protocol registry, and Rich renderables.

wskr currently uses Matplotlib's Agg renderer to produce images for a graphical terminal. The project is being redesigned to take its default size, colors, typography and light/dark appearance from the **running terminal**, while keeping the public plotting API unchanged. The planned behavior is specified in [DESIGN.md](DESIGN.md); **it is not all implemented yet**.

## What works today

- Phase 1's immutable terminal profile, safe optional OSC queries and figure-local default styling are merged and validated.
- Phase 2's `wskr_kitty` and `WSKR_PROTOCOL=kitty` use direct Kitty `f=100` PNG graphics with bounded Base64 framing, accepted by full hosted Linux/macOS tests and real Kitty screenshots of physical/virtual placement.
- The native image manager provides uploads, physical and virtual placements, scoped deletion, and an explicitly input-owned capability probe. The former external `kitty +kitten icat` transport is available as `kitty_legacy` for comparison.
- `RichPlot` and `RichImage` retain safe text fallbacks. Actual inline graphics are **not yet implemented**; protocol-level Unicode placeholder encoding is prepared for Phase 4.

**Limitations:** viewport fitting, debounced interactive redraw/resize, REPL/pandas integration and terminal-dependent contrast remain Phase 3 work. Ordinary static plots now persist at the prompt after Python exits; explicit figure closure and interactive teardown still clean up owned images. Rich virtual placeholder composition and ConsoleOptions sizing are Phase 4 work. `wskr_sixel` and `wskr_iterm2` remain unsupported stubs. See [STATUS.md](STATUS.md).

## Requirements and local installation

This repository declares **Python >=3.13,<3.15**, Matplotlib >=3.10.1 and the dependencies in [pyproject.toml](pyproject.toml). The Phase 2 native implementation requires a directly attached `xterm-kitty` TTY for output; it no longer invokes `kitty icat` for the primary display path. The legacy comparison transport still requires the `kitty` executable on PATH.

From a checkout:

```sh
uv sync
```

Run the installed development environment with `uv run` (or activate its environment). The `justfile` provides wskr-specific checks and smoke tests. See [Phase 2 qualification](docs/phase2-validation.md) for independently verified native Kitty behavior and known limitations.

## Terminal discovery (Phase 1, accepted)

Phase 1 introduced immutable `TerminalProfile` measurements and pure default styling, accepted and merged in PR #17. Kernel geometry is read from an attached terminal without escape sequences; unknown font, physical DPI and colors remain explicitly unavailable. Live OSC color interrogation requires **exclusive ownership of terminal input** and a callback that routes any unrelated bytes back to the application. Importing `wskr` no longer changes global Matplotlib `text.usetex`.

```python
from wskr.terminal import probe_profile
from wskr.render.matplotlib.theme import resolve_rc_defaults

profile = probe_profile()  # geometry only; no terminal escape queries
defaults = resolve_rc_defaults(profile)
print(profile.columns.value, profile.cell_width_px.source, defaults)
```

Only backend-owned **initial** figure defaults can use measured terminal dimensions. Display never changes figure size or DPI. `WSKR_SCALE` changes only the transmitted raster; opt-in `WSKR_FIT=contain` constrains that raster to the attached terminal's **measured pixel viewport** at each display. With unknown pixel geometry, no fit is attempted. Unattended automatic OSC color probing remains disabled without input ownership. **Fitted foreground `show(block=True)` sessions redraw automatically after stable window resizes**; background/nonblocking redraw and general placement remain Phase 3 work.

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

To **fit oversized plots to the currently measured Kitty pixel viewport**, without changing Matplotlib `figsize`, `dpi` or file exports:

```sh
WSKR_FIT=contain MPLBACKEND=wskr_kitty uv run python example.py
```

The default (unset `WSKR_FIT`) remains native-size output. Fit preserves aspect ratio and does not upscale by itself. If `WSKR_SCALE` is also set, it applies first and containment caps the resulting size. During an explicit foreground `plt.show(block=True)` session with `WSKR_FIT=contain`, window geometry is checked passively every 100 ms; redraw is debounced until the geometry has stabilized for 200 ms. No SIGWINCH handlers or terminal input modes are changed. In ordinary nonblocking usage, the viewport is remeasured only on subsequent application-initiated draws. A PNG fitting the viewport in pixel dimensions does not guarantee the terminal cursor is at the top or prevent existing scrollback from scrolling.

**Current behavior:** displaying a figure preserves its `figsize`/`dpi` and ordinary `savefig` outputs. Multiple managers survive `show()`, explicit `plt.close()` removes owned terminal images, and ordinary noninteractive Kitty plots remain in terminal history after Python exits. `show(block=None|False)` returns promptly; an explicit `plt.show(block=True)` requires foreground input and output on the **same Kitty TTY**, displays the figures on a temporary alternate screen, waits for Enter, and then restores the prior terminal contents and closes managed figures **without leaving image-sized blank rows**. The native Kitty canvas supports guarded interactive `draw_idle` uploads. Run `WSKR_SCALE=0.4 just visual-smoke matplotlib` for display scaling and persistence. Automatic resizing outside explicitly fitted blocking sessions, cursor-aware multi-figure placement, and richer REPL/pandas integration still require Phase 3 work.

## Using the current Rich adapter

```python
import matplotlib.pyplot as plt
from rich.console import Console
from wskr.render.rich.plt import RichPlot

fig, ax = plt.subplots()
ax.plot([0, 1, 2], [2, 3, 1])

Console().print(RichPlot(fig, desired_width=40, desired_height=10))
```

The current default protocol registry uses `noop` unless a transport is requested or configured. Without an image transport, `RichPlot` now displays a visible text fallback, not an image. Setting `WSKR_PROTOCOL=kitty` selects the direct native transport when a Kitty TTY is available. **Rich inline graphics remain unavailable** by design: the adapter still displays an explicit diagnostic instead of emitting unverified placeholders. The Phase 2 manager and placeholder encoder are prepared for Phase 4's actual Rich placement implementation. Do not use it for an unattended production dashboard yet.

## Extending transports

The current extension interface is `wskr.protocol.base.ImageProtocol`, registered by `wskr.protocol.registry.register_image_protocol(name, cls)`. It exposes `get_window_size_px()`, `send_image(png_bytes)` and `init_image(png_bytes)`, plus an optional `retain_display()` hook for terminal-history semantics. The registry can load entry points from `wskr.image_protocols`.

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

Phase 1 acceptance succeeded at `5e35aa6`: full `just check` (200 passed, 3 skipped), Phase 1 (55 passed, 1 skipped), PTY (35 passed), and live Kitty (5 passed). Phase 2 subsequently passed full hosted Linux/macOS validation (**229 passed, 3 skipped** on each) and focused Phase 2 suites (**54 passed** each), plus independently inspected real Kitty physical/virtual screenshots under Linux/Xvfb. See [Phase 2 acceptance](docs/phase2-validation.md).

Development should not be declared complete based on unit or simulated terminal tests alone. Real Kitty appearance, image placement, cleanup and resize/theme behavior have distinct acceptance criteria in [PLAN.md](PLAN.md).

## License

[GPL-3.0-only](LICENSE.md).
