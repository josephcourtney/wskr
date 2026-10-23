# wskr — Immediate Tasks

Phase 2 is accepted. Phase 3 ownership/manager-lifecycle slice is qualified but **Gate P3 is not complete**; see [PLAN](PLAN.md), [STATUS](STATUS.md), [Phase 3 evidence](docs/phase3-validation.md) and [ADR-002](docs/adr/0002-terminal-measured-defaults.md).

- [ ] Complete **automatic** viewport behavior: `WSKR_FIT=contain` now provides opt-in display-only containment using measured pixels on **each draw**, with unchanged `figsize`, `dpi` and `savefig`; still needed are resize-triggered redraw, cursor/placement awareness and responsive updates without editing user-owned figures.
- [ ] Perform controlled real-Kitty visual comparisons with geometry stable (no yabai intervention) and geometry changed by yabai; record starting/final cell and pixel measurements, image positions and screenshots. The prior cropped image is **not** proof of a code bug.
- [ ] Continue IPython/REPL/pandas figure hooks, redraw coalescing/debouncing and resumed/redirected terminal-input ownership. Native macOS Kitty `show(block=True)` alternate-screen restoration **was confirmed** by the user. Ordinary `show(block=None|False)` stays nonblocking and persistent.
- [ ] Implement debounced geometry/theme-change notifications and scoped image placement/repositioning without orphaned Kitty IDs or unbounded scrollback. Add multiple-figure, successive-draw and terminal-resize regression tests.
- [ ] Verify native macOS **explicit `plt.close()` scoped deletion** separately; static Kitty plots persisting through Python shutdown with `WSKR_SCALE=0.4` were already confirmed locally, and hosted Kitty validates the automatic-exit path.
- [ ] Qualify wheel/module-backend workflows, regular PNG/SVG savefig, interactive PTY and real Kitty outputs across short/tall and resized windows; retain hosted Ubuntu/macOS checks.
- [ ] Review the evidence runner's unsupported Kitty configuration options (`clear_all_in_scrollback`, `hide_single_tab`) while preserving scoped screenshots; distinguish test-harness warnings from wskr defects.
- [ ] Phase 4 only: connect actual Rich `ConsoleOptions` layout, Unicode virtual placeholders, nested panels/tables and scrolled/reused images to the shared transport. Keep current Rich diagnostics until acceptance.
