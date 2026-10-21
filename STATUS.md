# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 validation](docs/phase1-validation.md), [Evidence bundles](docs/phase1-evidence-bundles.md).

## Current focus

**The automated evidence capture works; a formatting-only quality failure was reported and repaired, but the updated branch is not yet validated.** Feature branch `feature/phase1-terminal-profile-20261020`; `main` unchanged.

## Latest macOS evidence — October 21, 2026, `2dbb65f`

- `just evidence` generated a complete run-specific ZIP and **3/3 separate, scoped Kitty screenshots** (553 × 1381 pixels); manifest marks captures `captured_unreviewed`.
- `just check` **FAILED** at Ruff format: `scripts/phase1_evidence.py` and `tests/test_phase1_evidence.py`. Lint, `ty`, full pytest not reached.
- `just phase1`: **54 passed, 1 skipped**. `just test-tty` and `just test-kitty`: **passed**.
- Matplotlib screenshot: sine/cosine figure renders, but dark text on transparent dark margins is nearly invisible; legend and axes interior remain legible.
- Rich Kitty: correct unsupported-inline diagnostic in panel/table. Rich noop: correct in-layout text fallback.

## Matplotlib configuration established by bundle

- User `rcParams`: `figure.figsize=[6,6]` (default `[6.4,4.8]`), `figure.dpi=300` (default `100`), `figure.facecolor=none`, `savefig.transparent=True`.
- `axes.facecolor=white`, `text.color=black`, `axes.labelcolor=black`. Do not override these user-owned settings without explicit opt-in.
- Observed visual contrast is problematic, but it is **not** evidence of a broken terminal PNG transport.

## Recent fix and remaining gates

- Ruff formatting normalized for evidence collector and regression test; **no new local check has been run** against that commit.
- Rerun `just check` or `just evidence` at latest branch head. Preserve further logs/screenshots and any new failures.
- Missing owned-input live color negotiation, Rich inline graphics (Phase 2/4), later display-time resize behavior, and legacy size-marker warnings remain open.

## Handoff

Do not merge or count screenshot capture as image-quality acceptance. The failed run ZIP is valid and retained.
