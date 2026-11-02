# wskr — Current status

Handoff for the adopted [design](DESIGN.md) and [plan](PLAN.md). Pending actions are in [TODO.md](TODO.md); historical evidence remains in the linked reports and commits.

## Implemented and qualified

- **P0–P2:** Stock Agg-backed `wskr_kitty`, native Kitty PNG transport, bounded input-owned terminal probing, provenance-aware appearance, scoped placements and cleanup, and ordinary PNG/SVG exports. Installed-wheel backend selection has been tested.
- **P3 core:** `show(block=None)` uses foreground/noninteractive blocking semantics; `block=False` retains history. Blocking views use an alternate screen; `owned_viewport(fig)` supports application-driven resize and owned-theme refresh. A cooperative `flush_events()`/`plt.pause()` pump redraws multiple figures without reading shell input.
- **Native macOS evidence:** Six owned-viewport cases passed; opt-in Unicode history anchors passed seeded-history 9×2/9×6 resize cases; a two-figure Unicode test passed single-pump redraw, selective `plt.close` and post-child cleanup. Blocking `n`/`p` paging, fitted resize and primary-screen restoration passed eight visually inspected screenshots; page capacity stayed at four figures per page.
- **Color evidence:** An embedded display ICC profile explains native screenshot RGB shifts; native acceptance checks now normalize tagged captures to sRGB. PR #60: **411 passed, 3 skipped** on each of Ubuntu/macOS, plus hosted Kitty graphical, Ruff, `ty` and wheel checks.

## Open boundaries

- [Issue #31](https://github.com/josephcourtney/wskr/issues/31): Default physical history placement can move offscreen or overlap reflowed text. `WSKR_KITTY_ANCHOR=unicode` remains **opt-in**; it follows text rather than pinning a nonblocking plot to the viewport. Zero-history controls, independent window-mode verification and other returned-prompt geometries remain unqualified.
- P3 still needs an actual blocking **page-capacity transition**, native appearance/theme contrast checks, and native REPL/IPython/pandas event-loop qualification (an opt-in post-cell pump is available). Unowned terminal input cannot be queried or pumped autonomously.
- **P4/P5:** Rich inline Kitty graphics and optional dependency/packaging cleanup remain incomplete. iTerm2/Sixel are not supported graphics backends.

**Next:** [immediate tasks](TODO.md); [native evidence and limits](docs/phase3-native-macos-acceptance.md).
