# wskr — Immediate Tasks

Unfinished items only; [PLAN.md](PLAN.md), [Phase 0 evidence](docs/phase0-evidence.md).

- [ ] **P0:** preserve local changes and update `feature/phase0-baseline-20261019`; rerun `just check`, including Ruff, ty and the full pytest suite. Report failures.
- [ ] **P0:** run `uv run pytest -q tests/test_kitty_visual.py` to verify reference screenshot and negative detector cases.
- [ ] **P0:** rerun `just test-kitty`; confirm transport launch, image submission, screenshot capture, and logo-content detection separately.
- [ ] **P0:** manually check actual Kitty output for a normal `MPLBACKEND=wskr_kitty` pyplot figure and a `RichPlot` within a Rich panel/table.
- [ ] **P0 close:** update source evidence and STATUS with new results; only then merge the Phase 0 branch.
- [ ] **P1 prep:** establish tests for safe OSC queries, explicit light mode, resource restoration and geometry/color provenance.
