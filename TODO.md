# wskr — Immediate tasks

Only pending execution items. See [STATUS.md](STATUS.md) for qualified behavior, [PLAN.md](PLAN.md) for sequencing, and [DESIGN.md](DESIGN.md) for requirements.

## P3 — remaining native qualification and shell integration

- [ ] Qualify unowned REPL/IPython/pandas scheduling and multi-manager output under actual interactive shells; the backend cannot claim a foreign event loop or keyboard input.
- [ ] Qualify opt-in `WSKR_KITTY_ANCHOR=unicode` in native macOS Kitty: remaining 9×2/9×6 no-history controls, full unmanaged 9×2 seeded-history screenshot archive and independently verified window modes; check returned shell prompts in other geometries plus explicit-close cleanup before any default change.
- [ ] Requalify native macOS history/reflow case [#31](https://github.com/josephcourtney/wskr/issues/31): both 9×2 and 9×6, 0/96 seeded lines, unmanaged and yabai. Confirm visible and prompt-safe positions; do not interpret scrollback-offscreen as PNG corruption. Decide whether an additional owned viewport-pinning contract is needed beyond `owned_viewport()`.
- [ ] Qualify a native blocking page-**capacity change** (resize across the measured layout threshold) and capture the actual returned shell prompt. The first complete native 8-stage ZIP already visually confirms `n`/`p` navigation, fitted 2240→868→2548px redraw, and alternate-screen restoration; its capacity stayed four figures/page. Nonblocking multi-figure redraw/close separately passed native review.

**Verification for each code slice:** `just check`, focused PTY tests and installed-wheel smoke; record actual results. Run native Kitty visual cases when macOS GUI/yabai are available. Do not treat a generated evidence ZIP as visual acceptance without inspecting its screenshots.
