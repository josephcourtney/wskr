# wskr — Immediate tasks

Only pending execution items. See [STATUS.md](STATUS.md) for qualified behavior, [PLAN.md](PLAN.md) for sequencing, and [DESIGN.md](DESIGN.md) for requirements.

## P1 / P3 — terminal appearance and Matplotlib lifecycle

- [ ] Define and test an **input-owner integration** for live OSC 10/11/4 queries: no unattended input theft; forward unmatched bytes; record unavailable values honestly. Feed resulting profile to new-figure styling without globally changing `rcParams`. Prove explicit colors/styles survive.
- [ ] Add opt-in, owned-session **theme refresh** for backend-owned styles only. Test dark→light, light→dark, explicit artist overrides and contrast/palette behavior, including failure to query.
- [ ] Finish font, DPI and opacity detection where Kitty exposes reliable, safely queried values; mark unsupported data unknown and test provenance. Keep rendering DPI distinct from physical DPI.
- [ ] Improve `draw_idle` coalescing and coordinate multiple figures during ordinary REPL/IPython/pandas event pumping; add subprocess/PTY integration with explicit input/output ownership and exported image invariance.
- [ ] Define and implement independent image positioning, bounded scrollback/image lifetime and old-Kitty capability fallback without overwriting shell prompts. Re-test [issue #31](https://github.com/josephcourtney/wskr/issues/31) on native Kitty with 9×2 and 9×6 images under zero/seeded history, unmanaged and yabai resize. Record pixel/row geometry, screenshots and failure stage.
- [ ] Confirm native macOS fitted blocking **multi-figure paging** (`n`/`p` + Enter), scoped explicit `plt.close()` deletion, and nonblocking multi-figure redraw separately from accepted owned-viewport cases.
- [ ] Reconcile the `show(block=None)` behavior with DESIGN §4: current persistent nonblocking default intentionally differs from ordinary Matplotlib auto-blocking; retain existing behavior until a deliberate compatibility decision with tests.

## P4 / P5 — next phases, not P3 completion criteria

- [ ] Replace transitional `RichPlot`/`RichImage` implementation with `ConsoleOptions` sizing and shared virtual Kitty image manager, preserving caller figure dimensions; test panels, tables, scrolling and upload reuse.
- [ ] Make Rich and OS-theme helpers optional; remove unneeded runtime science/test dependencies, unsafe legacy Kitty chunks and misleading iTerm2/Sixel registrations with explicit compatibility notes.

**Verification for each code slice:** `just check`, focused PTY tests and installed-wheel smoke; record actual results. Run native Kitty visual cases when macOS GUI/yabai are available. Do not treat a generated evidence ZIP as visual acceptance without inspecting its screenshots.
