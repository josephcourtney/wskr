# wskr — Immediate Tasks

Phase 2 is accepted. Phase 3 ownership/manager-lifecycle slice is qualified but **Gate P3 is not complete**; see [PLAN](PLAN.md), [STATUS](STATUS.md), [Phase 3 evidence](docs/phase3-validation.md) and [ADR-002](docs/adr/0002-terminal-measured-defaults.md).

- [ ] Define a display policy for figures with explicit `figsize`/`dpi` larger than the viewport: distinguish rendering bytes, image placement, optional *display-only* scaling and caller-owned figure geometry. Do not silently mutate explicit Matplotlib properties.
- [ ] Perform controlled real-Kitty visual comparisons with geometry stable (no yabai intervention) and geometry changed by yabai; record starting/final cell and pixel measurements, image positions and screenshots. The prior cropped image is **not** proof of a code bug.
- [ ] Finish interactive `plt.ion()` and `draw_idle()` scheduling, `plt.show(block=None|False|True)`, REPL and pandas with deterministic redraw/quit behavior and no recursive loops; `show(block=True)` is not yet implemented. Static noninteractive image persistence is now verified on hosted Kitty, but managed interactive cleanup requires further field testing.
- [ ] Implement debounced geometry/theme-change notifications and scoped image placement/repositioning without orphaned Kitty IDs or unbounded scrollback. Add multiple-figure, successive-draw and terminal-resize regression tests.
- [ ] Verify the new **static Kitty image survives Python shutdown on macOS**: within Kitty, run `WSKR_SCALE=0.4 just visual-smoke matplotlib` without `--pause`; the image should remain at the prompt after the script exits. Also confirm `plt.close()` explicitly deletes the last display. Hosted Linux Kitty already confirms post-teardown color pixels.
- [ ] Qualify wheel/module-backend workflows, regular PNG/SVG savefig, interactive PTY and real Kitty outputs across short/tall and resized windows; retain hosted Ubuntu/macOS checks.
- [ ] Review the evidence runner's unsupported Kitty configuration options (`clear_all_in_scrollback`, `hide_single_tab`) while preserving scoped screenshots; distinguish test-harness warnings from wskr defects.
- [ ] Phase 4 only: connect actual Rich `ConsoleOptions` layout, Unicode virtual placeholders, nested panels/tables and scrolled/reused images to the shared transport. Keep current Rich diagnostics until acceptance.
