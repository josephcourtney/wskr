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
