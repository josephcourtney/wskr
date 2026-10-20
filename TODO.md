# wskr — Immediate Tasks

Only unfinished items. See [PLAN.md](PLAN.md) and [Phase 0 evidence](docs/phase0-evidence.md).

- [ ] **P0:** preserve any local uncommitted changes, pull current feature branch, run `uv sync` and `just check`; report Ruff/ty/pytest outcomes.
- [ ] **P0:** repeat `just baseline`, `just build`, `just wheel-smoke` and `just test-tty` against the updated commit.
- [ ] **P0:** rerun `just test-kitty`; verify host-side Yabai window lookup, payload completion, screenshot and image comparison separately.
- [ ] **P0:** run normal `MPLBACKEND=wskr_kitty` pyplot and a RichPlot table/panel in live Kitty; document output and geometry.
- [ ] **P0 closure:** update Phase 0 evidence and STATUS with observed pass/fail/skip; do not count mocked screenshots as live evidence.
- [ ] **P1 prep:** test safe OSC probing, valid light-mode detection, descriptor restoration and geometry/color provenance.
