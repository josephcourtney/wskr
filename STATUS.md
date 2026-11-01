# wskr — Current status

Handoff: [DESIGN](DESIGN.md), [PLAN](PLAN.md), [TODO](TODO.md), [evidence](docs/phase3-validation.md).

## State — P3 lifecycle follow-up

- **P0–P2 accepted.** `wskr_kitty` uses Agg and native Kitty PNG with bounded queries and scoped image cleanup. P1 offers foreground-owner-only OSC/CSI/Kitty queries and scoped pyplot defaults; no unowned input reads.
- **P3 partial.** Default `show(block=None)` follows Matplotlib foreground/noninteractive blocking; explicit `block=False` preserves history. Explicit `block=True` and `owned_viewport()` use scoped alternate screens. An event pump drains multiple backend figures; owned viewport supports backend-only `refresh_theme(profile)` without input reads. Unattended REPL/IPython loops remain external.
- **Owned live viewport qualified on native macOS:** [PR #43](https://github.com/josephcourtney/wskr/pull/43) records all six 9×2/9×6 scenarios passing in unmanaged Kitty, yabai-floating and genuine BSP, with resize/restore; only `owned_viewport(fig)` is qualified.
- **Installed wheel qualified:** [PR #34](https://github.com/josephcourtney/wskr/pull/34) verifies both Kitty backend selection forms and PNG/SVG exports from outside the checkout. PR #45 quality: **372 passed, 3 skipped** on Ubuntu/macOS, installed-wheel and hosted real-Kitty regression pass.

## Open boundaries

- [Issue #31](https://github.com/josephcourtney/wskr/issues/31): Kitty 0.49.2 native 0/96-line history A/B shows scrollback/reflow-sensitive *visibility* in nonblocking fitted displays; the correctly transmitted image may leave the viewport. Historical output is not viewport-pinned. Native history/yabai and older Kitty compatibility remain open.
- P3 updates are in [PR #46](https://github.com/josephcourtney/wskr/pull/46): typed theme refresh, coordinated flush and explicitly downgradable P/Q (`WSKR_KITTY_PARENT=off`). No unsolicited input or background loop.
- P1 has owned Kitty font/size/DPI/opacity probes, OSC-preferred runtime colors and cell-based font/stroke defaults; `use_profile` styles new figures only. Unowned REPLs cannot safely query responses. New appearance probes lack native macOS visual signoff.
- Native scrollback reflow/prompt visibility, historical image positioning, unowned REPL/IPython scheduling and native paging acceptance remain P3 qualification gaps; Rich inline tables and panels remain P4. Rich inline panel/table graphics and reusable virtual placements remain P4; dependency/stub cleanup remains P5.
- Legacy `RichPlot` sizing can mutate figures; P3 guarantees do not extend to P4.

**Next:** [TODO.md](TODO.md); keep PTY/Kitty/native evidence separate.
