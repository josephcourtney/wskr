# wskr — Immediate Tasks

Phase 1 acceptance tasks: [PLAN.md](PLAN.md), [visual procedure](docs/phase1-visual-procedure.md).

- [ ] Run `just check`, `just phase1`, `just test-tty`, `just test-kitty` on `feature/phase1-terminal-profile-20261020`; fix observed regressions without muting Ruff or `ty`.
- [ ] Capture real Kitty Matplotlib graph output with `just visual-smoke matplotlib`; record actual visibility, clipping, text contrast, and viewport placement.
- [ ] In Kitty run `WSKR_PROTOCOL=kitty just visual-smoke rich`; retain screenshot/output. This old Rich inline transport is experimental and may fail.
- [ ] Confirm the `just visual-smoke noop` Rich fallback preserves panel/table boundaries; no actual image is expected.
- [ ] Determine a safe, caller-owned path for obtaining live terminal colors and optional font/graphics capabilities; do not query shared keyboard input automatically.
- [ ] Classify remaining legacy size-marker warnings truthfully without weakening enforcement policy.
