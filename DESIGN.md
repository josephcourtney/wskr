# wskr — Design

**Status:** Adopted target design (not a statement that all features are implemented)  
**Scope:** Terminal-native Matplotlib rendering with optional Rich composition  
**Canonical implementation:** `wskr`

This is the durable statement of what wskr must be and preserve. [PLAN.md](PLAN.md) describes the migration; [STATUS.md](STATUS.md) describes current reality; [TODO.md](TODO.md) lists immediate work; the [ADRs](docs/adr/) record why major choices were made. Requirements are normative unless marked optional or deferred.

## 1. Purpose and boundaries

wskr is a terminal-image rendering backend that allows existing Matplotlib code to display figures in a graphical terminal with an appearance appropriate to its **current** font, size, foreground/background, and color palette. It also offers optional Rich renderables for arranging figures alongside text. Kitty is the first fully supported graphics-protocol target.

wskr MUST NOT redefine plotting semantics, select chart types or aggregation, duplicate Matplotlib's axes/layout engine, or absorb domain-specific visualization tools such as those in `jkit.plot`. It MUST use Matplotlib's Agg canvas for rasterization and keep ordinary figure exporters operational.

The user-facing target is stock Matplotlib:

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([0, 1, 2], [3, 1, 4])
plt.show()
```

Selecting `MPLBACKEND=wskr_kitty` (or `module://wskr.render.matplotlib.kitty`) is the only required integration. The intended default requires no `wskr`-specific figure, plot, or show calls.

## 2. Architectural invariants

- **INV-01 — Matplotlib ownership.** Matplotlib owns its public figure, artist, rcParams, style, layout, interactive and save/export interfaces. No parallel plotting API is required.
- **INV-02 — Explicit intent.** Explicit sizes, DPI, colors, styles, text properties, and figure/layout settings take precedence over automatically inferred defaults. Ambiguous style provenance is treated as user-owned.
- **INV-03 — Terminal authority.** The attached terminal's effective runtime geometry and colors take precedence over host-OS appearance, configuration files, environment hints, and fallbacks.
- **INV-04 — Provenance.** Every detected metric distinguishes queried/measured, inferred, configured, and fallback values; missing data is not reported as measured.
- **INV-05 — Isolation.** Terminal queries, graphics transmission, Matplotlib integration, and Rich integration have separate typed interfaces. Importing a package must not query a terminal or globally reconfigure Matplotlib.
- **INV-06 — No unsafe output.** Raw graphics/terminal escapes MUST NOT be emitted into redirected stdout or an unsupported terminal. TTY state must be restored after errors and interruption.
- **INV-07 — Correctness of graphics protocol.** Encoded pixel formats, lengths, chunk boundaries, image/placement IDs, acknowledgments, and deletion obey Kitty's specification.
- **INV-08 — Image lifecycle.** Image uploads, placements, updates, and disposal are separate operations. Interactive redraw must not indefinitely accumulate previous images in scrollback.
- **INV-09 — Honest failures.** An unavailable transport cannot silently masquerade as a successful graphic display.
- **INV-10 — Reproducibility.** Conventional `savefig` exports remain independent of terminal appearance unless the application deliberately applies a terminal-specific style to the figure.
- **INV-11 — Optional composition.** Rich can use the same underlying image transport and sizing calculations but must not be a required dependency of basic Matplotlib use.
- **INV-12 — Honest capabilities.** Unsupported or incomplete iTerm2/Sixel implementations remain explicitly unavailable, regardless of entry-point registrations.

Rationale: [ADR-001](docs/adr/0001-canonical-wskr-and-stock-matplotlib.md), [ADR-002](docs/adr/0002-terminal-measured-defaults.md), [ADR-003](docs/adr/0003-kitty-transport-and-placement.md).

## 3. Component model

```text
      Matplotlib / pandas                 Optional Rich application
               |                                     |
       Standard backend API                    RichPlot / RichImage
               |                                     |
     Matplotlib Agg canvas                           |
               +------ Figure rendering service ----+
                              |
              TerminalProfile + style resolver
                              |
               Graphics image/placement manager
                              |
            ImageProtocol / Kitty graphics transport
                              |
           Safe terminal I/O + bounded query session
                              |
                      Attached terminal
```

