# wskr — Immediate Tasks

See [Phase 1 validation](docs/phase1-validation.md) and [automated evidence capture](docs/phase1-evidence-bundles.md).

- [ ] Fetch the feature branch and run `just check` after the evidence-runner formatting correction. If successful, rerun `just evidence` for one fully green run-specific ZIP.
- [ ] If `just check` reveals lint/`ty`/pytest errors previously hidden by formatting, preserve the complete failure log from the ZIP and repair those specific issues.
- [ ] Decide whether a dark terminal with explicit `figure.facecolor=none`, black text and `savefig.transparent=True` should receive only an opt-in contrast adaptation. Never silently override user `rcParams`.
- [ ] Implement safe caller-owned runtime terminal-color and optional graphics capability discovery; keep unavailable measurements explicit.
- [ ] Defer real Rich Kitty inline graphics/placement to Phase 2/4. Classify legacy pytest test-size warnings truthfully.
