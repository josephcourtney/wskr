# wskr — Current Status

Handoff; [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 0 evidence](docs/phase0-evidence.md).

## Focus

**Phase 0 acceptance remains open**, but direct Kitty launch and screenshot capture now execute locally.

## Observed local results through 2026-10-20

- Environment, baseline, source/wheel build, isolated wheel smoke and 34 TTY tests previously passed.
- At `bf11996`, `just check` passed syntax but stopped on three formatting errors.
- At `bf11996`, `just test-kitty`: **4 passed, 1 failed**. The captured PNG did not match an old full-window screenshot (`max diff 255`). This is not proof graphics were absent.
- The new logo-content visual check and formatting corrections are **committed but not locally validated**.

## Changes awaiting verification

- Screenshot assertion now checks the recognizable blue/yellow image independently of terminal theme, prompt and position, with positive and negative tests.
- Removed broken inline Kitty debug-image commands; retained screenshot and diagnostics on failure.
- Current `icat` transport, incorrect experimental direct PNG encoding, figure-size override and theme issues remain later-phase work.

## Handoff

Preserve local changes, fast-forward the feature branch, run `just check` and `just test-kitty`. Then exercise standard pyplot and Rich output in Kitty. Close Phase 0 only after those results are recorded.