### Terminal capability service — `wskr.terminal`

Owns geometry and color queries, safe TTY sessions, response framing/parsing, capability negotiation, caching, and a typed immutable `TerminalProfile`. It must not import figure or Rich semantics.

Its public/internal data model must express terminal rows/columns, window pixels, cell pixels, foreground/background, queried ANSI palette values, font family/size (when known), terminal DPI (when known), opacity (when known), negotiated graphics support, and provenance for each value.

### Protocol and image manager — `wskr.protocol`

Owns encoding, transmission, image identity, placement identity, replacement, deletion, and session cleanup. Image transfer and placement are distinct. The interface supports ordinary inline placement and virtual/Unicode-placeholder placement. Protocol transport must not resize figures or choose Matplotlib colors.

### Matplotlib backend — `wskr.render.matplotlib`

Owns a standard Agg-derived `FigureCanvas`/`FigureManager` lifecycle, figure-creation defaults, terminal display policy, redraw coordination, and the normal `show`/`draw_idle`/`destroy` interactions. It delegates all terminal measurement and image transmission.

### Rich adapter — `wskr.render.rich`

Owns Rich `Measurement` and renderable behavior; respects the Console's allocated cells and uses the shared graphics manager rather than encoding its own incompatible Kitty packets. Rich is an optional extra. Existing `RichPlot`/`RichImage` names should remain available with a documented migration policy.

### Core configuration and errors — `wskr.core`

Owns minimal explicit overrides, structured exceptions, and diagnostics. Neither import nor backend selection may alter unrelated global `rcParams` or force `text.usetex=False`.

## 4. Matplotlib interface contract

wskr supports normal `plt.subplots()`, `plt.figure()`, `ax.plot()`, `plt.style.use()`, `rcParams`, `plt.ion()`, `plt.ioff()`, `plt.show(block=...)`, `draw_idle()`, `fig.savefig()`, pandas plotting, and multiple open figures as far as terminal capability permits.

`wskr_kitty` is the primary backend name, registered through Matplotlib's supported `matplotlib.backend` entry-point group; the explicit `module://wskr.render.matplotlib.kitty` URI is also supported. Existing useful imports remain compatible or receive a deliberate deprecation path.

Figure-creation defaults are derived **before** constructing default-size artists. No public `wskr.subplots()`, `wskr.figure()`, special `height="12cell"` arguments or alternate pyplot API is introduced. Ordinary `figsize`, `dpi`, `fontsize`, `linewidth` and Matplotlib's relative font-size names remain the customization surface.

- `figsize=(w, h)`, `set_size_inches()` and user DPI choices are authoritative. Backend-owned default-sized figures can resize with the terminal; explicit ones cannot be resized behind the user's back.
- `savefig` must preserve its normal formats and options without transmitting graphics or mutating explicit figure sizing.
- New figures use newly detected colors. During managed live redraw, only demonstrably backend-owned styling is refreshed. Arbitrary artists, custom colormaps and explicit colors remain untouched.
- `show(block=False)` returns without taking over keyboard input. `block=None` follows Matplotlib interactive-mode expectations. An explicitly blocking managed terminal view may support resize/theme redraw and quit controls, provided it restores screen, cursor, termios and signals.
- `plt.ion()`/REPL/pandas plotting use standard Matplotlib idle/draw conventions rather than an application-specific `show`. Reentrant draws are guarded and frequent stale events coalesced.
- Each figure manager owns its own transport placements; closing one figure does not destroy unrelated figures. Displaying one figure does not implicitly close all others.

## 5. Terminal measurements and safe interrogation

The preferred measurements are:

