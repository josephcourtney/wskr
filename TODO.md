# wskr — Immediate Tasks

Only unfinished Phase 1 work. See [PLAN.md](PLAN.md) and [Phase 1 evidence](docs/phase1-validation.md).

- [ ] Preserve the local uncommitted Ruff autofix, update `feature/phase1-terminal-profile-20261020`, and rerun `just check` through Ruff, `ty` and full pytest.
- [ ] On the same updated commit, repeat `just phase1`, `just test-tty` and `just test-kitty`; record exact pass/skip counts.
- [ ] Inspect a real `MPLBACKEND=wskr_kitty` plot and `RichPlot` within a Rich panel/table for viewport size, style and placement.
- [ ] Integrate terminal-derived font/palette/artist defaults while preserving explicit user styling and rcParams.
- [ ] Add resize/refresh and input ownership tests; avoid unsafe automatic queries.
- [ ] Classify remaining legacy/GUI tests by actual dependency/size, without suppressing warning or altering enforcement to hide failures.
