# DESIGN.md — Terminal-native Matplotlib and Rich rendering for wskr

> **Status:** Proposed target architecture and implementation contract  
> **Date:** 2026-10-19  
> **Repository:** [josephcourtney/wskr](https://github.com/josephcourtney/wskr)  
> **Scope:** Consolidation and replacement of the existing rendering internals; this document does **not** assert that the target features are already implemented.

## 1. Executive decision

`wskr` is the canonical project. It becomes a compact, reliable, terminal-aware Matplotlib backend with an optional Rich adapter. **Kitty is the first fully supported graphics transport.** Future terminal protocols may use the same internal interfaces, but stubs must never be advertised as working integrations.

Preserve these strengths:

- From existing **wskr**: distinct terminal I/O, graphics protocol, Matplotlib, and Rich layers; protocol registry; Unicode-placeholder image embedding; and automated terminal/screenshot-test infrastructure.
- From **mplkitty v0.2.0** (the standalone prototype developed in the October 2026 discussions): terminal pixel/cell measurements; live foreground/background and ANSI-palette queries; font, DPI and opacity discovery; computed Matplotlib defaults; theme-sensitive rendering; PNG transmission without depending on an external `kitty` binary; and live redraw on geometry/theme changes.
- From [jktr/matplotlib-backend-kitty](https://github.com/jktr/matplotlib-backend-kitty): an intentionally small Agg-derived backend, standard backend selection, ordinary `plt.show()`, and automatic display in interactive Python and pandas plotting workflows.
- From [josephcourtney/jkit](https://github.com/josephcourtney/jkit): the principle that GridSpec composition, custom subplot sharing, scatter-density computation, and domain-specific chart semantics belong in **plotting utilities above the backend**, not in its image transport.

**Primary user contract:** existing Matplotlib code remains ordinary Matplotlib code. Selecting a backend is the only mandatory integration step; no parallel `wskr.plot()`, `wskr.subplots()`, `wskr.show()`, special figure units, or separate graph-description language is required.

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([0, 1, 2], [3, 1, 4])
ax.set(title="Activity", xlabel="Time")
plt.show()
```

```sh
export MPLBACKEND=wskr_kitty
python example.py
```

Equivalently, use the documented module form `MPLBACKEND=module://wskr.render.matplotlib.kitty`. Named backend registration must use the Matplotlib-supported backend entry-point group; the module form is the compatibility fallback.

## 2. Scope, requirements, and non-goals

### 2.1 Goals

1. **Stock Matplotlib semantics:** support pyplot, `Figure`/`Axes`, pandas `.plot()`, normal rcParams/styles, `plt.ion()`, `plt.ioff()`, `draw_idle()`, `plt.show(block=...)`, `Figure.savefig()`, and multiple figures without requiring wskr-specific calls.
2. **Environment as the default:** infer size, foreground/background, ANSI palette, dark/light appearance, font metrics, and graphics capability from the **currently running terminal**, not from assumptions about the host, display, or `kitty.conf`.
3. **Respect intent:** explicit Matplotlib styles, colors, dimensions, DPI, typography, and save/export operations take precedence over terminal-derived defaults.
4. **Pixel-accurate output:** render to the intended pixel buffer for the chosen terminal-cell allocation; avoid arbitrary image rescaling and hardcoded monitor DPI.
5. **Theme-native appearance:** match the terminal's effective background and foreground and derive readable accent, grid, and annotation colors. Adapt new renders to terminal theme changes.
6. **Correct Kitty protocol:** directly transmit standards-compliant PNG/RGBA graphics with image/placement IDs, chunking, replacement, deletion, and optional Unicode placeholders.
7. **Rich composability:** embed images in Rich layouts via a narrowly scoped optional adapter sharing the Kitty graphics layer.
8. **Safety and graceful degradation:** terminal probing must be bounded and must never corrupt redirected output, silently eat arbitrary user input, leave terminal modes altered, or claim a graphic was displayed when it was not.
9. **Measurability:** tests must separately prove Matplotlib behavior, query/parser behavior, graphics serialization, pseudo-terminal behavior, and real Kitty rendering.

### 2.2 Non-goals

- Reimplementing Matplotlib's renderer, rasterizer, transforms, artists, or layout engine. Use `FigureCanvasAgg` for terminal rasterization and Matplotlib's normal file exporters.
- Choosing plot types, aggregation windows, tick semantics, or which metrics belong in an application dashboard. A seven-day dataset with one meaningful observation should be reduced by the **application**, not by the backend.
- Moving `jkit.plot.make_plot_grid`, density-scatter routines, or other semantic plotting helpers into wskr.
- Requiring Kitty remote-control permission, `kitty @`, `kitty +kitten icat`, a running compositor API, `yabai`, SciPy, NumPy as an *additional explicit direct* dependency when already transitively supplied by Matplotlib, or Rich for basic Matplotlib output.
- Claiming iTerm2 or Sixel support based solely on protocol registration or placeholder classes. Add them only after independent implementations and end-to-end validation.
- Guaranteeing retroactive recoloring of arbitrary user-authored artists, arbitrary third-party artists, or explicit colors; Matplotlib does not provide universal style provenance.
- Promising GUI-grade mouse navigation, interactive toolbar widgets, or real-time animation as part of the initial acceptance contract.

### 2.3 Requirement vocabulary

- **MUST / MUST NOT:** required for acceptance.
- **SHOULD:** expected unless a documented compatibility or safety reason prevents it.
- **MAY:** optional or future capability.
- A capability is **implemented** only when both implementation and appropriate tests exist. A documented or prototyped capability is not considered shipped.

## 3. Architectural boundaries

```text
Matplotlib / pandas / pyplot           Optional Rich application
              |                                   |
       Standard backend API                     RichPlot/RichImage
              |                                   |
  wskr.render.matplotlib.*                wskr.render.rich.*
              |                                   |
       FigureCanvasAgg                            |
              +---------- Rendering service ------+
                            |
           TerminalProfile + style resolver
                            |
              Graphics image/placement manager
                            |
           ImageProtocol / Kitty direct transport
                            |
         Safe terminal session + query/response I/O
                            |
                       Kitty TTY
```

The modules are separated by responsibility rather than by terminal brand:

| Package area | Owns | MUST NOT own |
| --- | --- | --- |
| `wskr.terminal` | TTY access, session locking, query parsing, metrics, colors, capability profiles | Matplotlib figures or Rich objects |
| `wskr.protocol` | Image encoding, feature negotiation, image identity, transmission, placement/deletion | Figure styling, axis layout, plot semantics |
| `wskr.render.matplotlib` | Standard Matplotlib backend lifecycle, Agg canvas, creation-time defaults, terminal display policies | Kitty-specific parsing, application-specific plots |
| `wskr.render.rich` | Rich measurement, rendering into allocated cells, Unicode placeholders | Independent duplicate Kitty encoder or separate figure-sizing rules |
| `wskr.core` | Small explicit configuration, typed errors, debug diagnostics | Global style changes on package import |

A shared `TerminalProfile` is **data**, not a singleton requiring access to a live TTY at import time. Each observation records its origin (measured/query/inferred/override/fallback), so diagnostics can distinguish facts from guesses. Prefer frozen typed dataclasses or equivalent stable value objects.

Suggested public/internal conceptual types (exact Python names are not mandatory):

```python
@dataclass(frozen=True)
class TerminalProfile:
    columns: int
    rows: int
    window_width_px: int | None
    window_height_px: int | None
    cell_width_px: float | None
    cell_height_px: float | None
    foreground: str | None
    background: str | None
    ansi_palette: tuple[str | None, ...]
    font_family: str | None
    font_size_pt: float | None
    dpi_x: float | None
    dpi_y: float | None
    background_opacity: float | None
    graphics: frozenset[str]
    provenance: Mapping[str, str]
```

Unknown measurements remain `None`; never represent an unknown capability as measured. Keep protocol availability distinct from a mere `TERM` string or installed `kitty` executable.

## 4. Matplotlib public API and lifecycle

### 4.1 Backend registration and selection

- Retain `wskr_kitty` as the primary named backend for compatibility, registered via `[project.entry-points."matplotlib.backend"]` (singular, as supported by Matplotlib), plus the explicit module URI.
- A generic `wskr` backend MAY negotiate a supported protocol only after detection succeeds; `wskr_kitty` must not silently switch to another transport.
- Keep old module import paths or aliases for existing users where cheap and safe. Deprecate them with one actionable warning rather than immediate breaking deletion.
- Verify compatibility with the supported Matplotlib version range. Use current documented `FigureCanvasBase` / `FigureManagerBase` interfaces rather than relying on incidental private imports when a public entry point exists.
- No package-import side effects: importing `wskr`, its protocol classes, or its backend module MUST NOT query a terminal, invoke Kitty, enable `text.usetex=False`, change `plt.style`, force interactive mode, or modify rcParams outside the documented backend initialization lifecycle.

### 4.2 Figure creation and defaults

The backend MUST have an initialization point **before** a default figure is constructed, so measured terminal defaults can affect default `figure.figsize`, font sizes, colors, and style cycle without repainting unrelated figures.

Use backend figure-manager/canvas creation hooks, with Matplotlib-supported APIs. Avoid monkeypatching `pyplot.subplots` or replacing public Figure classes. Scoped creation-time defaults are preferable to irreversible global `rcParams` edits.

The implementation MUST preserve:

- `plt.subplots(figsize=(8, 3), dpi=150)` and `plt.figure(figsize=...)` as explicit user instructions.
- `plt.style.use(...)` and `matplotlibrc` user overrides.
- Per-artist parameters such as `color=`, `linewidth=`, `markersize=`, `fontsize=`, `facecolor=`.
- `Figure.savefig("plot.png", dpi=...)`, `fig.savefig("plot.svg")`, and other supported Matplotlib output paths without transmitting terminal graphics or changing saved dimensions unexpectedly.
- All live figures, not only `Gcf.get_active()`. Never destroy all figure managers implicitly as a side effect of showing one.

**Important provenance limitation:** Matplotlib does not reliably record whether a user explicitly set an rcParam to the exact same value as its existing default. The backend MUST NOT claim perfect provenance. Track which values it installs as backend defaults and which specific figure properties it later owns. Ambiguous values are treated as user-owned rather than overwritten automatically.

### 4.3 `show`, interactive sessions, and redraw

Use standard `plt.show(block=None | True | False)`:

- `block=None` follows Matplotlib interactive-mode expectations: block in ordinary non-interactive sessions, do not block in interactive mode, subject to supported environment constraints.
- `block=False` requests one initial display and returns; it MUST NOT consume terminal input or permanently take over the screen.
- `block=True` MAY open a managed terminal view for figure updates and a bounded input loop. Document the controls (`q`, `Esc`, Ctrl-C) and restore the previous terminal screen/modes/handlers on normal exit and exceptions.
- `plt.ion()`, IPython/REPL, and pandas plotting MUST display newly drawn or stale figures through standard redraw/idle hooks. No application-level `wskr.show()` call is required.
- A canvas must guard against reentrant draw cycles. `draw_idle` SHOULD coalesce repeated changes; it MUST NOT recursively invoke full `show()` or repeatedly retransmit an incomplete figure.
- Multiple open figures must retain independent canvas/manager state, IDs, and cleanup. Figure close/destroy must release owned graphics.
- Default one-shot CLI output MUST avoid creating unbounded scrollback or repeated redundant frames. Interactive managed views must update placements rather than continually appending new images.

Matplotlib keyboard/mouse events are handled only to the extent a terminal supplies reliable input. A minimal redraw/quit interactive view is **not** represented as a full GUI backend.

## 5. Terminal discovery and safe TTY handling

### 5.1 Probe order

A terminal probe has a per-render or per-refresh budget and follows this order:

1. Check whether the intended graphics output destination is a usable TTY. A redirected stream, pipe, file, notebook capture, or headless test is **not** proof of an attached graphics terminal.
2. Query `TIOCGWINSZ` for rows/columns and any nonzero pixel geometry.
3. Ask for missing geometry with `CSI 14 t` (window pixels) and `CSI 16 t` (cell pixels) if safe and supported. Derive cell geometry from window pixels and grid dimensions only when necessary.
4. Prefer actual terminal `OSC 10` (foreground) and `OSC 11` (background), or Kitty's extended current-color query where supported. Query needed `OSC 4` palette entries; do not require reading all 256 entries on every plot.
5. Optionally query Kitty's terminal capabilities for current font family/PostScript name, font size, horizontal and vertical DPI, foreground/background and background opacity. Unsupported capability values remain unknown.
6. Negotiate the Kitty graphics protocol separately from theme/geometry hints.
7. Cache the resulting profile for one rendering transaction. For long-running sessions invalidate relevant values upon resize/theme changes or periodic bounded re-probe.

Use runtime queries instead of reading `kitty.conf`. Runtime color changes, Kitty auto-dark/light themes, custom palettes, and remote sessions can differ from configuration files.

`TERM`, `COLORTERM`, `KITTY_WINDOW_ID`, `COLORFGBG`, and other environment values MAY narrow probing and support fallbacks; none alone establishes graphics support. A host machine's macOS dark-mode setting is likewise not an authoritative description of Kitty's active color scheme.

### 5.2 Query safety contract

The existing `wskr.terminal.io` abstraction is the starting point, but query correctness and ownership must be tightened:

- Open/retain **one** appropriate TTY handle for each atomic query transaction where possible; close precisely once.
- Synchronize TTY queries and graphics responses with a process-local lock. Interleaved concurrent readers/writers are unsupported unless mediated by an explicit response dispatcher.
- Apply bounded monotonic deadlines and maximum response sizes; parse `BEL` and `ESC \` terminators and specific expected response types. Avoid accepting an unrelated terminal response as the result of another query.
- Save and restore terminal attributes (`termios`, echo/canonical settings), screen state, cursor visibility, signal handlers, and temporary resources in `finally` paths.
- Probe only when terminal ownership is sufficiently safe. In contexts where a parent application, shell, curses/TUI, or another library owns keyboard input, choose cached metrics, a cooperating host API, or conservative defaults rather than stealing input.
- Do not drain or flush arbitrary pending keystrokes. Unmatched response/input bytes SHOULD be retained for a cooperating input dispatcher where one is available; otherwise avoid unsafe active querying.
- A PTY may be present without Kitty graphics support. Query failures are diagnostic, not fatal to ordinary `savefig`.
- Under tmux, screen, SSH, and other intermediaries, use protocol passthrough only when identified as safe; otherwise report unavailable and fall back without emitting raw escape codes.
- If no safe device is available, all probe calls return an unknown/fallback profile rather than raising `termios.error: (9, 'Bad file descriptor')`.

In a non-TTY context `plt.show()` MUST NOT emit escape sequences into redirected output; it must give a clear, configurable diagnostic or explicit no-display result. A silent successful no-op is forbidden.

### 5.3 Detection provenance and refresh

Each profile value is tagged `measured`, `queried`, `inferred`, `configured`, or `fallback`. Expose a small optional diagnostic command/function showing the effective values, origins, and unavailable probes; never output escape sequences or private terminal input in diagnostics.

No hardcoded monitor model, MacBook DPI, three-line REPL prompt height, or default `800×600` pixel value is to be used as though it were measured. Fallback geometries may be employed **only** with explicit fallback provenance.

## 6. Terminal-derived styles, light/dark mode, and precedence

### 6.1 Theme choice

The visible terminal's effective background and foreground are the source of truth. Theme resolution priority is:

1. Explicit application/user styling and any explicit `wskr` theme override.
2. Queried actual terminal background/foreground (and current ANSI palette).
3. A trustworthy terminal-reported color-scheme capability, if available.
4. `COLORFGBG` or similar environmental hints.
5. Optional operating-system appearance detection (`darkdetect` or platform facility) only as a fallback.
6. Documented conservative fallback colors.

Classify appearance using perceptual/relative luminance of the **actual background**, accounting for sRGB conversion; do not treat color-index ordering or the OS preference as stronger evidence. Crucially, a successful "light" detection is a result, not a failure: strategy chaining stops at the first **valid boolean**, not the first `True`.

The style should derive:

- Transparent figure/axes backgrounds when supported and safe; an opaque fallback uses the queried background.
- Text, tick labels, and annotations from the terminal foreground.
- Muted axes/spines and low-emphasis grids from foreground/background blends.
- A default color cycle from queried terminal ANSI colors, adjusted or filtered for contrast and distinguishability; do not assume ANSI blue/red are legible on all themes.
- Explicit contrast thresholds and colorblind-conscious differentiation for default plot series; line style and marker shape may complement color.

Avoid hardcoded dark navy/cyan/orange theme branding. Do not globally call `plt.style.use("dark_background")` at import time.

### 6.2 Explicit styles versus inherited styles

Precedence: **explicit artist/figure parameters > explicit user rcParams and styles > backend-installed defaults > inferred profile > library fallbacks**.

The backend must compute its style before new artists are created. It must not recolor user-owned artists just because a color equals a previously inferred default. Track backend-owned defaults and artist/figure state when possible. On ambiguity, favor preserving the user's choice and describe the limitation in documentation.

For a theme change:

- **New figures** use the latest effective profile.
- **Live figures** refresh all components known to be backend-owned and preserve confirmed overrides.
- **Explicit colors, colormaps, facecolors, transparency, and artist styles** remain unchanged.
- Figures in ordinary scrollback are static until deliberately rerendered. Do not promise automatic recoloring of historical raster images.
- Palette-indexed Kitty image formats (`f=8` / `f=16`) MAY be added behind capability detection for suitable images, but default true-color rendering remains required for gradients, arbitrary colormaps, and antialiasing.

### 6.3 Fonts

Kitty's queried PostScript font family/name and point size are hints, not proof that the remote Python process has that font installed. Matplotlib must resolve a locally available font, preferably a matching monospace family. If unavailable, fall back to a bundled/system monospace preference without shipping proprietary fonts.

Derive label/tick/title sizing from measured cell height or reported font metrics. Use Matplotlib's existing relative font names (`small`, `medium`, `large`, etc.) with a coherent base `font.size`. Use suitable stroke/marker/spacing scale factors via normal `rcParams`. Keep labels legible rather than compressing all typography to fit an allocated space.

## 7. Figure geometry, DPI, and scaling

### 7.1 Separate three concepts

1. **Extent:** how many terminal columns/rows or pixels the image is allocated.
2. **Style scale:** relative typography, strokes, markers and spacing inside that extent.
3. **Density:** formatting/tick/layout compactness; an application may choose it, but the backend does not infer data semantics.

No new public physical-size unit is required. Internally compute defaults in cells and convert to inches for Matplotlib. Once defaults are installed, ordinary `figsize=`, `dpi=`, `fontsize=` and other Matplotlib options remain the public overrides.

### 7.2 Pixel calculation

For measured cell width `cw` and height `ch` in pixels, and allocated `C` columns and `R` rows:

```text
target_width_px  = round(C * cw)
target_height_px = round(R * ch)
figure_width_in  = target_width_px  / render_dpi
figure_height_in = target_height_px / render_dpi
```

`render_dpi` is a rasterization/conversion scale and is **not** the display's physical DPI. Terminal physical DPI is useful for typography estimates where reliable, not necessary for the final pixel-exact PNG dimensions.

For missing pixel geometry, infer conservatively and mark the result. For renderers with explicit cell placement, never assert pixel exactness when the cell dimensions are merely assumed.

### 7.3 Sensible default allocation

New default figures SHOULD occupy most—but not all—of the available terminal width and a **bounded fraction** of its height. They must not assume every plot should fill the viewport.

Initial deterministic policy to implement/test (tunable through ordinary backend configuration, not a new pyplot signature):

- Reserve at least one column margin on each side and space for a subsequent shell prompt.
- Default to roughly 90% of the available columns.
- Default height to approximately one-third of the usable rows, capped by a compact terminal-native physical aspect ratio and by available rows; enforce a small minimum only when the terminal is tall enough.
- Multi-subplot figures MAY request more height when backend ownership of default sizing is known, subject to viewport limits.
- For narrow or short terminals, reduce decoration and keep fonts readable before shrinking text indiscriminately; allow scrolling or explicit dimensions when a chart cannot fit.

These are *presentation defaults*, not rules about the data being plotted. Never draw 16 or 20 terminal rows solely because the renderer previously reserved that much space.

### 7.4 Respecting explicit dimensions

- An explicit `figsize=(w, h)` or `fig.set_size_inches()` is authoritative; DO NOT resize the figure itself to the terminal at `show()`.
- User-specified `dpi` is authoritative for the figure's rasterization; terminal placement may scale an oversized buffer to fit **only** according to a clearly documented display policy. Do not mutate figure DPI merely to resize placement.
- `fig.savefig()` MUST preserve requested output dimensions and format. Terminal auto-sizing must not leak into ordinary exports of explicitly sized figures.
- Backend-owned default-sized figures MAY be recomputed on live terminal resize, but only those figures; user-sized figures retain their geometry.
- Avoid treating equality to a default rcParam as reliable proof that a value was not set explicitly.

### 7.5 Dynamic redraw

Long-running terminal views compare geometry/theme fingerprint values and issue redraws when relevant values change. Prefer `SIGWINCH` notification where safe, with a low-frequency bounded polling fallback for theme changes. Debounce repeated signals; never block a normal draw waiting for multiple expensive queries.

A resize redraw updates the **existing** managed graphics placement. A terminal theme change updates backend-owned styling, re-rasterizes, and replaces the placement without leaving a trail of previous frames in scrollback.

## 8. Kitty graphics transport and placement lifecycle

### 8.1 Primary transfer mechanism

Use a native direct Kitty graphics implementation, without requiring the `kitty` executable. Encoding must follow the official [Kitty graphics protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/):

- PNG is `f=100`; raw 24-bit RGB is `f=24`; raw 32-bit RGBA is `f=32`. Do **not** transmit PNG bytes while claiming `f=32`.
- Escape-coded payload data MUST be Base64-encoded before transmission.
- Chunk encoded data into payloads no larger than 4096 bytes; nonfinal chunks must have lengths divisible by four. Set `m=1` for continuing chunks and `m=0` for the final chunk.
- Apply complete control parameters to the first chunk; subsequent chunks may use the minimum continuation parameters.
- Encode image transmission, image ID/number, action, placement, and quiet/acknowledgment settings correctly and independently.
- Write binary-safe protocol bytes directly to the intended TTY output handle. Do not print escape codes through Rich text formatting or redirected stdout.

Probe support first. Tests MUST parse emitted commands and reconstruct the transmitted payload byte-for-byte. Do not infer success from the existence of `KITTY_WINDOW_ID` or availability of `kitty +kitten icat`.

### 8.2 Identity and lifecycle

Model image **identity** separately from image **placement**:

- Assign deterministic, collision-conscious positive IDs scoped to the rendering session.
- Upload once when content is unchanged; reuse the referenced image where supported.
- Create a placement for ordinary inline output and track its occupied cells and cursor policy.
- Update/recreate the existing managed placement on redraw, deleting old content/placement only when necessary.
- Implement explicit cleanup on `FigureManager.destroy()`, terminal-session end, layout replacement, and failures. Do not delete images owned by another process.
- Define response/ack modes: query only when the client can safely read acknowledgments; use quiet modes when embedded inside applications that cannot receive reply escapes.
- Bound memory, retained images, and transfer sizes. Prefer compressed PNG first; raw RGBA MAY be selected later on measured performance grounds.

One-shot displays should advance the cursor predictably and leave enough space for the shell prompt without relying on a fixed number of rows. Blocking live views may use an alternate screen but must restore it even on interruption.

### 8.3 Unicode-placeholder placement for Rich

Retain the useful idea in `wskr.render.rich.img`, but implement the [Kitty Unicode placeholder protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/#unicode-placeholders) precisely:

1. Transmit the image in quiet mode and create a **virtual** placement (`U=1`) for the intended cell rectangle.
2. Emit `U+10EEEE` placeholder cells with the specified combining row/column diacritics.
3. Encode image identity and, when necessary, placement identity via terminal color attributes per protocol.
4. Let Rich's layout place and move those Unicode cells. Underlying terminal rendering then follows scrolling, wrapping, and repositioning of text.
5. Bound row/column values and verify image-ID decoding, clipping, wrapping, and cleanup; do not misuse ANSI foreground-index values as a general integer field without the required high-order encoding.

Real placements and placeholder-based virtual placements have different deletion semantics. Rich's Unicode placeholders must not be treated as controllable ordinary physical placements.

The backend should not require a virtual Rich placeholder in a normal one-shot Matplotlib figure; choose the appropriate placement policy for the host.

### 8.4 Terminal multiplexer and unsupported terminal behavior

Kitty graphics may be supported through a compatible emulator or multiplexer, but detection must be by capability negotiation where safe. Unsupported transports produce an explicit `TransportUnavailableError` or a clearly documented non-graphical fallback selected by the caller. The existing `NoOpProtocol` MAY remain as a test/explicitly requested sink, but must never masquerade as a successful live render.

`kitty icat` can remain an optional diagnostic comparison or emergency adapter, not a mandatory runtime dependency or transport of first resort.

## 9. Rich integration

`wskr.render.rich` is an **optional extra** (`pip install "wskr[rich]"`), with lazy imports and no Rich dependency for basic pyplot use.

Target behavior:

```python
from rich.console import Console
from wskr.render.rich.plt import RichPlot
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([0, 1, 2], [2, 3, 1])
Console().print(RichPlot(fig, desired_width=40, desired_height=10))
```

Retain recognizable `RichPlot` and `RichImage` classes for compatibility, but simplify their internals:

- `__rich_measure__` reports allocated terminal-cell width consistently with Rich's `ConsoleOptions`, including nested tables/panels.
- `__rich_console__` asks the shared graphics manager to upload the image and yields correct placeholder cells. It never maintains a separate PNG framing implementation.
- Honor host-provided width/height allocations; when absent, use compact measured terminal defaults.
- Render once per changed layout/image fingerprint rather than uploading on every Rich measurement/render call.
- No hardware-specific DPI constants, no `lru_cache(maxsize=1)` that permanently freezes terminal size, and no independent default 800×600 geometry.
- Non-Kitty or redirected Rich output uses a visible, ordinary-text placeholder/alternative supplied by the application rather than raw escape bytes.
- Rich content remains composable within tables, side-by-side layouts, and terminal scrollback; images must follow host text layout as far as Kitty's placeholder protocol permits.

The Rich adapter may expose extra Rich-specific sizing arguments; this is **not** a new Matplotlib plotting API.

## 10. Configuration and dependency policy

### 10.1 Existing configuration first

Use established Matplotlib controls for ordinary users:

| User objective | Interface |
| --- | --- |
| Select backend | `MPLBACKEND=wskr_kitty`, `matplotlib.use("wskr_kitty")`, or `module://...` |
| Explicit figure dimensions | `figsize=(width, height)` |
| Explicit rendering DPI | `dpi=...`, `savefig(dpi=...)` |
| Font and text sizes | `rcParams`, `fontsize=`, named relative font sizes |
| Colors/colormaps | `plt.style.use()`, `rcParams`, artist keyword arguments |
| Explicit plot layout | `layout="constrained"`, `tight_layout()`, normal GridSpec |
| Save/output format | `fig.savefig(...)` |
| Interactive behavior | `plt.ion()` / `plt.ioff()` / `plt.show(block=...)` |

Only backend-specific capabilities that Matplotlib cannot express SHOULD use `WSKR_*` configuration, e.g. `WSKR_THEME=auto|dark|light` for troubleshooting, `WSKR_QUERY_TIMEOUT_MS`, diagnostic logging, and an explicit graphics disable/selection flag. Keep this surface intentionally small; avoid a second general-purpose styling/configuration language. Document precedence and defaults.

### 10.2 Dependencies

Core runtime SHOULD require only supported Python and Matplotlib, plus a standard-library implementation of POSIX TTY handling where possible. Optional extras:

- `rich` for Rich renderables.
- `darkdetect` or platform integration for OS-appearance fallback only.
- optional `Pillow` only if a feature actually requires it beyond Matplotlib's existing image support.
- testing/documentation tools in dev dependencies, not runtime dependencies.

Do not retain pytest-timeout, SciPy, or other tooling as unneeded production requirements. Do not add dependencies without a documented reason per `AGENTS.md`.

Start from the repository's current supported Python version (`>=3.12` unless deliberately changed and tested). Avoid inventing a new broad version guarantee during a design-only change.

### 10.3 Licensing

`wskr` currently declares **GPL-3.0-only**. Preserve that declared licensing status unless a separate explicit decision changes it. Architectural ideas from other projects are not copyrighted code to be copied blindly; review licenses before transplanting implementation or test code. The referenced jktr backend is CC0; ensure any imported snippets, dependencies, or new source comply with wskr's licensing terms. Keep license/provenance notes for copied or adapted code.

## 11. Compatibility and migration mapping

Refactor incrementally on a feature branch; keep separately reviewable, testable changes.

| Existing location | Target |
| --- | --- |
| `wskr.terminal.io` / `terminal.osc` | Safe TTY session, bounded response parser, dedicated terminal profile |
| `wskr.terminal.capabilities` / `terminal.kitty.capabilities` | Single provenance-aware profile and capability detector |
| `wskr.protocol.base` | Clear protocol interface for upload, place, update, delete, query |
| `wskr.protocol.kitty.KittyTransport` | Correct direct Kitty transfer, no mandatory `icat` |
| `wskr.protocol.kitty.KittyPyTransport` | Retire or merge into the corrected primary Kitty transport |
| `wskr.protocol.registry` | Retain optional registration, feature-check negotiated availability |
| `wskr.render.matplotlib.core` / `kitty` | Shared Agg backend, standard manager/canvas lifecycle, lazy defaults |
| `wskr.render.matplotlib.size` | Terminal-cell allocation and pixel/inch conversion with explicit-size provenance |
| `wskr.render.matplotlib.utils` | Theme/contrast/default-style resolver; fix boolean detection strategy |
| `wskr.render.rich.img` / `plt` | Shared Kitty image manager + standards-compliant Unicode placeholders |
| `wskr.render.matplotlib.iterm2` / `sixel` | Stop advertising as functional until real transport/backend tests exist |
| `jkit.plot` helpers | **Keep outside wskr**; use ordinary Matplotlib to compose figures |
| `mplkitty` prototype | Source of behavioral requirements and tests; do not introduce a duplicate public backend |

Existing working backend names and meaningful Rich classes should remain importable during a deprecation window. Explicitly document removals and changed default behavior in the changelog and migration guide. No unannounced change from PNG/TTY rendering to destructive terminal takeover.

## 12. Validation strategy

Tests are layered, deterministic where possible, and must not depend on GitHub Actions. All real-Kitty tests are opt-in local runs.

### 12.1 Pure unit tests

- Terminal color parsers: `OSC 4/10/11/21`, supported delimiters, malformed/truncated responses, 8-bit/16-bit RGB fields, unrelated reply rejection.
- Kitty extended capability parsing: font, DPI, opacity, unknown answers, unsupported versions.
- Dark/light precedence: a valid `False` (light) must terminate strategy selection; explicit override, terminal query, `COLORFGBG`, OS fallback, complete failure.
- Contrast/color-cycle selection: black/white, near-neutral, low-contrast and unusual ANSI palettes.
- Cell/window metric inference and provenance; absent/non-positive geometry; narrow viewport; very small terminal.
- Figure pixel buffer dimensions match the allocated measured cells within rounding tolerance. Vary figure DPI independently to ensure pixels, not physical monitor DPI, determine placement.
- Explicit `figsize`, user `rcParams`, styles, per-artist colors and named Matplotlib font sizes are preserved.
- Correct PNG `f=100`, payload Base64, ≤4096-byte chunks, `m` continuation, decoding identity; intentional RGBA `f=32` separately tested.
- Image/placement ID allocation, replacement, disposal, acknowledgment and timeout behavior.
- Rich measurement, row/column diacritic generation, placeholder identity encoding, and protocol cleanup.
- Import has no `rcParams` side effects or terminal/subprocess I/O.
- `savefig()` emits neither terminal probes nor graphics escape codes and produces correct PNG/SVG artifacts.

### 12.2 Pseudo-terminal integration tests

- Open/close TTY once and restore exact original termios flags on normal, exception, interrupt, and timed-out paths.
- Read until expected response terminator without consuming arbitrary unrelated input; verify bounded response and correct query matching.
- No output or probing on redirected stdout unless a safe, explicit controlling-TTY render destination is requested.
- Missing `/dev/tty`, `isatty=False`, unavailable graphics, missing executable, and tmux without passthrough all fail safely and observably.
- `plt.ion()` and REPL/pandas workflows trigger auto-display without explicit `plt.show()`; repeated stale events debounce.
- `plt.show(block=False)` returns, `plt.show(block=True)` enters/exits cleanly, Ctrl-C restores screen state.
- Geometry and theme changes trigger redraw of backend-owned defaults; explicit figures and colors are unaffected.
- Multiple open figures do not share image/placement IDs and destroy independently.
- No old images accumulate during repeated resize/theme redraw cycles.

### 12.3 Real Kitty acceptance tests

Adapt existing `tests/test_e2e_kitty.py` tooling for a real Kitty session. Where feasible, use a separate disposable Kitty window or test terminal and compare screenshots against baselines. GUI automation such as `yabai` may be used in an optional local adapter, never required for ordinary tests.

Required manually/visually verified configurations:

1. Dark Kitty theme, light Kitty theme, manual dynamic theme switch, Kitty OS-following theme switch.
2. Different Kitty ANSI palettes and transparent/semitransparent backgrounds.
3. Terminal widths roughly 60/100/160 cells; short viewport; live resize while rendering.
4. Multiple font sizes and at least two font families; both HiDPI and ordinary pixel geometries.
5. One-line CLI/shell workflow, interactive Python/`plt.ion()`, pandas `.plot()`, and a managed `show(block=True)` session.
6. Multiple figures; Rich figure inside a table/panel; scrolling and redraw.
7. Direct Kitty, SSH/remote output where available, tmux passthrough or explicit unsupported fallback.
8. Piped output and no TTY: no corrupt ANSI escape sequences.
9. Conventional `savefig` PNG/SVG comparison unaffected by Kitty theme.
10. Repeated display/close cycles with no lingering images, terminal mode changes, or shell prompt corruption.

Screenshot comparisons SHOULD measure geometry, contrast, clipping, alignment and perceptual change as well as raw pixel difference. Normalize or allow documented differences caused by fonts, DPI and terminal version; do not make a single host's raster pixels a universal pass condition.

### 12.4 Quality and operational tests

- Run the repository's documented `uv`, Ruff, formatting, typing and pytest/coverage checks where available; record any environment blocker instead of claiming a pass.
- Include installed-wheel smoke tests of `MPLBACKEND=wskr_kitty` and `module://...`, without relying on an editable checkout.
- Measure typical startup/first-render cost, terminal query latency, PNG transmission time, and redraw behavior. Cache safely but do not freeze geometry across terminal resizes.
- Log debug detail to stderr/logger only, keep ordinary output quiet, and never record terminal keystrokes or binary payloads in diagnostic logs.
- Explicitly separate mock/PTy passes from **actual Kitty screenshot verification** in release notes.

## 13. Implementation phases and exit gates

### Phase 0 — Characterize the baseline

- Pin current working wskr backend and Rich behavior in regression tests.
- Record existing imports, backend names, and existing `wskr` configuration meanings.
- Review licences, direct dependencies, available testing environments and all existing integration fixtures.
- **Exit:** a runnable baseline test suite and documented migration compatibility map.

### Phase 1 — Safe terminal/profile and theme system

- Introduce bounded TTY session and provenance-aware `TerminalProfile`.
- Correct terminal color queries and dark/light strategy chaining.
- Query geometry, palette, Kitty font/DPI/opacity with safe fallbacks; avoid import-time I/O.
- Establish terminal-derived creation-time Matplotlib style defaults.
- **Exit:** pure and PTY tests prove accurate probes, fallback behavior, no FD leaks, no unsafe import effects, no forced user style changes.

### Phase 2 — Correct native Kitty transport

- Complete standards-compliant Base64 PNG transfer and capability negotiation.
- Implement image/placement IDs, updates, deletions, cursor/screen handling.
- Remove the mandatory external `kitty` executable dependency; retire incorrect experimental transfer path.
- **Exit:** protocol serialization tests and live Kitty one-shot/multiple-placement tests pass.

### Phase 3 — Matplotlib compatibility and live behavior

- Implement explicit-vs-default sizing ownership, auto-style at figure construction, stable exports.
- Correct `show(block=...)`, `ion()`, REPL/pandas, multiple figures, draw-idle and clean manager lifecycle.
- Add managed resize/theme refresh, prompt-safe one-shot output, and live-view restoration.
- **Exit:** stock Matplotlib scripts and unit/PTy/live checks meet `14`.

### Phase 4 — Unified Rich placement

- Reuse graphics manager for `RichImage`/`RichPlot`.
- Correct Unicode placeholder and virtual placement logic; remove independent sizing/framing.
- Introduce optional `rich` extra and backwards-compatible aliases.
- **Exit:** Rich nested table/panel/scroll/reflow tests and live Kitty screenshots pass.

### Phase 5 — Release and cleanup

- Prune unused dependencies and misleading advertised stubs; align package entry points, docs, examples, and errors.
- Preserve a migration path for `wskr_kitty` and existing Rich imports; record deprecated APIs before eventual removal.
- Validate wheel/sdist and local installation; perform the complete Kitty acceptance matrix.
- **Exit:** all release acceptance gates pass, documented limitations are precise, changelog/version follow repository policy, and no unsupported transport is claimed complete.

## 14. Definition of done

The consolidated implementation is complete only if **all** of the following hold:

- Standard `plt.subplots()`/`ax.plot()`/`plt.show()` works with `MPLBACKEND=wskr_kitty` and with the module URI, using an installed wheel.
- Ordinary Matplotlib `figsize`, `dpi`, `rcParams`, styles, artist colors, `savefig`, and layout engines behave predictably and honor explicit choices.
- Default figures automatically match measured Kitty cell geometry, background/foreground, legible terminal accents, and appropriately scaled fonts with **no mandatory application configuration**.
- New plots pick up current dark/light colors; live backend-owned plots can resize/retheme without losing deliberate user styling or leaking image placements.
- Direct Kitty PNG transport uses correct encoding and acknowledgments, requires no `kitty` binary, and updates/removes managed placements safely.
- `plt.ion()`, REPL and pandas interactive plotting behave through normal Matplotlib lifecycle; `show(block=False)` does not block; blocking views restore terminal state.
- Rich plotting shares the same image manager and works in measured nested terminal layouts via correctly encoded Unicode placeholders.
- Headless/redirected/non-Kitty environments do not receive escape-sequence garbage and do not report a successful display when no display occurred.
- Tests distinguish unit, PTY and real-Kitty coverage; live Kitty visual validation is completed and documented.
- Core dependencies stay minimal; experimental backends are not presented as supported; migration and licensing are documented.

## 15. Deferred extensions and decisions

**Deferred, not part of initial completion:**

- Functional Sixel/iTerm2 transports, built from the same protocol interface and released only after real end-to-end checks.
- Indexed-color Kitty graphics (`f=8` / `f=16`) for theme-reactive graphics without PNG rerendering; requires feature negotiation and appropriate palette quantization.
- Sophisticated pointer navigation, zoom/pan, paned terminal dashboards, animation, and high-frequency redraw scheduling.
- Image protocol alternatives such as local-file/shared-memory transfer for performance; direct Base64 is the correctness baseline.
- Publication-specific subplot utilities or domain-specific charting APIs; these remain application libraries.

**Resolved decisions:**

| Question | Decision |
| --- | --- |
| Canonical project? | `wskr` |
| Primary supported graphics transport? | Direct Kitty protocol |
| Default public plotting interface? | Stock Matplotlib, unchanged |
| Primary style authority? | User overrides, then current terminal measurements |
| Default physical layout authority? | Terminal cells and pixel geometry, not assumed monitor DPI |
| Dynamic resizing? | Only backend-owned default dimensions |
| Dynamic recoloring? | Only demonstrably backend-owned style values |
| Rich integration? | Optional adapter using shared image manager and Kitty Unicode placeholders |
| Multi-protocol support? | Architecture retained; unsupported adapters unadvertised |
| Plot semantics/application metrics? | Outside the backend (`jkit`, `git-wut`, etc.) |
| Tests/release automation? | Local, reproducible and opt-in GUI tests; no GitHub Actions required |

## 16. References and provenance

### Source implementations reviewed

- [wskr](https://github.com/josephcourtney/wskr): `src/wskr/protocol`, `terminal`, `render/matplotlib`, `render/rich`, and terminal tests.
- [jkit](https://github.com/josephcourtney/jkit): `src/jkit/plot.py` and its tests; application-level subplot layout helpers.
- [matplotlib-backend-kitty](https://github.com/jktr/matplotlib-backend-kitty): minimal Agg-based Matplotlib backend, `icat` integration and REPL behavior.
- `mplkitty` v0.1.0/v0.2.0: standalone local prototype developed in discussions on 2026-10-19; used here as a requirements/behavioral reference, not claimed to be part of the wskr repository.

### Standards and development references

- [Kitty graphics protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/) — image transmission, chunking, IDs, placements and Unicode placeholders.
- [Kitty terminal queries](https://sw.kovidgoyal.net/kitty/kittens/query_terminal/) — runtime font, DPI, foreground/background and opacity capabilities.
- [Matplotlib backend bases](https://matplotlib.org/stable/api/backend_bases_api.html) and [backend development](https://matplotlib.org/stable/users/explain/figure/writing_a_backend_pyplot_interface.html) — canvas/manager and selection contracts.
- [Rich renderables](https://rich.readthedocs.io/en/stable/console.html#console-renderables) — layout measurement and output protocol.

### Discussion history integrated

- Earlier `wskr`/Kitty conversations: selecting a Matplotlib backend, interactive plotting, OSC dark-mode queries, and the inaccessible-TTY / `termios` failure mode.
- 2026-10-19 `git-wut` report critique: excessive chart area, unreadable short-window histories, terminal aesthetics, and separation of backend rendering from dashboard information selection.
- 2026-10-19 `mplkitty` design/implementation: geometry/color/font/DPI/opacity probing, normalized style defaults, safe fallbacks, native Kitty transport, resize and theme refresh.
- 2026-10-19 architecture comparison: canonical `wskr`, minimal stock-Matplotlib interface, reuse of Rich/transport ideas, keeping `jkit` plotting utilities separate.

This specification is the **target contract**. It intentionally distinguishes current repository features from planned changes and requires verification before declaring any migration phase complete.
