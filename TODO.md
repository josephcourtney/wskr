# wskr — Immediate Tasks

Only pending tasks. Phase ordering: [PLAN.md](PLAN.md). Recorded code findings: [Phase 0 evidence](docs/phase0-evidence.md).

- [ ] **P0 acceptance:** on the feature branch run `uv sync` and `just check`; record any existing formatting/lint/type/test failure without applying unrelated fixes.
- [ ] **P0 acceptance:** run `just baseline`, `just build` and `just wheel-smoke`; record installed metadata, headless exports and package-install outcome.
- [ ] **P0 acceptance:** run `just test-tty` and capture terminal query/restoration failures; ensure opt-in tests are not silently skipped.
- [ ] **P0 acceptance:** in a real Kitty session run `just test-kitty` plus a normal `MPLBACKEND=wskr_kitty` plotting script and RichPlot table; capture observed placement/geometry and distinguish GUI prerequisites from successful assertions.
- [ ] **P0 closure:** classify results as passed/failed/skipped/blocked in `docs/phase0-evidence.md` and update `STATUS.md`; do not close Phase 0 solely from source inspection.
- [ ] **P1 next:** introduce safe terminal probing tests for OSC framing, a definitive light (`False`) response, timeouts, descriptor lifecycle and measurement provenance before modifying transport or theme behavior.
