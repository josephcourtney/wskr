# Contributor and Agent Instructions — wskr

## Project scope

wskr is a terminal-native Matplotlib backend with optional Rich integration. The adopted architecture is in [DESIGN.md](DESIGN.md), execution order in [PLAN.md](PLAN.md), current state in [STATUS.md](STATUS.md) and immediate work in [TODO.md](TODO.md). Do not treat the planned direct-Kitty or auto-theme features as already implemented.

**[POLICY.md](POLICY.md) takes precedence for documentation roles and git history.** Architecture rationale belongs in numbered [ADRs](docs/adr/); completion evidence belongs in commits, STATUS and the curated changelog.

## Engineering boundaries

- Preserve ordinary Matplotlib APIs: `plt.subplots`, figure/axes methods, `rcParams`, `plt.show`, `fig.savefig` and installed backend selection.
- Keep terminal I/O, Kitty protocol/placement, Matplotlib Agg rendering and optional Rich composition separate. Domain-specific plots and GridSpec helpers remain outside the backend.
- No terminal I/O or global `rcParams` mutations on package import in the **target** implementation. Respect user-owned styles and dimensions.
- Terminal probing is bounded and safe: redirect/TTY detection, input isolation, descriptor/termios restoration and explicit failure paths. Never send raw graphics escapes to non-TTY stdout.
- Do not claim Sixel/iTerm2 support while the backends are stubs; do not silently turn failed displays into successful no-ops.
- Do not copy code from other repositories without checking compatible licensing. wskr declares GPL-3.0-only.
- Preserve useful public imports and backend names, or document compatibility transitions deliberately.

## Tools and validation

- Use `uv` for Python environment, dependencies, builds and running tools; current `pyproject.toml` targets Python >=3.13,<3.15.
- Use the repository Ruff, `ty` and pytest/coverage configuration once commands are confirmed to point at **wskr**. Before relying on `just check` or borrowed build recipes, inspect and repair their Cwide-specific assumptions.
- Add deterministic tests for protocol parsing, TTY failure/safety, Matplotlib lifecycle and export; use PTY tests for terminal interactions and separate opt-in **real Kitty** tests for on-screen correctness.
- Report actual executed commands and results. Do not claim checks passed when the environment cannot run them; do not confuse mocked screenshots with a live Kitty pass.
- Keep dependency additions narrow and justified. Do not introduce GitHub Actions as a required workflow.

## Documentation workflow

- `DESIGN.md` — durable requirements/invariants only; no progress, chronological narrative or step-by-step plans.
- `PLAN.md` — migration phases and ordering; no ongoing status bookkeeping.
- `STATUS.md` — compact, high-signal current implementation and blockers (normally <=50 lines / ~2500 characters).
- `TODO.md` — only pending, near-term, concrete tasks; remove completed items rather than preserving an archive.
- `CHANGELOG.md` — notable **completed** user-visible changes, not plans or per-commit minutiae.
- `README.md` — workflows supported **today**, with planned capabilities clearly marked.
- `docs/adr/` — dated, numbered decisions with context, alternatives and consequences.

Use concise imperative conventional commit subjects with bodies for nontrivial changes, citing design invariants or ADR IDs where useful. Keep changes logically scoped; document failures and external validation gaps without inventing successful results.
