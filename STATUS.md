# wskr — Current status

Short-horizon handoff. [DESIGN](DESIGN.md) · [PLAN](PLAN.md) · [TODO](TODO.md) · [evidence](docs/phase3-validation.md).

## State at 2026-11-01 (P1 appearance completion branch)

- **P0–P2 accepted.** `wskr_kitty` uses Agg and native Kitty PNG with bounded queries and scoped image cleanup. P1 offers foreground-owner-only OSC/CSI/Kitty queries and scoped pyplot defaults; no unowned input reads.
- **P3 remains open.** Ordinary pyplot shows persistent history-resident images; explicit `show(block=True)` provides an alternate-screen session, fitted multi-figure sheets/paging and debounced resize. `flush_events()`/`plt.pause()` drive nonblocking fitted redraw; idle REPL/IPython/pandas redraw is not automatic.
- **Owned live viewport qualified on native macOS:** [PR #43](https://github.com/josephcourtney/wskr/pull/43) records all six 9×2/9×6 scenarios passing in unmanaged Kitty, yabai-floating and genuine BSP, including resize/restore. This qualifies `owned_viewport(fig)`, not history-anchored output.
- **Installed wheel qualified:** [PR #34](https://github.com/josephcourtney/wskr/pull/34) verifies both Kitty backend selection forms and PNG/SVG exports from outside the checkout. PR #44 Ubuntu/macOS quality: **351 passed, 3 skipped**, installed-wheel checks and real-Kitty graphical regression green.

## Open boundaries

- [Issue #31](https://github.com/josephcourtney/wskr/issues/31): Kitty 0.49.2 native 0/96-line history A/B shows scrollback/reflow-sensitive *visibility* in nonblocking fitted displays; the correctly transmitted image may leave the viewport. Historical output is not viewport-pinned. Native history/yabai and older Kitty compatibility remain open.
- New owner-only CSI 14/16 pixel queries and opt-in event-pumped interactive draw coalescing are merged in [PR #44](https://github.com/josephcourtney/wskr/pull/44). No unsolicited terminal I/O or background loop.
- P1 adds queried Kitty font/size/DPI/opacity, OSC-preferred runtime colors and cell-based font/stroke defaults; `use_profile` styles new figures only. Unowned REPLs cannot safely query responses. Native macOS appearance visuals are not independently signed off.
- Existing-figure theme updates, independent placement, bounded scrollback lifetime and idle REPL/IPython/pandas integration remain P3 work. Rich inline panel/table graphics and reusable virtual placements remain P4; dependency/stub cleanup remains P5.
- Legacy `RichPlot` sizing can mutate figures; P3 guarantees do not extend to P4.

**Next:** [TODO.md](TODO.md); keep PTY/Kitty/native evidence separate.
