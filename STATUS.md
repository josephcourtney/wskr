# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 evidence](docs/phase1-validation.md).

## Current focus

**Phase 1 safety and quality checks pass locally; actual plotting integration is not yet visually accepted.** Work remains on `feature/phase1-terminal-profile-20261020`.

## Verified on macOS — October 20, 2026, `d9b1e32`

- `just check`: syntax, Ruff and `ty` passed; full pytest **181 passed, 3 skipped**, **137 size-marker warnings**.
- `just phase1`: **45 passed, 1 opt-in skip**.
- `just test-tty`: **35 passed** without the earlier `tcdrain` hang.
- `just test-kitty`: **5 passed**, verifying live Kitty image submission and logo detection.
- Ordinary `MPLBACKEND=wskr_kitty` `plt.show()` exited 0 with no captured text. **On-screen image presence is unknown** without a screenshot/observation.
- `RichPlot` with the default `noop` protocol produced an empty panel and warning text; **actual image display failed** for this configuration.

## Subsequent remedy (not yet locally tested)

- A `noop` Rich transport now produces a visible text fallback within Rich layout, without attempting PNG uploads or printing out-of-band warnings. Unit coverage added.

## Remaining acceptance

- Test the new fallback and complete terminal-owned figure/artist defaults while preserving explicit user rcParams/style.
- Inspect stock pyplot and Rich output in a real Kitty window. Rich rendering requires an explicitly selected transport; its Kitty virtual placement remains experimental.
- Display-time size, resize and Rich placeholder/protocol lifecycle work is planned for later phases.

## Handoff

Repeat `just check`, `just test-tty` and `just test-kitty` after changes. Do not merge or call Phase 1 complete solely from the successful logo-based Kitty suite.
