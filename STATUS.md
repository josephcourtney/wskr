# wskr — Current status

Handoff: [DESIGN](DESIGN.md), [PLAN](PLAN.md), [TODO](TODO.md).

## State — P3 lifecycle follow-up

- **P0–P2 accepted.** `wskr_kitty` uses Agg and native Kitty PNG with bounded queries and scoped image cleanup. P1 offers foreground-owner-only OSC/CSI/Kitty queries and scoped pyplot defaults; no unowned input reads.
- **P3 partial.** Default `show(block=None)` follows Matplotlib foreground/noninteractive blocking; explicit `block=False` preserves history. Explicit `block=True` and `owned_viewport()` use scoped alternate screens. An event pump drains multiple backend figures; owned viewport supports backend-only `refresh_theme(profile)` without input reads. Unattended REPL/IPython loops remain external.
- **Native owned-viewport acceptance:** [PR #43](https://github.com/josephcourtney/wskr/pull/43) records all six 9×2/9×6 scenarios passing in unmanaged Kitty, yabai-floating and genuine BSP, with resize/restore; only `owned_viewport(fig)` is qualified.
- **Installed wheel:** [PR #34](https://github.com/josephcourtney/wskr/pull/34) verifies both Kitty backend selection forms and PNG/SVG exports from outside the checkout. PR #46 Ubuntu/macOS: **381 passed, 3 skipped**; hosted Kitty and wheel checks passed.

## Open boundaries

- [Issue #31](https://github.com/josephcourtney/wskr/issues/31): Native Kitty 0.49.2 can hide or overlap physical history-anchored plots during reflow. Opt-in `WSKR_KITTY_ANCHOR=unicode` passed native 9×2/9×6 yabai and one unmanaged-labelled 9×6 test (96-history). Zero-history, full unmanaged 9×2 stage evidence and other prompt geometries remain open; one post-harness zsh prompt screenshot passes. Nonblocking output is not viewport-pinned.
- P3 updates are in [PR #46](https://github.com/josephcourtney/wskr/pull/46): typed theme refresh, coordinated flush and explicitly downgradable P/Q (`WSKR_KITTY_PARENT=off`). No unsolicited input or background loop.
- P1 has owned Kitty font/size/DPI/opacity probes, OSC-preferred runtime colors and cell-based font/stroke defaults; `use_profile` styles new figures only. Unowned REPLs cannot query safely. No native appearance-query signoff.
- Native history positioning, REPL/IPython scheduling and paging remain P3 gaps; Rich inline and virtual placements remain P4; packaging cleanup remains P5.
- Legacy `RichPlot` sizing can mutate figures; P3 guarantees do not extend to P4.

**Next:** [TODO.md](TODO.md); [P3 follow-up evidence](docs/phase3-lifecycle-acceptance-20261101.md).
