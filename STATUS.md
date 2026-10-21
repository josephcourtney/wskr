# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 2 validation](docs/phase2-validation.md).

## Active work

**Phase 2 implementation staged on `feature/phase2-native-kitty-20261021`; qualification pending.** Phase 1 was merged into `main` in [PR #17](https://github.com/josephcourtney/wskr/pull/17) after clean macOS validation at code SHA `5e35aa6`.

## Implemented on the Phase 2 branch

- Pure Kitty PNG `f=100` Base64/chunk codec, ACK parsing and scoped deletion/placement control.
- Serialized, deadline-bounded terminal writer and explicit input-owner capability query; raw graphics refused on redirected stdout.
- Managed random-ID image uploads, physical and virtual placements, replacement and disposal. `kitty` and stock `wskr_kitty` select the native transport; `kitty_legacy` retains `icat` for comparison.
- Protocol-owned Unicode placeholder/diacritic encoder for eventual Rich rendering; **Rich inline placement remains intentionally unavailable**.
- Deterministic tests and `just phase2` qualification; integrated collector now includes Phase 2 tests.

## Verification and limitations

**Not verified on macOS or real Kitty at the Phase 2 head.** Run `just check`, `just phase2`, `just test-tty` and `just evidence`, then inspect archive/checksums and screenshots before deciding the merge. Phase 1's 200/55/35/5 pass counts do not apply to this new code.

Terminal `TERM` is a hint, not proof of negotiated graphics; `probe` requires explicit input ownership. Phase 3 retains Matplotlib lifecycle and viewport-clipping/contrast defects. Phase 4 retains Rich's `ConsoleOptions` fitting and true virtual inline placement. See [TODO.md](TODO.md).
