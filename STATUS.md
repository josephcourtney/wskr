# wskr — Current Status

Short-horizon handoff; architecture: [DESIGN.md](DESIGN.md); order: [PLAN.md](PLAN.md); tasks: [TODO.md](TODO.md).

## Current focus

**Phase 0 source audit and baseline scaffolding are implemented on `feature/phase0-baseline-20261019`; runtime acceptance is blocked.** This status is source-backed, not a successful local test report. See [phase0 evidence](docs/phase0-evidence.md).

## Completed on this branch

- Fast-forward merged policy-aligned documentation to `main` (`526d71d`).
- Replaced borrowed Cwide `justfile` recipes with wskr-specific nonmutating checks, build, baseline, wheel-smoke and opt-in terminal tests.
- Removed stale Cwide Ruff overrides; suspended strict pytest resource-category enforcement pending test classification.
- Added baseline API/headless export regression tests and diagnostic/wheel-install smoke scripts.
- Inventoried backend names, public API, transport selection, configuration, known limitations and validation gates.

## Known gaps

- Current main Kitty display needs `kitty +kitten icat`. Experimental direct PNG framing is incorrect; Rich and live placement need verification.
- Figures are resized during display even when explicitly sized; `show` destroys figure managers.
- Import changes global `text.usetex`; dark-mode chain mishandles successful light detection; unsafe TTY fallback may emit raw escapes to stdout.
- Sixel/iTerm2 are stubs. Safe TTY/refresh, font/palette defaults and managed redraw remain future-phase work.
- Full `just check`, installed-wheel and real Kitty tests **have not run**: the execution environment lacks repository cloning access, `just` and a live Kitty terminal.

## Handoff

Run the commands in [phase0 evidence](docs/phase0-evidence.md) on a local checkout; record outcomes before closing PLAN Phase 0. Then begin Phase 1 safely. No graphics source module was modified on this branch.
