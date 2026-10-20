# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 evidence](docs/phase1-validation.md).

## Current focus

**Phase 1 terminal-profile and TTY safety tests now pass locally.** The feature branch is not merged; style/visual integration remains open.

## Verified on macOS — October 20, 2026, `a2f12f5`

- `just check`: **PASS** — syntax, Ruff format/lint, `ty`, pytest **181 passed, 3 skipped**.
- `just phase1`: **45 passed, 1 opt-in TTY skip**.
- `just test-tty`: **35 passed**, including the earlier problematic TTY/PTY path; no `tcdrain` hang.
- `just test-kitty`: **5 passed**, including live image transmission and screenshot-content detection.
- Warnings are test-size classifications (**137** in full pytest; **26** TTY; **5** Kitty) and the Phase 1 medium-size distribution advisory. No test failures were reported.
- Branch head at the time of execution: `a2f12f5`; results do not imply later commits were rerun.

## Implemented, outstanding and risks

- Immutable provenance-aware profile, bounded caller-owned OSC queries, strict color parsing, decisive light-mode detection, pure defaults and no import-time rcParams mutation.
- Initial terminal-derived figure dimensions work in unit tests; terminal-derived artist/font/palette application still needs integration and explicit-style tests.
- Ordinary stock Matplotlib/Rich plots have **not** been visually verified in Kitty; image-logo checks do not establish layout correctness.
- Display-time figure resizing, runtime refresh and unsupported protocol paths remain later-phase work. Legacy test-size markers are incomplete.

## Handoff

Complete safe style/default integration and real plot/Rich visual characterization before closing Phase 1. Record subsequent checks against their exact branch commit; do not merge on test counts alone.
