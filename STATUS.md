# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 0 evidence](docs/phase0-evidence.md).

## Current focus

**Phase 1 implementation is in progress on `feature/phase1-terminal-profile-20261020`; local verification is pending.** Phase 0 is merged into main.

## Implemented on the feature branch

- Immutable, provenance-aware terminal geometry and optional OSC 4/10/11 color profile; unknown font/DPI/opacity remain unknown.
- Bounded, opt-in owned-input OSC query with response matching, unrelated-byte routing, timeouts and termios restoration.
- Pure terminal-derived figure/style defaults and initial pyplot-backend figure size; explicit sizing and nondefault rcParams take precedence.
- Importing `wskr` no longer changes `text.usetex`. Light-mode `False` is definitive; default detection no longer interrogates shared TTY input.
- Focused unit and PTY regression tests plus `just phase1`.

## Remaining gaps

- **Not yet validated on macOS**: `just phase1`, `just check`, `just test-tty`, `just test-kitty`. Do not assume the new code passes.
- Automatic live OSC colors still require a caller-owned input session; no background reading of interactive keystrokes is allowed.
- Artist styling, runtime theme/geometry refresh and display-time explicit-size preservation are incomplete; direct Kitty protocol remains Phase 2/3 work.
- Ordinary pyplot/Rich visual verification and pytest size classification remain outstanding.

## Handoff

Run the quality gates and report any Ruff, ty, pytest or live-Kitty failures before merging or declaring the Phase 1 gate complete.