| Data | Normal source | Fallback |
| --- | --- | --- |
| Rows and columns | `TIOCGWINSZ` | Standard terminal-size APIs; tagged assumptions |
| Window pixels | `TIOCGWINSZ` or `CSI 14 t` | Derived or unavailable |
| Cell pixels | `CSI 16 t` or window/grid division | Inferred with provenance |
| Foreground/background | Live `OSC 10`/`OSC 11` or Kitty extended current colors | Environment/OS hint; documented default |
| ANSI palette | `OSC 4` / Kitty color query | Contrast-safe palette |
| Font and DPI | Kitty terminal capability query | Local monospace/font-height defaults |
| Opacity | Kitty runtime capability query | Unknown, not assumed |
| Graphics | Negotiated protocol capability | Unsupported, not inferred from `TERM` alone |

Runtime measurements supersede `kitty.conf` and the operating-system theme. Signals such as `KITTY_WINDOW_ID`, `COLORTERM`, `TERM` and `COLORFGBG` are hints only.

Terminal interrogation MUST be bounded, non-destructive, and optional when a caller does not own the TTY. Query logic must respect `BEL` and `ESC \` framing, cap response sizes and wait time, identify expected responses, and avoid consuming unrelated keyboard input. It must restore termios even on interruption. No valid TTY must be a safe failure, not a `Bad file descriptor` crash. Multiplexer passthrough is used only when established as safe.

The effective `TerminalProfile` is cached within a render transaction and refreshed on a meaningful resize/theme event or bounded periodic probe; pixel metrics must not be cached permanently across terminal resizes. Diagnostics disclose which values were measured versus assumed.

## 6. Terminal-native appearance

### Theme selection

**Explicit user styling > backend-specific explicit override > currently queried terminal colors > trusted terminal hints > environment > OS appearance > fallback.**

A valid *light* detection is definitive for that strategy; fallback processing must not treat `False` as missing data. Determine dark/light appearance from the effective background using proper luminance handling, not from the OS preference or an ANSI color index alone. The backend does not impose a hardcoded dark-themed Matplotlib style at package import.

Default figure/axes backgrounds are transparent where feasible; opaque fallback uses the current terminal background. Text uses terminal foreground. Spines and grids are contrast-aware muted derivatives; data colors are chosen from queried ANSI colors subject to contrast and distinguishability checks. Default styling must not override explicit artist/figure settings.

When the terminal changes theme, new figures reflect it. A live managed session may rerender *backend-owned* styles, while preserving explicit styles. Existing scrollback bitmaps do not automatically recolor. Optional palette-indexed Kitty graphics may be added only after validated negotiation; true-color remains the baseline.

### Typography and geometry

Use actual cell geometry as the root scale. Derive the default font, line/marker widths and spacing coherently through ordinary Matplotlib `rcParams` and its existing relative font-size names. An unavailable queried font may not exist on the Python host; use a locally available monospace fallback without shipping proprietary font files.

The model distinguishes:

1. **Extent** — occupied terminal cells / pixels.
2. **Scale** — sizes of font, lines, markers and spacing relative to cell dimensions.
3. **Density** — visual detail and padding (applications own data-dependent simplification).

For allocated `C` columns and `R` rows, measured cell width `cw` and height `ch`, and internal rendering DPI `d`:

```text
width_px = round(C × cw)       height_px = round(R × ch)
figsize_inches = (width_px / d, height_px / d)
```

Internal rasterization DPI is **not necessarily physical monitor DPI**. The output buffer is calculated for the intended placement instead of guessed from inches alone. Default figure extent occupies a compact, bounded fraction of the terminal, not the full viewport by fiat. Explicit Matplotlib sizes remain respected. Labels must remain legible on short/narrow terminals.

## 7. Kitty image protocol and placement

The primary Kitty transport is a pure-Python protocol implementation; it does not require the `kitty` executable, Kitty remote control or `kitty +kitten icat`. The old external utility may remain an optional diagnostic tool.

- PNG transmission uses Kitty `f=100`; raw RGB and RGBA use `f=24` and `f=32` only with matching raw bytes. Protocol payloads are Base64 encoded; chunks and continuation markers comply with Kitty framing and size constraints.
- Image IDs, placement IDs, transmission, placement, replacement and deletion are separate managed operations. Redraws replace an existing managed view instead of appending unlimited image frames.
- Protocol support is negotiated safely; failures are explicit. Logging and diagnostics never expose untrusted input or binary image payloads.
- One-shot displays leave the shell prompt and cursor in a predictable state without arbitrary fixed-row subtraction. A blocking alternate-screen view restores prior state on exit/error.
- Rich uses Kitty Unicode placeholders (`U+10EEEE` with row/column diacritics and correct image/placement identity encoding) and **virtual** placements. Real and virtual placements have different lifecycles and must not be confused.
- The protocol manager limits retained images and releases only resources owned by its session.

The base protocol interface remains extensible; the currently stubbed iTerm2 and Sixel backends are **not** considered supported implementations. See [ADR-003](docs/adr/0003-kitty-transport-and-placement.md).

## 8. Rich composition

Rich integration should allow:

```python
from rich.console import Console
from wskr.render.rich.plt import RichPlot
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([0, 1, 2], [2, 3, 1])
Console().print(RichPlot(fig, desired_width=40, desired_height=10))
```

`RichPlot` and `RichImage` derive their size from the Console layout and use the same terminal profile, Agg rasterization and graphics manager as the Matplotlib backend. Uploads are reused when content/layout is unchanged. Unicode placeholders allow graphics to participate in Rich tables/panels and scroll with text where supported. Non-Kitty output must degrade visibly and safely rather than output raw escape codes.

Rich-specific sizing arguments are permitted for Rich renderables, not as a second Matplotlib plotting API.

## 9. Configuration, dependencies and compatibility

Use `MPLBACKEND` or `matplotlib.use` to select the backend, Matplotlib rcParams/styles for visual preferences, standard `figsize`/`dpi`/`savefig` for dimensions/export, and existing interactive-mode switches for display behavior.

Only terminal-specific concerns without a Matplotlib equivalent merit optional `WSKR_*` configuration (e.g. query timeout, troubleshooting theme override, protocol selection, diagnostics). Preserve established useful names or deprecate them explicitly.

Core runtime dependencies should remain minimal: supported Python + Matplotlib and stdlib TTY facilities where practical. Rich, OS theme fallback, screenshot tooling, and test dependencies are optional or development extras when the implementation permits it.

The project currently declares **GPL-3.0-only**; keep that license unless a separate deliberate licensing decision occurs. Third-party source must be license-reviewed before copying. A future transport must pass real capability and integration tests before being advertised as supported.

## 10. Acceptance invariants

The target is satisfied only if:

- Installed-package `MPLBACKEND=wskr_kitty` and module backend selection run ordinary pyplot scripts with no wskr plotting API.
- Explicit Matplotlib sizes, styles and exporters retain their semantics; auto defaults match measured cells and current terminal appearance.
- Safe, bounded terminal detection cannot corrupt redirected streams or steal unrelated application input.
- Kitty-native transmission correctly encodes PNG, manages images and placements, and cleans up on redraw/close.
- `plt.ion()`, multiple figures, nonblocking/managed-blocking show, resize and theme changes behave consistently.
- Rich shares placement/geometry infrastructure and is optional for core installs.
- Unsupported terminals and unimplemented transports fail honestly, and release status distinguishes unit/PTy testing from live Kitty screenshot validation.

These are design requirements, **not completion claims**. Implementation phases and test matrices belong in [PLAN.md](PLAN.md); current gaps are in [STATUS.md](STATUS.md).

## 11. References

- [ADR-001 — Canonical wskr and stock Matplotlib](docs/adr/0001-canonical-wskr-and-stock-matplotlib.md)
- [ADR-002 — Measured terminal defaults](docs/adr/0002-terminal-measured-defaults.md)
- [ADR-003 — Kitty transport and placement](docs/adr/0003-kitty-transport-and-placement.md)
- [Kitty graphics protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/)
- [Kitty terminal queries](https://sw.kovidgoyal.net/kitty/kittens/query_terminal/)
- [Matplotlib backends](https://matplotlib.org/stable/users/explain/figure/backends.html)
