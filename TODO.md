# wskr — Immediate Tasks

Pending tasks only; see [PLAN.md](PLAN.md) and [Phase 0 evidence](docs/phase0-evidence.md).

- [ ] **P0 quality:** pull the latest feature branch, run `just check`, and record Ruff, ty and full pytest outcomes; repair only observed remaining failures.
- [ ] **P0 regressions:** run `uv run pytest -q tests/test_kitty_visual.py` and `just test-kitty` after the lint refactor; confirm no regression to live image-content detection.
- [ ] **P0 visual:** manually inspect `MPLBACKEND=wskr_kitty` pyplot output and a `RichPlot` in a Rich table/panel; document appearance and placement.
- [ ] **P0 close:** reconcile [Phase 0 evidence](docs/phase0-evidence.md) and STATUS with final results; merge only once accepted.
- [ ] **P1 preparation:** add tests for OSC probing, definite light-theme result, TTY resource cleanup, and geometry/color provenance.
