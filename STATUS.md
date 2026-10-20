# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 0 evidence](docs/phase0-evidence.md).

## Focus

**Phase 0 runtime/packaging baseline is substantially validated; full quality and Matplotlib/Rich visual gates remain open.**

## Verified locally on macOS, October 20

- Environment, baseline diagnostics, wheel/sdist build, isolated wheel install and headless PNG/SVG checks passed in an earlier run.
- TTY tests: **34 passed** (earlier run; test-category warnings remain).
- At commit `5efd931`: `just test-kitty` **5 passed**, including a real Kitty launch/payload and successful screenshot image-content detection. Five size-marker warnings remain.
- `just check` reached Ruff lint after **71 formatted files** and stopped at four reported lint findings. Syntax and formatting passed; typing/full pytest did not run.

## New code awaiting rerun

- Fixed all four reported lint findings on the Phase 0 branch. No graphics transport behavior changed.
- Current `icat` dependency, experimental direct-Kitty framing, implicit figure resize and theme bugs are later-phase issues, not Phase 0 regressions.

## Handoff

Run `just check` and `just test-kitty` on the latest branch head, then perform an actual standard pyplot and RichPlot terminal visual check. Do not infer a full-quality pass or merge/close Phase 0 until the remaining checks are recorded.
