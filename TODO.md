# wskr — Immediate Tasks

Phase 1 qualification; see [PLAN.md](PLAN.md) and [validation evidence](docs/phase1-validation.md).

- [ ] Preserve the local `just fix` modifications, pull the feature branch, and rerun `just check`. Confirm the five Matplotlib rcParams/rc_context `ty` errors are gone and complete full pytest.
- [ ] Run `just phase1` on the same commit. The previous local run passed **54** and skipped **1**; record new counts.
- [ ] For any remaining failures, provide the failing traceback or `ty` diagnostic; leave unrelated code unchanged.
- [ ] Establish which plotted styles are user-owned by inspecting current and default rcParams before changing dark-theme contrast or figure sizing.
- [ ] Finish truthful test-size classification; defer Kitty Rich inline placements to Phase 2/4.
