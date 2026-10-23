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
