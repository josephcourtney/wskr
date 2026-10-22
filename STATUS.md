# wskr — Current Status

Handoff: [DESIGN](DESIGN.md), [PLAN](PLAN.md), [TODO](TODO.md), [Phase 2 acceptance](docs/phase2-validation.md).

## Milestones

**Phase 2 accepted: native Kitty graphics and managed image placements.** Code qualified at `d615ec08` in [PR #18](https://github.com/josephcourtney/wskr/pull/18); Phase 1 was previously integrated through [PR #17](https://github.com/josephcourtney/wskr/pull/17).

Hosted Ubuntu and macOS 15 quality jobs passed syntax, Ruff formatting/lint, `ty`, and **229 full pytest passes with 3 skips**. The focused Phase 2 suite passed **54 tests** on each platform. Real Kitty under Xvfb also passed independently inspected screenshots for **physical and Unicode virtual image placements**. Evidence and artifacts: [docs/phase2-validation.md](docs/phase2-validation.md).

## Current boundaries

- `wskr_kitty` and `WSKR_PROTOCOL=kitty` select the **native** PNG `f=100` transport; external `kitty icat` is available through `kitty_legacy` for comparison.
- Native transport supports scoped image uploads, physical/virtual placement, deletion, input-owned capability queries and redirected-output rejection.
- Real Rich image composition remains **unimplemented**: Rich text diagnostics remain intentional, and protocol-level Unicode placeholders are prepared for Phase 4.
- **No macOS Kitty GUI claim:** macOS passed PTY and full code checks; real graphical screenshots were generated with hosted Linux Kitty.

## Next focus

**Phase 3:** Matplotlib figure ownership, lifecycle, viewport fitting and resize/replacement without silently rewriting user-provided styling. Known Phase 1 evidence includes small-window clipping, left-edge tick clipping and low-contrast labels on explicitly transparent backgrounds. See [TODO](TODO.md) and [ADR-002](docs/adr/0002-terminal-measured-defaults.md).

Phase 4 will connect Rich's cell allocation and virtual-placeholder composition to the accepted shared transport.
