# Phase 3 lifecycle follow-up — 2026-11-01

This is a record of the lifecycle implementation increment in [PR #46](https://github.com/josephcourtney/wskr/pull/46), not a declaration that every native macOS history-reflow acceptance case passed.

## Implemented

- Matplotlib `show(block=None)` now auto-blocks a noninteractive foreground script owning its input/output TTY, without taking over a foreign REPL. Explicit `block=False` keeps history-resident output.
- A single event pump drains queued `draw_idle()` updates and debounced resize checks across all registered backend canvases. Reentrancy and explicit close are guarded; no background REPL input reader is installed.
- `LiveViewport.refresh_theme(profile)` updates demonstrably backend-owned figure/axes surfaces and principal labels only. Explicit axis/title/label colors, plot data, custom figures, user `rcParams`, and source figure geometry remain authoritative; absent or repeated theme measurements cannot force new uploads.
- `WSKR_KITTY_PARENT=off` opts out of newer parent-relative P/Q placement for older Kitty. Scoped replacement, cleanup and one-child-plus-anchor image ownership are bounded across repeated redraws.

## Verification

Implementation commit: `8c707c7ac87aed6e25b9d43bef47e68ee45acede`.

- [Ubuntu/macOS quality, type checks, complete pytest and installed-wheel smoke](https://github.com/josephcourtney/wskr/actions/runs/41362040033): **381 passed, 3 skipped** on Ubuntu; same checks passed on macOS. Includes real foreground pseudo-terminal subprocess cases for default `show()` blocking and two interactive figures drained by one event pump.
- [Hosted Kitty/Xvfb graphical acceptance](https://github.com/josephcourtney/wskr/actions/runs/41362040034): **passed** for existing real-Kitty graphics, resize, multi-figure sheets, paging and owned-viewport regression.

## Qualification boundary

These results **do not qualify** ordinary nonblocking Kitty history placement in a macOS 0/96-line history-reflow experiment. An image attached to a history anchor can leave the visible viewport after reflow, even when its PNG was correctly transmitted. This is not fixed by a protocol fallback and must not be advertised as viewport pinning. Track [issue #31](https://github.com/josephcourtney/wskr/issues/31), [the placement contract](phase3-placement-semantics.md) and the [native macOS harness](phase3-native-macos-acceptance.md). Native macOS blocking multi-figure paging and historical output under yabai likewise still require independent screenshot review.

The opt-in `owned_viewport` alternative already passed six native macOS/yabai sizes/arrangements in [PR #43](https://github.com/josephcourtney/wskr/pull/43); that does not prove history-relative reflow visibility. A third-party REPL/IPython event loop must cooperate by pumping Matplotlib callbacks; wskr cannot safely install an unsolicited stdin reader.
