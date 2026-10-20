# wskr — Immediate Tasks

Only unfinished tasks; see [PLAN.md](PLAN.md) and [Phase 0 evidence](docs/phase0-evidence.md).

- [ ] **P0:** preserve locally modified files (the second `just fix` changed three sources); pull the latest feature branch, run `uv sync` and `just check`. Record first failing step plus ty and pytest outcomes.
- [ ] **P0:** rerun `just baseline`, `just build`, `just wheel-smoke` and `just test-tty` on latest commit.
- [ ] **P0 Kitty:** run `just test-kitty`; report the independent Kitty launch/payload smoke pass/fail and the Yabai screenshot test pass/fail/**skip** separately.
- [ ] **P0 screenshots:** if automated screenshots are needed, make the Yabai service available and rerun; otherwise record a clearly identified manual Kitty visual inspection, **not** a mock result.
- [ ] **P0 completion:** reconcile `docs/phase0-evidence.md` / `STATUS.md` with verified results before merging the implementation branch.
- [ ] **P1 prep:** add safe OSC/color, terminal descriptor and provenance regression tests before changing core graphics rendering.
