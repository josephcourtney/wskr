# wskr

Terminal-native Matplotlib display using the Kitty graphics protocol, with transitional Rich renderables. [DESIGN.md](DESIGN.md) defines the target; [STATUS.md](STATUS.md) distinguishes verified behavior from unfinished requirements.

## Supported today

- Stock Matplotlib Agg-backed `wskr_kitty` backend, selected through `MPLBACKEND=wskr_kitty` or `module://wskr.render.matplotlib.kitty`. No special plotting API.
- Direct Kitty PNG transport (without `kitty icat`) with scoped image/placement IDs, replacement and explicit deletion. An attached `xterm-kitty` TTY is required.
- Provenance-aware kernel/CSI geometry, safe OSC and Kitty XTGETTCAP measurements (palette, foreground/background, font family/size, DPI and opacity) through an explicit input-owning client; scoped, figure-local appearance without changing `rcParams`. Unattended pyplot does not read shared terminal input.
- Preserved explicit figure dimensions/DPI and standard PNG/SVG `savefig` exports; display-only `WSKR_SCALE` and optional `WSKR_FIT=contain`.
- Nonblocking, terminal-history-resident static figures; explicit foreground `show(block=True)` with an alternate screen, Enter-to-close, fitted multi-figure contact sheets and `n`/`p` paging.
- Explicit `owned_viewport(fig)` for an application with exclusive foreground terminal ownership, application-driven `refresh()` and `poll_resize()`, and previous-screen restoration on exit.

**Not yet supported end-to-end:** unattended theme-change recoloring of existing figures, unattended IPython/REPL redraw, viewport-pinned *nonblocking history* images, arbitrary independent placement, Rich inline Kitty panels/tables, and iTerm2/Sixel graphics. Rich names currently return visible diagnostics, not inline images. See [TODO.md](TODO.md).

## Installation and backend selection

Requires Python >=3.13,<3.15 and Matplotlib >=3.10.1; use `uv sync` in a checkout.

```sh
uv sync
MPLBACKEND=wskr_kitty uv run python example.py
```

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([0, 1, 2], [3, 1, 4])
plt.show()  # Nonblocking, intentionally persistent in terminal history
fig.savefig("chart.svg")
```

Alternatively, use `matplotlib.use("module://wskr.render.matplotlib.kitty")` before importing `pyplot`.

For an oversized figure, fit only the transmitted PNG, leaving figure geometry and exports untouched:

```sh
WSKR_FIT=contain MPLBACKEND=wskr_kitty uv run python example.py
```

`WSKR_SCALE` scales only terminal pixels and is applied before optional containment. Without `WSKR_FIT=contain`, the backend does not silently resize an explicitly sized figure. `show(block=None|False)` returns without claiming keyboard input; `show(block=True)` requires foreground stdin/stdout on the same Kitty TTY and closes its managed images when dismissed.

When the application pumps `canvas.flush_events()` or `plt.pause()`, a fitted nonblocking figure can be redrawn following a stable resize. Interactive applications may opt into `WSKR_IDLE_REDRAW=coalesce` to queue repeated `draw_idle()` calls until the next event pump; the default remains immediate. The placement stays attached to its *original scrollback anchor*, not the current viewport. Under Kitty 0.49.2, native experiments with 96 wrapped history lines showed a fitted redraw can be off-screen after shrinking even though upload and placement succeeded. See [placement semantics](docs/phase3-placement-semantics.md).

## Foreground-owned live viewport

```python
import matplotlib.pyplot as plt
from wskr.render.matplotlib.live import owned_viewport

fig, ax = plt.subplots()
line, = ax.plot([0, 1, 2], [0, 1, 0])

with owned_viewport(fig) as screen:
    line.set_ydata([0, 0.5, 0])
    screen.refresh()
    screen.poll_resize()  # call repeatedly from your own event loop
