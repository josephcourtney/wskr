# wskr — Immediate tasks

Only pending execution items. See [STATUS.md](STATUS.md) for qualified behavior, [PLAN.md](PLAN.md) for sequencing, and [DESIGN.md](DESIGN.md) for requirements.

## P3 — managed redraw and Matplotlib lifecycle

- [ ] Add opt-in, owned-session **existing-figure theme refresh** for backend-owned styles only. Test dark→light, light→dark, explicit artist overrides and contrast/palette behavior, including failure to query.
- [ ] Extend opt-in event-pumped `draw_idle` coalescing into normal event-loop scheduling and coordinate multiple figures during ordinary REPL/IPython/pandas event pumping; add subprocess/PTY integration with explicit input/output ownership and exported image invariance.
- [ ] Define and implement independent image positioning, bounded scrollback/image lifetime and old-Kitty capability fallback without overwriting shell prompts. Re-test [issue #31](https://github.com/josephcourtney/wskr/issues/31) on native Kitty with 9×2 and 9×6 images under zero/seeded history, unmanaged and yabai resize. Record pixel/row geometry, screenshots and failure stage.
- [ ] Confirm native macOS fitted blocking **multi-figure paging** (`n`/`p` + Enter), scoped explicit `plt.close()` deletion, and nonblocking multi-figure redraw separately from accepted owned-viewport cases.
- [ ] Reconcile the `show(block=None)` behavior with DESIGN §4: current persistent nonblocking default intentionally differs from ordinary Matplotlib auto-blocking; retain existing behavior until a deliberate compatibility decision with tests.

**Verification for each code slice:** `just check`, focused PTY tests and installed-wheel smoke; record actual results. Run native Kitty visual cases when macOS GUI/yabai are available. Do not treat a generated evidence ZIP as visual acceptance without inspecting its screenshots.
