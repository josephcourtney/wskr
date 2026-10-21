# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 validation](docs/phase1-validation.md), [evidence instructions](docs/phase1-evidence-bundles.md).

## Current focus

**Phase 1 implementation and screenshot collection exist; the final clean macOS quality/evidence gate has not yet passed on the latest branch.** Phase 0 is on `main`; Phase 1 remains on `feature/phase1-terminal-profile-20261020`.

## Verified evidence

- At `ab3ad41` (October 21): `just check` passed — **194 tests passed, 3 opt-in skips, 137 nonfatal legacy test-size warnings**; `just phase1`: **54 passed, 1 skipped**.
- Earlier live `just test-tty`: **35 passed**; `just test-kitty`: **5 passed**.
- First automated `just evidence` at `2dbb65f`: produced a ZIP and all three isolated real Kitty screenshots, but `just check` stopped at Ruff formatting.
- Visual review: Matplotlib lines/axes render; black text on transparent margins is difficult to read against a dark terminal. Rich Kitty shows an expected inline-unavailable diagnostic; Rich noop shows a text fallback.

## Recent changes, not yet locally qualified

- Corrected the evidence collector/test formatting issue reported by the first evidence run.
- Recorded the **no silent contrast adaptation** decision in [ADR-002](docs/adr/0002-terminal-measured-defaults.md). Added a deterministic regression for the observed 6×6-inch, 300-DPI transparent configuration.
- No `just check` or `just evidence` run has been observed on these latest commits. GitHub status checks are not a substitute for local Kitty acceptance.

## Known scope limits

- Runtime OSC foreground/background interrogation is available only through caller-owned input; default plotting does not consume shared TTY input.
- Rendering still uses external `kitty icat`; native Kitty codec/placement and Rich inline graphics are Phase 2/4 work.
- Display-time figure resizing, managed redrawing and theme changes remain Phase 3 work. Existing size-marker warnings are advisory.

## Handoff

Run `just evidence` in a clean macOS Kitty checkout at the latest branch head; inspect the ZIP's check logs, manifest and three screenshots. **Do not merge Phase 1 before the final gate is green**; preserve failures precisely.
