# wskr — Current status

This is a short-horizon handoff, not a development history. Requirements: [DESIGN.md](DESIGN.md); execution: [PLAN.md](PLAN.md); immediate work: [TODO.md](TODO.md); evidence: [Phase 3](docs/phase3-validation.md).

## State at 2026-11-01 (`main` `823ecc7`)

- **P0–P2 accepted.** The installed `wskr_kitty` backend uses Matplotlib Agg and direct Kitty PNG transport, with bounded TTY queries and session-scoped image/placement cleanup. Phase 1 guarantees safe *optional* interrogation, not automatic live appearance detection.
- **P3 remains open.** Ordinary pyplot shows persistent history-resident images; explicit `show(block=True)` provides an alternate-screen session, fitted multi-figure sheets/paging and debounced resize. `flush_events()`/`plt.pause()` drive nonblocking fitted redraw; idle REPL/IPython/pandas redraw is not automatic.
- **Owned live viewport qualified on native macOS:** [PR #43](https://github.com/josephcourtney/wskr/pull/43) records all six 9×2/9×6 scenarios passing with unmanaged Kitty, yabai-floating and genuine vertical BSP, including resize, image visibility and screen restoration. This qualifies `owned_viewport(fig)`, **not** ordinary history-anchored output.
- **Installed wheel qualified:** [PR #34](https://github.com/josephcourtney/wskr/pull/34) verifies both Kitty backend selection forms and PNG/SVG exports from outside the checkout. Post-merge Ubuntu/macOS quality: **337 passed, 3 skipped**; these are recorded CI outcomes, not reruns in this handoff.

## Open boundaries

- [Issue #31](https://github.com/josephcourtney/wskr/issues/31): Kitty 0.49.2 native 0/96-line history A/B shows scrollback/reflow-sensitive *visibility* in nonblocking fitted displays; the correctly transmitted image may leave the viewport. Historical output is not viewport-pinned. Native 9×6/yabai history acceptance and older Kitty compatibility are unresolved.
- Terminal-derived appearance is incomplete: ordinary pyplot does not own input to query OSC colors/palette; Kitty font/DPI/opacity and theme-change refresh are unavailable or unqualified. Explicit Matplotlib styling must remain authoritative.
- General independent positioning, bounded scrollback lifetime, idle REPL/IPython/pandas and theme updates remain P3 work. Rich inline panel/table graphics and reusable virtual placements remain P4; dependency/stub cleanup remains P5.
- The old `RichPlot` sizing path can mutate figure size; do not infer P3 guarantees apply to the uncompleted P4 adapter.

**Next:** follow [TODO.md](TODO.md). Validate code changes with `just check` and dedicated real-Kitty screenshots; distinguish hosted Linux Kitty, native macOS GUI, and synthetic PTY evidence.
