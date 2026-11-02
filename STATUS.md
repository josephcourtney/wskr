# wskr — Current status

Handoff: [DESIGN](DESIGN.md), [PLAN](PLAN.md), [TODO](TODO.md).

## State — P3 lifecycle follow-up

- **P0–P2 accepted.** `wskr_kitty` uses Agg and native Kitty PNG with bounded queries and scoped image cleanup. P1 provides owned terminal queries and scoped pyplot defaults; no foreign input reads.
- **P3 partial.** Default `show(block=None)` follows Matplotlib foreground/noninteractive blocking; explicit `block=False` preserves history. Explicit `block=True` and `owned_viewport()` use scoped alternate screens. An event pump drains multiple backend figures; owned viewport supports backend-only `refresh_theme(profile)` without input reads. REPL pump requires host cooperation.
- **Native owned-viewport acceptance:** [PR #43](https://github.com/josephcourtney/wskr/pull/43) records all six 9×2/9×6 scenarios passing in unmanaged Kitty, yabai-floating and genuine BSP, with resize/restore; only `owned_viewport(fig)` is qualified.
- **Wheel:** [PR #34](https://github.com/josephcourtney/wskr/pull/34) verifies both Kitty backend selection forms and PNG/SVG exports from outside the checkout. PR #58: **403 passed, 3 skipped** on Ubuntu/macOS; hosted Kitty passed.

## Open boundaries

- [Issue #31](https://github.com/josephcourtney/wskr/issues/31): Physical history anchors can overlap/offscreen plots. Opt-in `WSKR_KITTY_ANCHOR=unicode` passed native 9×2/9×6 yabai and one unmanaged-labelled 9×6 test (96-history). Zero-history, full unmanaged 9×2 stage evidence and other prompt geometries remain open; one returned zsh prompt passes. Nonblocking output is not viewport-pinned.
- P3 implements typed theme refresh, coordinated flush and P/Q fallback (`WSKR_KITTY_PARENT=off`) without foreign input or background loops.
- P1 has owned Kitty font/size/DPI/opacity probes, OSC-preferred runtime colors and cell-based font/stroke defaults; `use_profile` styles new figures only. Unowned REPLs cannot query safely; native appearance-query signoff pending.
- Opt-in Unicode 2-figure native test: one pump updates both figures; independent `plt.close` deletes only owned images; child exit remains clean. Blank rows persist. Native 8-stage blocking navigation/resize/alt-screen restore visually passes (2240→868→2548 px); measured page capacity did not change. REPL scheduling and history controls remain P3 gaps.
- Legacy `RichPlot` sizing can mutate figures; P3 guarantees do not extend to P4.

**Next:** [TODO.md](TODO.md); [P3 follow-up evidence](docs/phase3-lifecycle-acceptance-20261101.md).
