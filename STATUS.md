# wskr — Current Status

Short handoff; architecture: [DESIGN.md](DESIGN.md); phases: [PLAN.md](PLAN.md); tasks: [TODO.md](TODO.md).

## Focus

**Phase 0 partly validated; acceptance remains open.** See [Phase 0 evidence](docs/phase0-evidence.md).

## Verified in local logs (2026-10-20, commit `064fbc4`)

- `uv sync` and `just baseline` passed (Python 3.14.0, Matplotlib 3.11.2).
- `just build` and isolated `just wheel-smoke` passed for `wskr 0.0.17`.
- `just test-tty`: **34 passed**, with 34 size-marker warnings.
- `just check` failed on formatting; subsequent `just fix` left Ruff findings.
- `just test-kitty` timed out waiting for a startup window-ID file, before screenshot comparison.

## Latest branch remediation (not yet rerun)

- Addressed reported lint/format categories and clarified baseline script typing.
- Made an explicit long GUI test timeout possible and removed shell-driven window-ID discovery.
- Kept source graphics behavior unchanged; current `icat` dependency, incomplete direct Kitty encoding, import-time global rcParams mutation, explicit-size overwrite and theme flaw remain future-phase work.

## Handoff

Preserve the locally dirty tree before pulling. Re-run [Phase 0 checks](docs/phase0-evidence.md) and record exact outcomes. **Do not close Phase 0 or merge this branch as fully validated until acceptance gates are satisfied.**
