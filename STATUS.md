# wskr — Current status

[DESIGN](DESIGN.md) specifies target behavior; [PLAN](PLAN.md) orders work; [TODO](TODO.md) lists unqualified gates.

## Implemented and verified

- **P0–P2:** Installed `wskr_kitty` backend and direct Kitty PNG transport, owned bounded terminal probing, figure/placement lifecycle, PNG/SVG exports.
- **P3 runtime:** Foreground `show(block=True)` uses an alternate screen, measured fitted contact-sheet paging and restored primary screen. `block=False` retains history; debounced `flush_events()`/`plt.pause()` pumps all managed figures. Canonical n/p navigation replans after resize, respecting changed page capacity. `owned_viewport(fig)` supports live refresh/resize and owned dark/light recoloring of titles, labels, ticks, spines and grid (not explicit artist colors).
- **Interactive integration:** Opt-in IPython `%load_ext wskr.render.matplotlib.ipython` drains redraws after each completed cell, without stealing stdin, installing threads or starting its own event loop. Unattended redraw remains unsupported.
- **Native evidence:** Six owned-viewport scenarios, Unicode-anchor seeded-history and zero-history 9×2/9×6, two-figure lifecycle and native dark→light owned appearance pass. Blocking paging navigation/fit/restoration passed without changing page capacity. ICC-tagged screenshots are normalized to sRGB for tests.
- **Latest verification:** PR #65: **422 passed, 3 skipped** on Ubuntu and macOS, Ruff, `ty`, wheel smoke and hosted Kitty graphical checks passed.

## Acceptance still open

- [Issue #31](https://github.com/josephcourtney/wskr/issues/31): physical history anchors can leave the viewport on reflow. Unicode anchoring remains **opt-in**, not viewport-pinned; independent unmanaged-mode attestation and full returned-shell-prompt controls remain open.
- **P3 native signoff:** Real page-capacity change (`just native-paging-capacity`) and interactive IPython/pandas/Python REPL behavior remain unqualified. The native appearance scenario passed; broader palettes and unowned theme polling are not claimed.
- **P4/P5:** Rich inline Kitty rendering, release/dependency/stub hardening. iTerm2/Sixel graphics remain unsupported.

**Next:** [acceptance tasks](TODO.md), [native evidence](docs/phase3-native-macos-acceptance.md).
