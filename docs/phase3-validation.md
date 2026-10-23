# Phase 3 — Matplotlib Lifecycle Validation

**Status:** First implementation slice passed hosted quality and graphical regression checks at code SHA `3fda8e5f0130e5f54af9610ebea1b14c9f71a3f0`; **Gate P3 remains open**. This file records the evidence without attributing yabai-confounded screenshots to a renderer defect.

## Completed slice

- `render_figure_to_terminal` no longer calls `Figure.set_size_inches` or modifies a caller's figure/DPI at display time. Backend-derived construction defaults remain separate. Explicit finite/bounded `WSKR_SCALE` now rescales **only the transmitted PNG**, preserving the caller's raster-export semantics.
- `TerminalBackend.show` visits all registered managers without `Gcf.destroy_all`. Interactive redraw targets only the active manager.
- Destruction of each figure manager closes only its owned transport.
- `NativeKittyTransport.send_image` replaces the prior image on successful subsequent sends using scoped deletion; separately uploaded images remain independently owned.
- A dedicated `just phase3` recipe and hosted test step cover stable/user-owned geometry, changing viewport measurements, deterministic PNG/SVG exports, multiple managers, scoped cleanup and replacement.

## Hosted verification

GitHub Actions [quality run 39712138799](https://github.com/josephcourtney/wskr/actions/runs/39712138799) passed on Python 3.13 Ubuntu and macOS 15:

| Check | Ubuntu | macOS 15 |
| --- | --- | --- |
| Python compile, Ruff format/lint, ty | Pass | Pass |
| Full pytest | **235 passed, 3 skipped** | **235 passed, 3 skipped** |
| Focused Phase 3 | **34 passed** | **34 passed** |
| Focused Phase 2 regression | **54 passed** | **54 passed** |

The real Kitty graphical workflow [39712138855](https://github.com/josephcourtney/wskr/actions/runs/39712138855) also passed on Linux with Xvfb (physical and Unicode virtual placement). GUI rendering on macOS of this **new** Phase 3 code has not been separately observed. Previous macOS Phase 2 native placement evidence remains valid for unchanged protocol primitives but is not a Phase 3 visual signoff.

## Known boundaries

The user's local Phase 2 Matplotlib screenshot showed a cropped image **while yabai actively reshaped Kitty**. Its appearance is not proof of a wskr defect. Tests in this slice simulate geometry changes to verify **figure immutability**, not to prove live viewport fitting or window-manager resize redraw behavior.

Outstanding for Gate P3: explicit terminal placement/viewport policy for oversized user figures, stable-window versus yabai-resized screenshot comparison, interactive `show(block=True)`/REPL/pandas behavior, `draw_idle` scheduling and debounced resize update, multiple displayed images during scrolling, image placements/repositioning and wheel/module-backend export qualification. The figure's size/DPI/style must stay authoritative under ADR-002.

## Static output persistence at interpreter exit — October 22, 2026

The preceding implementation deleted the last Kitty plot when the smoke-test script exited: Matplotlib's registered `Gcf.destroy_all` called `KittyFigureManager.destroy()`, which invoked `NativeKittyTransport.close()` and deleted the one-off image. This was directly observed on native macOS, with yabai **disabled**, after pressing Enter at the smoke-test prompt. The original script retained the entire image while the process was alive.

**Implemented:** Matplotlib's normal `Gcf.destroy_all` shutdown remains registered. A subsequent lightweight `atexit` callback marks interpreter shutdown *before* the figure managers are destroyed. Only managers whose last successful `show()` happened with interactive mode **off** call the optional `ImageProtocol.retain_display()` hook before closing. Native Kitty relinquishes ownership of its final one-off display without issuing an image-delete frame; all other independently owned uploads/placements remain subject to scoped close cleanup. Explicit `plt.close()` or `Gcf.destroy` still delete the output, as do managed interactive displays at exit. Repeated updates still delete superseded display images.

**Hosted evidence:** [quality workflow 39766399752](https://github.com/josephcourtney/wskr/actions/runs/39766399752) passed on Python 3.13 in Ubuntu and macOS 15: Ruff, ty, compilation, **241 full tests passed, 3 skipped**, focused Phase 3 **40 passed** and Phase 2 **54 passed** per operating system. [Real Kitty GUI run 39766399850](https://github.com/josephcourtney/wskr/actions/runs/39766399850) launched a *real* Python program that registered a final exit marker before importing Matplotlib; that marker is emitted after pyplot manager teardown. Kitty `--hold` displayed the surviving static chart after this marker. Host screenshot pixel tests detected **11,557 cyan, 19,292 magenta and 15,470 yellow pixels**, and both existing native physical/Unicode virtual placement scenarios also passed.

**Not yet verified on native macOS GUI:** the new process-exit retention policy. A local check is:

```sh
git switch main && git pull --ff-only && uv sync
WSKR_SCALE=0.4 just visual-smoke matplotlib
```

The chart should remain visible after the script returns to the shell. Explicit `plt.close()` before exit is expected to remove it. This is a deliberately narrow lifetime policy, not a completed solution for cross-session scrollback, window-resize redraw, remote terminal reconnections, or `show(block=True)`; **Gate P3 remains open**.

## Foreground blocking show and interactive Kitty redraw — October 22, 2026

**Implemented and tested at code SHA `e4ae001de37a333251905dd8b425aa78a745f8b0`:**

- Ordinary `plt.show()`, `plt.show(block=None)` and `plt.show(block=False)` remain **nonblocking**. Unlike GUI backends, a terminal plot has no separate user-closable window; ordinary noninteractive output must remain in Kitty history when Python exits.
- Explicit `plt.show(block=True)` checks that **both stdin and stdout are TTYs, resolve to the same terminal, and stdin belongs to the foreground process group**. It renders all registered figures, displays an explicit Enter-to-close prompt, and calls `Gcf.destroy_all()` when the user finishes, including when `KeyboardInterrupt` or `EOFError` interrupts input. Invalid/shared input is rejected **before rendering**, without consuming REPL or notebook bytes. This terminal-specific policy is not a general Matplotlib GUI event loop.
- The Kitty-specific Agg canvas now inherits the guarded `WskrFigureCanvas.draw/draw_idle` behavior. Interactive draw requests transmit a PNG, are protected against recursive draw callbacks, replace the previous Kitty image with a scoped deletion, and clean up on managed close. Noninteractive `draw_idle` does not unexpectedly transmit.
- A **real child process on a controlling POSIX PTY** ran the actual `module://wskr.render.matplotlib.kitty` backend and `plt.show(block=True)`, received an Enter key through its PTY, emitted the expected Kitty PNG upload and scoped image-delete packets, and exited cleanly on both hosted Linux and macOS. Additional pure/in-process tests cover mismatched TTYs, background process groups, absent stdin, unchanged nonblocking semantics, interruption cleanup, and actual interactive native Kitty redraw.

[Hosted quality run 39891723351](https://github.com/josephcourtney/wskr/actions/runs/39891723351), Python 3.13:

| Check | Ubuntu | macOS 15 |
| --- | --- | --- |
| Compilation, Ruff format/lint, ty | Pass | Pass |
| Full pytest | **253 passed, 3 skipped** | **253 passed, 3 skipped** |
| Focused Phase 3 | **52 passed** | **52 passed** |
| Phase 2 regression | **54 passed** | **54 passed** |

The [real Kitty/Xvfb graphical workflow 39891723347](https://github.com/josephcourtney/wskr/actions/runs/39891723347) passed physical, Unicode virtual and post-interpreter-exit static image scenarios. The new explicit blocking prompt has been exercised through real controlling PTYs on **both systems**; a separately observed native macOS Kitty GUI session for this prompt is not yet recorded.

**Still outstanding for Gate P3:** native macOS GUI interactive confirmation, deliberate terminal resize/theme notifications and debounced placement changes, richer IPython/pandas REPL behavior, image scrollback positioning and wheel-qualified workflows. `block=None` remains intentionally nonblocking (a documented terminal-output exception to GUI-backend default-block semantics). Interactive blocking does not imply generalized UI event-loop support. Figure geometry, DPI and exports remain caller-owned.

## Blocking Kitty plots restore terminal contents — October 23, 2026

**Observed on native macOS:** After `plt.show(block=True)` returned on Enter, the image disappeared, but the rows underlying it remained blank. This is expected for Kitty's `a=d,d=I` deletion operation: removing image pixels does **not** retract terminal text rows or edit existing scrollback. The problem was a missing distinction between persistent primary-screen output and temporary managed graphics, not failed PNG transmission.

**Implementation:** For an explicitly foreground-owned `show(block=True)`, enter xterm/Kitty alternate screen (`CSI ? 1049 h`) *before* the first figure is rendered. Render all managed images, prompt for Enter, and issue scoped image cleanup while still inside that screen. Restore the primary screen (`CSI ? 1049 l`) in a `finally` path even when Enter is interrupted, rendering fails, or stdout flush raises. The primary text and cursor return immediately with **no image-sized gap**. The operation is performed only after the same-TTY and foreground-group input checks. `show(block=None|False)` is unchanged and continues to preserve ordinary plot output in terminal history.

**Real Kitty GUI acceptance evidence:** The [hosted alternate-screen visual workflow](https://github.com/josephcourtney/wskr/actions/runs/39926528819) captured actual Xvfb/Kitty screenshots before and after closure. The alternate screen displayed the reference bar plot with **9,954 cyan, 14,852 magenta and 12,246 yellow pixels**. On the restored primary screen those colors were absent, while bright green/red primary-screen markers were both visible (4,536 pixels each) and separated by **18 pixels**—one text row, rather than a plot-sized blank region. An independent controlling-PTY integration test verifies escape sequence order: enter alternate screen, upload PNG, delete owned image, restore primary screen, then return to caller. Existing physical/virtual graphics and post-interpreter-exit persistent output remain separately tested.

**Verification scope:** The user has not yet run this specific alternate-screen correction in native macOS Kitty. The hosted GUI experiment confirms real Kitty behavior on Linux; macOS unit/PTY checks and static analysis qualify the code path but do not constitute macOS GUI visual inspection. Gate P3 remains open for live resize/viewport behavior and richer REPL/pandas integration.

## Opt-in display-only measured viewport containment — October 23, 2026

**Implemented:** `WSKR_FIT=contain` is an explicitly opt-in render-time scaling policy. Each display obtains the attached terminal's actual pixel dimensions from `ImageProtocol.get_window_size_px()` and constrains the **transmitted PNG** to those bounds, preserving aspect ratio. Without the option, the native-size renderer is unchanged. Containment alone never enlarges an image; an explicit finite/bounded `WSKR_SCALE` can enlarge or shrink before the containment cap. If pixel geometry is missing/invalid, the renderer does not guess terminal DPI or silently resize the Matplotlib figure; it preserves the uncontained raster. Repeated `show()`/`draw_idle()` calls sample geometry again, but **window resizing does not yet trigger an automatic redraw**, reposition the cursor, or adjust Kitty placements by itself.

**Figure ownership and exports:** The source `Figure.figsize`, `Figure.dpi`, artists/styles and PNG/SVG `savefig` remain untouched. Unit tests compare byte-identical exports while changing viewport width/height and checking that dimensions never exceed the measured viewport. An actual POSIX PTY test modifies `TIOCSWINSZ` pixel dimensions between displays and reads them via the production `TIOCGWINSZ` path.

**Hosted code qualification:** [Quality workflow 39930104004](https://github.com/josephcourtney/wskr/actions/runs/39930104004) at source commit `cce34465f4b034297a4339d58b204b10ac312ed3` passed on Python 3.13 Ubuntu and macOS 15: compileall, Ruff format/lint, `ty`, full **265 passed, 3 skipped** on each platform, focused Phase 3 **64 passed**, Phase 2 **54 passed**.

**Real Kitty evidence:** [Kitty GUI run 39929822366](https://github.com/josephcourtney/wskr/actions/runs/39929822366) launched an actual Kitty process inside Linux/Xvfb with `WSKR_FIT=contain`. An explicit 6×6 inch, 300-DPI Matplotlib figure (**1800×1800 source pixels**) was transmitted at **396×396 pixels**, within Kitty's freshly measured **639×396 pixel viewport**. Its cyan/magenta/yellow bars were visible on a screenshot after the child Python process exited. Existing physical/virtual placement and alternate-screen restoration checks still passed.

**Qualification limits:** This proves actual terminal-pixel containment and post-process-exit graphical transmission on hosted Linux; it does **not** establish automatic resize-triggered redraw, fit to the **remaining space below an arbitrary cursor**, or local native macOS Kitty results for this new opt-in mode. Reserve full Gate P3 signoff for controlled yabai/unmanaged geometry and adaptive placement tests.

## Foreground live geometry redraw — October 23, 2026

**Implemented in PR #26:** During an **explicit** `plt.show(block=True)` session with `WSKR_FIT=contain`, `wskr` owns the foreground TTY and passively polls kernel `TIOCGWINSZ` geometry at 100 ms intervals while waiting for a complete canonical input line. A stable change of rows, columns or measured pixel dimensions for 200 ms triggers a repaint of **only the alternate screen**, restarting at its home cursor position; each figure manager transmits a newly contained PNG and uses existing Kitty scoped replacement/deletion. The Enter prompt remains available. Pressing Enter, Ctrl-C or EOF still closes owned images and restores the prior primary-screen content.

No SIGWINCH handler is installed or replaced, no termios mode is changed, and the implementation does not read keyboard bytes until the foreground-owned canonical TTY reports a completed line. During ordinary `show(block=False|None)` or a blocking session without `WSKR_FIT=contain`, the old behavior remains unchanged. This scope is deliberate: a nonblocking pyplot call cannot independently own the surrounding shell, IPython or pandas input event loop.

**Hosted evidence:** [Linux/macOS quality workflow 39932302605](https://github.com/josephcourtney/wskr/actions/runs/39932302605), tested code `d8ba8991aee23478e55d8030e90b1e125c572f5e`, passed compileall, Ruff format/lint, `ty`, **268 passed, 3 skipped** in the full suite on each platform, **67 focused Phase 3** and **54 Phase 2** per system. A new real controlling POSIX PTY test launches stock Matplotlib using `module://wskr.render.matplotlib.kitty`, changes `TIOCSWINSZ` pixels from 700×460 to 480×240 *while the plot is displayed*, verifies exactly two Kitty PNG transfer commands and scoped image cleanup, and checks the alternate-screen repaint/restore ordering. Synthetic tests cover unstable changes, debounce, unavailable geometry, and Enter without unwanted input reads.

**Real graphical regression:** The established Linux Kitty/Xvfb screenshot workflow remained green at the tested head. It tests physical/virtual placements, post-exit static output and gap-free alternate-screen restoration, **not a visual screenshot sequence of a live-resized Kitty window**.

**Open scope:** native macOS Kitty live resize under both stable/unmanaged and yabai-managed window geometry; actual placement/cursor measurements for multiple large figures; automatic nonblocking REPL event-loop redraw; terminal theme-change handling. Gate P3 remains open.

## Viewport-contained multi-figure contact sheet — October 23, 2026

**Implemented in PR #27:** Inside an **explicitly fitted noninteractive foreground** `plt.show(block=True)` session, two or more Matplotlib managers render their independent Agg canvases into a single display-only contact sheet. For a landscape measured viewport the panels occupy two nonoverlapping columns; portrait viewports use one column with successive rows. Terminal pixel geometry determines the tile allocation, aspect ratio is preserved, and two terminal rows are reserved for the Enter-to-close prompt. The resulting PNG uses only the first figure manager's transport image; the remaining managers and their figures remain independently owned and are closed normally. When the measured viewport changes, the existing debounced foreground redraw creates a replacement sheet and the native Kitty manager releases the previous image by scoped ID.

**Provenance / ownership:** The source `Figure.figsize`, `dpi`, artists and ordinary `savefig` remain unmodified. With insufficient measured pixels for useful tiles or when `WSKR_FIT=contain` is unset, the original sequential-manager behavior remains in effect; this first slice is **not** general Kitty per-image positioning, paging or Rich composition. Interactive redraw and nonblocking REPL modes remain unchanged. Rendering multiple figures through a contact sheet avoids relying on Kitty cursor advancement to position several full-size placements.

**Hosted quality:** [Workflow 39935239103](https://github.com/josephcourtney/wskr/actions/runs/39935239103), code SHA `995bc4f4b6d93f5fad3c652999a77e0edc260a6b`: Python 3.13 Ubuntu and macOS 15 both passed compileall, Ruff format/lint, `ty`, full suite **275 passed, 3 skipped**, focused Phase 3 **74 passed**, Phase 2 **54 passed**. Deterministic tests verify red and blue source canvases in separate wide/portrait tiles, byte-identical Matplotlib export, unchanged figure dimensions, insufficient-geometry handling, one transport upload and independent manager teardown.

**Real Kitty graphical acceptance:** [Workflow 39935239120](https://github.com/josephcourtney/wskr/actions/runs/39935239120) passed Linux/Xvfb physical and Unicode virtual graphics, post-process-exit persistence, alternate-screen restoration, and a **new actual two-manager screenshot**. The displayed contact sheet showed nonoverlapping red and blue panels in correct left-to-right order within the Kitty window, and neither remained on the restored primary screen.

**Open Gate P3:** Native macOS Kitty screenshot acceptance, controlled yabai-managed/unmanaged reflow tests, very-small-terminal figure navigation/paging, independent placement and cursor control, and nonblocking IPython/pandas display-loop integration.

## Small-terminal fitted paging — October 23, 2026

**Implemented in PR #28:** An explicitly fitted, noninteractive foreground `plt.show(block=True)` session containing multiple figures chooses a page capacity from measured terminal pixels rather than shrinking every panel indefinitely. The preferred minimum display-only tile is **240×180 pixels**, with two terminal rows reserved for the prompt. A wide window can present two columns; a portrait window presents one. If required, the remaining figures occupy subsequent pages as separate contact-sheet PNGs. The first manager's native Kitty transport retains sole ownership of the currently displayed sheet and deletes the previous page when a replacement is sent.

**Foreground interaction:** While blocking, `n` then Enter advances to the next page; `p` then Enter selects the previous page, wrapping around. A bare Enter (or `q` then Enter) closes the session and restores the previous terminal contents. Commands are read only after the foreground canonical TTY signals a complete input line. No raw input, installed SIGWINCH handler, or cross-REPL input ownership is introduced. On a debounced resize, page capacity is recalculated and the selected page is clamped if it is no longer valid.

**Evidence:** [Quality run 39938408398](https://github.com/josephcourtney/wskr/actions/runs/39938408398) passed Ubuntu and macOS 15, Python 3.13: compileall, Ruff format/lint, `ty`, **282 full tests passed, 3 skipped**, **81 focused Phase 3 tests passed**, **54 Phase 2 tests passed** on each platform. Pure tests cover narrow, landscape and portrait capacities, page clamping, single-panel raster composition, unchanged Figure `figsize`/`dpi` and byte-identical saved PNGs. A *real controlling PTY* running the actual Matplotlib/Kitty backend sent n/n/p/Enter with four scoped Kitty uploads and four image deletes, returning cleanly to the primary screen.

[Real Kitty/Xvfb run 39938408364](https://github.com/josephcourtney/wskr/actions/runs/39938408364) passed a new screenshot regression: page one contains red and blue independent pyplot figures, page two contains only green, and the primary screen contains none after exit. The same workflow also passed baseline physical/virtual placements, static post-exit persistence, alternate-screen restoration and two-figure layout.

**Remaining:** Native macOS Kitty paging and yabai-managed small-window visual confirmation, independent cursor-aware placements, nonblocking IPython/pandas event loops, and wheel qualification. With truly unusable or missing pixel measurements, the existing sequential fallback remains; this feature does not invent measurement precision or claim scrollback composition. Gate P3 remains open.

## Event-pumped nonblocking resize: graphical rejection — October 23, 2026

Merged [PR #29](https://github.com/josephcourtney/wskr/pull/29) introduced opt-in, debounced `canvas.flush_events()`/ `plt.pause()` refresh for previously displayed `WSKR_FIT=contain` figures without claiming terminal input. Ubuntu/macOS quality passed **288 tests, 3 skipped**, focused Phase 3 **87** and Phase 2 **54**, at [run 39941159016](https://github.com/josephcourtney/wskr/actions/runs/39941159016). The existing physical/virtual Kitty Xvfb scenarios passed; they did not test a live window shrink.

A dedicated **real Kitty/Xvfb** acceptance scenario in [draft PR #30](https://github.com/josephcourtney/wskr/pull/30) resized a real X11 Kitty window from **999×684** to **612×432** measured pixel viewport while a Python application pumped `flush_events()`. A 9×2-inch, 100-DPI figure transmitted an initial **900×200** PNG and then a correctly fitted **612×136** PNG. Real screenshots showed these red/blue chart pixels:

| Stage | Red | Blue |
| --- | ---: | ---: |
| Before resize | 16,008 | 21,525 |
| After resize, before redraw | 16,008 | 12,792 |
| After replacement upload/deletion | **0** | **0** |
| After interpreter exit | **0** | **0** |

Thus the original physical placement **survives** the window shrink (partly clipped); the event-pumped replacement loses visible placement. The source raster and width containment are correct, so unit/PTY PNG evidence is insufficient for placement acceptance. A 9×6-inch chart shows the same post-redraw disappearance. Reproduction and screenshot artifact references: [run 39942815378](https://github.com/josephcourtney/wskr/actions/runs/39942815378) and [issue #31](https://github.com/josephcourtney/wskr/issues/31).

**Acceptance remains open:** implement a safe independent placement anchor and non-destructive replacement policy without assuming ownership of REPL/shell cursor, output or input. Do not claim general nonblocking resize until after/before and post-exit real Kitty screenshots pass. Fitted blocking/alternate-screen resizing is a separate, previously qualified path.
