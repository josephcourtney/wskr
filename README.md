# wskr

Terminal-native Matplotlib display using the Kitty graphics protocol, with transitional Rich renderables. [DESIGN.md](DESIGN.md) defines the target; [STATUS.md](STATUS.md) distinguishes verified behavior from unfinished requirements.

## Supported today

- Stock Matplotlib Agg-backed `wskr_kitty` backend, selected through `MPLBACKEND=wskr_kitty` or `module://wskr.render.matplotlib.kitty`. No special plotting API.
- Direct Kitty PNG transport (without `kitty icat`) with scoped image/placement IDs, replacement and explicit deletion. An attached `xterm-kitty` TTY is required.
- Provenance-aware kernel/CSI geometry, safe OSC and Kitty XTGETTCAP measurements (palette, foreground/background, font family/size, DPI and opacity) through an explicit input-owning client; scoped, figure-local appearance without changing `rcParams`. Unattended pyplot does not read shared terminal input.
- Preserved explicit figure dimensions/DPI and standard PNG/SVG `savefig` exports; display-only `WSKR_SCALE` and optional `WSKR_FIT=contain`.
- Nonblocking, terminal-history-resident static figures; explicit foreground `show(block=True)` with an alternate screen, Enter-to-close, fitted multi-figure contact sheets and `n`/`p` paging. Nonblocking figure redraws can be coordinated through an application-owned event pump.
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
plt.show(block=False)  # Explicitly retain the plot in terminal history
fig.savefig("chart.svg")
```

Alternatively, use `matplotlib.use("module://wskr.render.matplotlib.kitty")` before importing `pyplot`.

For an oversized figure, fit only the transmitted PNG, leaving figure geometry and exports untouched:

```sh
WSKR_FIT=contain MPLBACKEND=wskr_kitty uv run python example.py
```

`WSKR_SCALE` scales only terminal pixels and is applied before optional containment. Without `WSKR_FIT=contain`, the backend does not silently resize an explicitly sized figure. `show(block=None)` follows Matplotlib interactive-mode semantics: it blocks in a noninteractive foreground script with exclusive TTY access, and returns in interactive or unowned sessions. `show(block=False)` explicitly retains nonblocking history output. `show(block=True)` requires foreground stdin/stdout on the same Kitty TTY and closes managed images on dismissal.

When the application pumps `canvas.flush_events()` or `plt.pause()`, a fitted nonblocking figure can be redrawn following a stable resize. Interactive applications may opt into `WSKR_IDLE_REDRAW=coalesce` to queue repeated `draw_idle()` calls until the next event pump. A pump on one pyplot figure also drains pending backend-managed figures. The default remains immediate; this does not add an unattended REPL/IPython event loop. Nonblocking placement is **history-relative, not viewport-pinned**. The default physical parent can become obscured or overlap wrapped history under Kitty 0.49.2 despite correct PNG transmission. In a compatible Kitty, opt into `WSKR_KITTY_ANCHOR=unicode` to bind the image to a transparent Unicode-placeholder text cell; native macOS evidence supports selected 9×2/9×6 scrollback/reflow cases, but not a universal placement guarantee. For older Kitty without P/Q parent-relative placement, `WSKR_KITTY_PARENT=off` instead uses ordinary scoped physical placement. Neither mode provides unattended viewport pinning. See [placement semantics](docs/phase3-placement-semantics.md) and [native acceptance](docs/phase3-native-macos-acceptance.md).

## Cooperative IPython and REPL plots

A standard Python REPL can call `plt.pause()` or
`fig.canvas.flush_events()` after changing a figure. For IPython, an
**explicit, optional** host event hook drains queued updates after each
completed cell:

```sh
WSKR_FIT=contain WSKR_IDLE_REDRAW=coalesce MPLBACKEND=wskr_kitty ipython
```

```python
%load_ext wskr.render.matplotlib.ipython
import matplotlib.pyplot as plt
plt.ion()
fig, ax = plt.subplots()
line, = ax.plot([0, 1], [1, 0])
line.set_ydata([0, 1])
fig.canvas.draw_idle()
# After this cell: one cooperative redraw, no input polling or thread.
```

An installed pandas Matplotlib plot can participate in the same event pump.
Use `%unload_ext wskr.render.matplotlib.ipython` to remove the callback.
The extension does not install IPython or claim its input loop; it does not
repaint while the user is idle. Other interactive shells should call
`flush_events()` themselves. A truly *unowned* terminal cannot be queried
or asynchronously refreshed without host cooperation.

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
    # If an input-owning application has measured a new profile:
    # screen.refresh_theme(new_profile)  # backend-owned colors only
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

Known Kitty runtime font and DPI are **measurements**, not instructions to install fonts or substitute physical DPI for rasterization DPI. If the measured font is unavailable on the Python host, new figures use Matplotlib's installed monospace fallback. Re-running the probe and scoping a new profile gives *new figures* the current theme. An explicitly owned live viewport may call `refresh_theme(profile)` to update backend-owned figure/axes, title/axis/tick text, spines and grids; historical PNGs and explicitly styled artists are not automatically recolored. Explicit Matplotlib style and sizing values remain authoritative. A non-owning REPL cannot automatically interrogate OSC replies safely.

`RichPlot` and `RichImage` retain their historical imports under `wskr.render.rich`. Currently they display a diagnostic fallback for unavailable inline graphics, even with `WSKR_PROTOCOL=kitty`. Do not use them for image-bearing Rich panels or tables until Phase 4 is complete. The older `kitty_legacy` comparison implementation requires a Kitty executable and is not the supported primary transport.

## Verification and project documents

```sh
just check           # syntax, formatting, Ruff, ty, pytest
just phase1          # terminal-profile and query tests
just phase2          # graphics-protocol tests
just phase3          # Matplotlib and screenshot-evidence tests
just test-native-gui # opt-in automated native macOS owned-viewport matrix
```

Experimental unattended native GUI testing is available with `just native-auto unmanaged resize 2` or `just native-auto-matrix`: a separate controller creates an isolated yabai space and Kitty window, verifies unmanaged/floating/BSP state, drives resize and paging input and captures the specific window without selection dialogs. It requires native macOS, yabai space-creation capability and Screen Recording access; **automated native GUI results remain unqualified** pending a real run and screenshot review. See [native automation](docs/phase3-native-yabai-automation.md).

Native macOS Kitty also has **manual, opt-in** evidence recipes: `just native-resize-history unmanaged 2 96` (scrollback/reflow), `just native-lifecycle unmanaged` (two-figure redraw and close), `just native-paging unmanaged` (foreground `n`/`p`/Enter and resize), `just native-paging-capacity unmanaged` (must cross a page-capacity boundary), and `just native-appearance unmanaged` (owned dark→light query/contrast screenshots). These tests may **erase the disposable test window's screen and scrollback** and request selected-window screenshots; do not run them in a terminal containing history you wish to retain.

Installed-wheel backend selection, PNG/SVG exports, hosted Kitty graphics and multiple native macOS scenarios have been qualified separately. The eight-stage native blocking-paging run confirms navigation, fitted raster resizing and primary-screen restoration, but not a change in page capacity. Native screenshot colors are converted from their embedded ICC display profile to sRGB **for acceptance checks only**; rendering and transmitted pixels are unchanged. See [current status](STATUS.md), [P3 evidence](docs/phase3-native-macos-acceptance.md) and [P3 lifecycle evidence](docs/phase3-lifecycle-acceptance-20261101.md).

Documentation roles follow [POLICY.md](POLICY.md): [DESIGN](DESIGN.md) records stable requirements, [PLAN](PLAN.md) execution strategy, [STATUS](STATUS.md) the current handoff, [TODO](TODO.md) pending work, [CHANGELOG](CHANGELOG.md) completed changes and [ADRs](docs/adr/) decisions.

License: [GPL-3.0-only](LICENSE.md).
