# wskr — Current Status

Short handoff; see [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md) and [TODO.md](TODO.md).

## Focus

**Phase 0 acceptance remains open.** Two macOS ARM64 runs are recorded in [Phase 0 evidence](docs/phase0-evidence.md).

## Established on macOS

- `uv sync`, `just baseline`, `just build` and `just wheel-smoke` passed for `wskr 0.0.17` (first run).
- `just test-tty`: **34 passed**, with 34 test-category warnings (first run).
- `just check`: format failures on first attempt; after `just fix` only one embedded-script line-length error remained. ty/full pytest not yet reached.
- `just test-kitty`: 3 tests passed; real screenshot case failed **before capture**, first at startup-file polling, then at unavailable `yabai` window query.

## Latest branch work — awaiting rerun

- Repaired script lint/format issues, baseline tests and broad optional-command error handling.
- GUI screenshot now preflights the Yabai service; unavailability causes an explicit **skip**, not a fabricated display pass.
- Added a separate real Kitty launch/payload smoke independent of Yabai.
- Current `icat` transport, incorrect experimental PNG framing and auto-theme/sizing issues remain planned later-phase work.

## Handoff

Protect locally dirty files and rerun [Phase 0 checks](docs/phase0-evidence.md). **Only a successful local `just check` and observed real Kitty results can close the remaining acceptance gates.**
