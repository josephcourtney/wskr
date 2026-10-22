# wskr — Current Status

Handoff: [DESIGN](DESIGN.md), [PLAN](PLAN.md), [TODO](TODO.md), [Phase 2 acceptance](docs/phase2-validation.md).

## Milestones

**Phase 2 accepted: native Kitty graphics and managed image placements.** Code qualified at `d615ec08` in [PR #18](https://github.com/josephcourtney/wskr/pull/18); Phase 1 was previously integrated through [PR #17](https://github.com/josephcourtney/wskr/pull/17).

Hosted Ubuntu/macOS quality checks passed **229 full tests, 3 skipped**, with **54 focused Phase 2 passes**. Real Kitty Linux/Xvfb screenshots passed for physical/virtual placements. Independently reviewed **local macOS 27.0.1/Python 3.14** evidence at clean merge SHA `dc3306b` confirmed the same test counts plus **5 real-Kitty passes, five screenshots, and 21/21 matching bundle checksums**. See [Phase 2 acceptance](docs/phase2-validation.md).

## Current boundaries

- `wskr_kitty` and `WSKR_PROTOCOL=kitty` select the **native** PNG `f=100` transport; external `kitty icat` is available through `kitty_legacy` for comparison.
- Native transport supports scoped image uploads, physical/virtual placement, deletion, input-owned capability queries and redirected-output rejection.
- Real Rich image composition remains **unimplemented**: Rich text diagnostics remain intentional, and protocol-level Unicode placeholders are prepared for Phase 4.
- **Native macOS Kitty GUI verified:** local physical and Unicode virtual bar charts rendered; Rich panel/table fallbacks stayed intact. Full Rich inline graphics are still Phase 4.

## Next focus

**Phase 3:** Matplotlib figure ownership, lifecycle, viewport fitting and resize/replacement without silently rewriting user-provided styling. Local Phase 2 evidence also shows **severe vertical clipping**: the 1800×1800 user-configured Matplotlib figure overflows a 1664×952 viewport, losing the upper half, title and some labels. Earlier evidence also showed small-window/left-edge clipping and low-contrast labels on transparent backgrounds. See [TODO](TODO.md) and [ADR-002](docs/adr/0002-terminal-measured-defaults.md).

Phase 4 will connect Rich's cell allocation and virtual-placeholder composition to the accepted shared transport.
