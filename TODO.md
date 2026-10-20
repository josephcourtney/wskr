# wskr — Immediate Tasks

Pending execution work; [PLAN.md](PLAN.md) and [Phase 0 evidence](docs/phase0-evidence.md).

- [ ] **P0 checks:** update `feature/phase0-baseline-20261019` and run `just check`; record ty warnings/errors and full pytest results. Correct only remaining observed failures.
- [ ] **P0 Kitty regression:** rerun `just test-kitty` after type fixes; retain the 5-pass real Kitty result.
- [ ] **P0 visual:** inspect stock `MPLBACKEND=wskr_kitty` pyplot and `RichPlot` inside a real Rich panel/table.
- [ ] **P0 close:** record all acceptance results in `docs/phase0-evidence.md`, prune STATUS/TODO, and merge only when verified.
- [ ] **P1 prep:** add tests for safe OSC queries, light-theme detection, descriptor restoration, and terminal-value provenance.
