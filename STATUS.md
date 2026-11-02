# wskr — Current status

[DESIGN](DESIGN.md) specifies target behavior; [PLAN](PLAN.md) orders work; [TODO](TODO.md) lists unqualified gates.

## Implemented and verified

- **P0–P2:** Installed `wskr_kitty` backend and direct Kitty PNG transport, owned bounded terminal probing, figure/placement lifecycle, PNG/SVG exports.
- **P3 runtime:** Foreground `show(block=True)` uses an alternate screen, measured fitted contact-sheet paging and restored primary screen. `block=False` retains history; debounced `flush_events()`/`plt.pause()` pumps all managed figures. Canonical n/p navigation replans after resize, respecting changed page capacity. `owned_viewport(fig)` supports live refresh/resize and owned dark/light recoloring of titles, labels, ticks, spines and grid (not explicit artist colors).
- **Interactive integration:** Opt-in IPython `%load_ext wskr.render.matplotlib.ipython` drains redraws after each completed cell, without stealing stdin, installing threads or starting its own event loop. Unattended redraw remains unsupported.
- **Native evidence:** Six owned-viewport scenarios, Unicode-anchor seeded-history 9×2/9×6, and two-figure single-pump/selective-close pass. An eight-stage blocking paging run visually passed navigation, fit and restoration; it **did not** change page capacity. ICC-tagged screenshot comparisons now normalize display-space captures to sRGB.
- **Latest verification:** PR #65: **422 passed, 3 skipped** on Ubuntu and macOS, Ruff, `ty`, wheel smoke and hosted Kitty graphical checks passed.

## Acceptance still open

- [Issue #31](https://github.com/josephcourtney/wskr/issues/31): physical history anchors can become offscreen during reflow. `WSKR_KITTY_ANCHOR=unicode` remains **opt-in**, not viewport-pinned; zero-history/unmanaged mode and returned-prompt controls need native screenshots.
- **P3 native signoff:** A real page-capacity transition (`just native-paging-capacity`), dark/light owned measurements + screenshots (`just native-appearance`), and actual IPython/pandas/REPL host behavior. These harnesses exist but their required native results have **not** been reviewed.
- **P4/P5:** Rich inline Kitty rendering, release/dependency/stub hardening. iTerm2/Sixel graphics remain unsupported.

**Next:** [acceptance tasks](TODO.md), [native evidence](docs/phase3-native-macos-acceptance.md).
