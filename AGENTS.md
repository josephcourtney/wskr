# AGENTS.md

## Scope

Cwide is a standalone semantic vocalization library and CLI. Its core interprets written sources and produces structured, source-correlated speech representations; it does not own synthesis, audio timing, playback or an HTTP service. The historical reader source is preserved in [Ruckus `cwide-reader`](https://github.com/josephcourtney/ruckus/tree/main/cwide-reader), not in the cwide repository's semantic package. Follow [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [STATUS.md](STATUS.md), and the [ADRs](docs/adr/) rather than copying the separate Tater Tots runtime proposal.

## Development requirements

- Python 3.13-compatible code; use `uv` and the existing Ruff, `ty`, import-linter and pytest configuration.
- Run `just check` before implementation merges. Report missing tools/external resources accurately; never claim an unrun check passed.
- Use POSIX-style paths in machine-readable output, deterministic test data, and narrowly justified lint exceptions.
- Prefer small typed interfaces, pure transformations and existing maintained libraries; avoid speculative frameworks and event buses.

## Architecture guardrails

- Keep parsing, domain interpretation, policy, and output rendering conceptually separate. Do not flatten typed structure or discard source spans before downstream consumers no longer need them.
- Track source IDs, half-open Unicode-code-point spans, stable semantic identity, and canonical spoken-text offsets. Represent one-to-many, many-to-one, disjoint/reordered, omitted and generated outputs explicitly.
- Assign mapping quality (`exact`, `derived`, `approximate`, `unmapped`) independently of relation type. Record normalization transformations and do not reconstruct precise offsets with `source.find(text)`; prohibit fabricated highlights for uncertain mappings.
- Keep independent `parse`, `vocalize`, and `render` stage interfaces alongside the `Vocalizer` facade; none may require TTS or HTTP.
- Fail closed on unsupported or ambiguous syntax and retain diagnostics and original content. Do not let optional contextual/model resolvers silently change deterministic facts.
- Preserve numeric precision, caller pronunciation overrides, domain-intent distinctions, and current public entry points unless a migration is deliberate and documented.
- Do not emit SSML from parsers/handlers or make core representations depend on a TTS vendor.
- Keep a single registry/dispatch mechanism. Explicit handler registration is acceptable; pluggy/event bus/FastAPI orchestration is not part of the adopted design.
- The preserved `cwide-reader` package is maintained in Ruckus; do not reintroduce it or audio/UI dependencies to Cwide. Ruckus testing is not a core release gate.
- Do not treat `tater_tots` as an imported working implementation. See [docs/tater-tots-reference.md](docs/tater-tots-reference.md) and the [single legacy migration ledger](docs/source-migration-ledger.md). Verify source modules/tests/assets and behavior before final retirement dispositions.

## Tests

Maintain legacy golden fixtures and introduce focused contract tests before IR migrations. Prioritize Unicode/code-point-to-UTF-16 conversion, relation/quality-correct provenance, repeated text, disjoint spans, no fabricated highlights, text/SSML/structured equivalence, fallback behavior, policy variation, versioned serialization, and external handoff composition. Use the size/scope marker system in [TESTING.md](TESTING.md). Audio, models and external applications belong in optional integration tests, not ordinary core tests.

## Documentation and progress

[POLICY.md](POLICY.md) defines document roles:

- `DESIGN.md` — durable architecture/invariants; ADRs explain durable rationale.
- `PLAN.md` — milestones and ordering, not progress.
- `STATUS.md` — brief, accurate current implementation and known gaps.
- `TODO.md` — immediate incomplete execution items; prune as completed.
- `CHANGELOG.md` — meaningful completed changes only.
- `README.md` — accurate current user workflows and clearly marked future capabilities.
- `MASTER_CHECKLIST.md` — dated, evidence-backed hierarchical completion inventory derived from DESIGN/PLAN; not a second task queue. Mark only precise evidenced outcomes.

Update documentation when architecture or public behavior changes. Bump versions for warranted API/format changes. Keep commits logically scoped with rationale and validation notes. These instructions yield to explicit user instructions and `POLICY.md` when in conflict.
