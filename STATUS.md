# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md).

## Current focus

**Phase 1 terminal profile is implemented on `feature/phase1-terminal-profile-20261020`, but acceptance remains open.** Baseline Phase 0 is merged into `main`.

## Mac validation on October 20, 2026 (at `d10040b`)

- `uv sync` passed and the real Kitty suite **passed 5 tests**.
- `just phase1`: **43 passed, 2 failed, 1 skipped**. Both failures were macOS PTY comparisons differing only in kernel-managed `PENDIN`.
- `just test-tty`: timed out in the legacy `tcdrain` call.
- `just check`: after local format/autofix, Ruff reported **19 remaining errors**; `ty` and full pytest were not reached.
- The user committed/pushed Ruff's formatting changes as `d10040b`.

## Remediation committed since that run — unverified

- Compare all app-managed terminal modes while excluding only the macOS `PENDIN` state bit; remove legacy query's blocking `tcdrain`.
- Factor bounded OSC transactions into write/read/framing helpers, retaining a single deadline and restoring termios before close.
- Replace literal magic comparisons, document validation hooks, and tighten negative-test assertions.
- Add a no-drain regression test and classify Phase 1 test sizes; do not suppress existing lint policy.

## Remaining

- **No rerun of the updated branch** has established a clean `just phase1`, `just check`, or `just test-tty`. The prior 5-test live Kitty pass does not apply automatically to changed code.
- Automatic style integration, live resize and ordinary pyplot/Rich screenshot validation remain unfinished.

## Handoff

Rerun the local quality and terminal gates on the feature branch. Record any remaining failures before merging Phase 1.
