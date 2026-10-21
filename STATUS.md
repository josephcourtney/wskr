# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 validation](docs/phase1-validation.md), [ADR-002](docs/adr/0002-terminal-measured-defaults.md).

## Milestone

**Phase 1 accepted — terminal profiles, safe bounded queries, and Matplotlib default/style precedence.** Validated from a clean macOS Kitty checkout at code SHA `5e35aa6e9ae101aff0f30b82a19bd4cf26de2fb7` in [PR #17](https://github.com/josephcourtney/wskr/pull/17). Phase 0 was previously integrated into `main`.

## Acceptance evidence — October 21, 2026

- Complete run `20261021T202749061910Z-5e35aa6e9a-f0056e.zip`, 14/14 matching SHA-256 hashes, clean source tree, macOS arm64/Python 3.14.0.
- `just check` **passed** syntax, Ruff format/lint, `ty` and full pytest (**200 passed, 3 skipped**).
- `just phase1`: **55 passed, 1 skipped**; `just test-tty`: **35 passed**; live `just test-kitty`: **5 passed**.
- Three actual, isolated **1272×1381 Kitty** screenshots reviewed. Matplotlib PNG image transmitted; both Rich modes display the correct in-layout diagnostic fallback. **Matplotlib presentation is still flawed**: black title/labels on the dark transparent margin have poor contrast, and leading y-tick digits clip at the left viewport edge.
- **137 nonfatal full-suite size-marker warnings** reflect legacy test classification, not a failed gate.

## Next phase and known limits

- **Phase 2:** standards-correct native Kitty protocol codec, negotiated availability, image IDs, placement, cleanup and acknowledgments. Do not treat external `kitty icat` as completed native transmission.
- **Phase 3:** solve small-window viewport fitting, display placement and clipping; honor explicit user `figsize`, DPI and colors. Any contrast-assistance mechanism must be opt-in and preserve saved exports.
- **Phase 4:** genuine Rich inline graphics/virtual placement; current diagnostics are intentional.
- Safe OSC foreground/background responses require caller-owned terminal input; unavailable capabilities remain unknown rather than fabricated.

Gate P1 is accepted on the tested **code** SHA; documentation-only closeout commits are not separate runtime validation runs. Full historical evidence and limitations appear in [docs/phase1-validation.md](docs/phase1-validation.md).
