# wskr — Immediate tasks

Only pending execution items. See [STATUS.md](STATUS.md) for qualified behavior, [PLAN.md](PLAN.md) for sequencing, and [DESIGN.md](DESIGN.md) for requirements.

## P3 — remaining native qualification and shell integration

- [ ] Qualify unowned REPL/IPython/pandas scheduling and multi-manager output under actual interactive shells; the backend cannot claim a foreign event loop or keyboard input.
- [ ] Qualify opt-in `WSKR_KITTY_ANCHOR=unicode` in native macOS Kitty: remaining 9×2 no-history control, 9×6 with 0/96 history lines, unmanaged/yabai modes; verify prompt position, after-exit persistence and explicit-close cleanup before considering a default change.\n- [ ] Requalify native macOS history/reflow case [#31](https://github.com/josephcourtney/wskr/issues/31): both 9×2 and 9×6, 0/96 seeded lines, unmanaged and yabai. Confirm visible and prompt-safe positions; do not interpret scrollback-offscreen as PNG corruption. Decide whether an additional owned viewport-pinning contract is needed beyond `owned_viewport()`.
- [ ] Confirm native macOS fitted blocking **multi-figure paging** (`n`/`p` + Enter), scoped explicit `plt.close()` deletion, and nonblocking multi-figure redraw separately from accepted owned-viewport cases.

**Verification for each code slice:** `just check`, focused PTY tests and installed-wheel smoke; record actual results. Run native Kitty visual cases when macOS GUI/yabai are available. Do not treat a generated evidence ZIP as visual acceptance without inspecting its screenshots.
