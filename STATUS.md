# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 validation](docs/phase1-validation.md), [evidence instructions](docs/phase1-evidence-bundles.md).

## Current focus

**Phase 1 code is implemented and the targeted checks pass, but the latest full quality gate failed formatting.** Phase 0 is merged into `main`; Phase 1 remains on `feature/phase1-terminal-profile-20261020` in [draft PR #17](https://github.com/josephcourtney/wskr/pull/17).

## Latest macOS evidence — October 21, 2026, `a1a722e`

- `just evidence` from a clean checkout generated a complete ZIP; 14/14 artifact checksums matched.
- `just check` **FAILED at Ruff format** (`scripts/phase1_evidence.py:290:23`); lint, `ty` and full pytest were not reached.
- `just phase1`: **55 passed, 1 skipped**; `just test-tty`: **35 passed**; `just test-kitty`: **5 passed**.
- All three real Kitty screenshots were captured and reviewed at 1272×1381. Standard Matplotlib lines/grid/legend render; dark transparent margins make black title/labels difficult to read. Rich Kitty shows the expected inline-unavailable diagnostic; Rich noop displays the in-layout fallback.

## Latest changes — unverified on macOS

- Replaced the collector's multiline conditional with explicit branches to remove the observed Ruff formatter failure. This is not yet a passing `just check` result.
- ADR-002 preserves explicit user styling; the new transparent/300-DPI regression passed within `just phase1`.
- Prior fully passing `just check`: `ab3ad41` (194 passed, 3 skipped). This is **not** evidence for the latest head.

## Known limits and next action

- Automatic safe live OSC color discovery, native Kitty graphics, Rich inline placement and display-time resizing remain unimplemented or deferred to later phases.
- Run `just evidence` on the latest clean feature head, review all command results and captured screenshots, and record the exact tested commit. **Do not merge until the full gate is green.** See [TODO.md](TODO.md).
