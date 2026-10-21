# wskr — Immediate Tasks

See [Phase 2 validation](docs/phase2-validation.md), [PLAN Gate P2](PLAN.md), [ADR-003](docs/adr/0003-kitty-transport-and-placement.md).

- [ ] Review `tests/test_kitty_native.py`, `tests/test_kitty_pty_transactions.py` and `tests/test_phase2_visual_smoke.py` against strict Ruff 0.15.2 formatting/lint and `ty`; neither executable is available in the present Linux environment. Keep changes narrowly scoped to verified findings.
- [ ] Obtain a complete repository test run (`just check`, `just phase2`) from any compatible environment when available. The Linux isolated exact-code test subset currently passes 14 tests, but is not a whole-project gate.
- [ ] Independently qualify real Kitty `f=100` transfer, physical placement, `U=1` Unicode virtual placement, response behavior and scoped image deletion. The evidence collector prepares **five isolated window screenshots** plus references; their existence must not count as automatic visual success.
- [ ] Update [draft PR #18](https://github.com/josephcourtney/wskr/pull/18) with any failures and further corrections; preserve Gate P2 as incomplete until integration evidence justifies acceptance. Do not block additional review/refinement on availability of the user's Mac.
- [ ] Keep the Phase 3 Matplotlib resize/figure-lifecycle and contrast/clipping issues separate. Defer true Rich panels/tables via virtual placements and allocated-cell sizing to Phase 4.