```

Use `WSKR_FIT=contain MPLBACKEND=wskr_kitty` in a foreground Kitty process; do not enter this mode from a REPL that owns the terminal. It does not read stdin or create a background event loop, and its images do not persist after the session. [Native macOS acceptance](docs/phase3-owned-live-automated-acceptance.md) covers unmanaged Kitty, yabai floating and genuine vertical BSP, with both short and tall figures.

## Terminal profile and Rich status

```python
from wskr.terminal import probe_profile
from wskr.render.matplotlib.theme import resolve_rc_defaults

profile = probe_profile()  # geometry; no escape queries by default
defaults = resolve_rc_defaults(profile)
```

An application that owns *foreground stdin and stdout on the same TTY* may collect the live terminal appearance and scope it to normal pyplot creation:

```python
from wskr.terminal import probe_owned_profile, use_profile

input_queue = bytearray()  # replace with application's input dispatcher
# This example belongs in an application's own foreground terminal event loop.
# Feed unrelated reply bytes back to its actual input queue.
profile = probe_owned_profile(owns_input=True, on_unmatched=input_queue.extend)
with use_profile(profile):
    fig, ax = plt.subplots()  # regular Matplotlib APIs
    ax.plot([0, 1], [1, 2])
```

`input_queue` is an application-owned input buffer, not a provided wskr global. `probe_owned_profile` rejects redirected/background/mismatched TTYs and never runs implicitly. For tests or applications with an existing terminal query dispatcher, `probe_profile(color_query=..., geometry_query=..., kitty_query=...)` accepts bounded input-owner callbacks. The public query helpers are `query_osc`, `query_csi`, and `query_kitty_field` from `wskr.terminal.query`.

Known Kitty runtime font and DPI are **measurements**, not instructions to install fonts or substitute physical DPI for rasterization DPI. If the measured font is unavailable on the Python host, new figures use Matplotlib's installed monospace fallback. Re-running the probe and scoping a new profile gives *new figures* the current theme; already-rendered figures are not recolored, nor are custom artist colors overridden. Explicit Matplotlib style and sizing values remain authoritative. A non-owning REPL cannot automatically interrogate OSC replies safely.

`RichPlot` and `RichImage` retain their historical imports under `wskr.render.rich`. Currently they display a diagnostic fallback for unavailable inline graphics, even with `WSKR_PROTOCOL=kitty`. Do not use them for image-bearing Rich panels or tables until Phase 4 is complete. The older `kitty_legacy` comparison implementation requires a Kitty executable and is not the supported primary transport.

## Verification and project documents

```sh
just check             # syntax, Ruff, ty, pytest
just phase1           # terminal-profile and query tests
just phase2           # protocol tests
just phase3           # Matplotlib lifecycle tests
just test-native-gui  # native macOS: isolated Kitty/yabai acceptance matrix
```

The supported wheel selection and PNG/SVG exports are qualified separately from real Kitty graphics. P1 completion [PR #45](https://github.com/josephcourtney/wskr/pull/45) passed **372 tests, 3 skipped** per platform on Ubuntu and macOS; installed-wheel selection/exports and hosted real-Kitty graphical regressions also passed. The new Kitty XTGETTCAP appearance reads have PTY/mock validation but not yet independent native macOS graphical qualification. [PR #43](https://github.com/josephcourtney/wskr/pull/43) records six independently reviewed native macOS owned-viewport scenarios; this does not qualify history-anchored output. See [Phase 2 evidence](docs/phase2-validation.md), [Phase 3 evidence](docs/phase3-validation.md), and the [native acceptance guide](docs/phase3-owned-live-automated-acceptance.md).

Project roles follow [POLICY.md](POLICY.md): [DESIGN](DESIGN.md) contains stable requirements, [PLAN](PLAN.md) execution strategy, [STATUS](STATUS.md) current handoff, [TODO](TODO.md) immediate work, [CHANGELOG](CHANGELOG.md) completed user-visible changes, and [ADRs](docs/adr/) architectural rationale.

License: [GPL-3.0-only](LICENSE.md).
