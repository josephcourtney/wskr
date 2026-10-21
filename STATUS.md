# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 validation](docs/phase1-validation.md), [Evidence bundles](docs/phase1-evidence-bundles.md).

## Current focus

**Phase 1 validation passes, but automated evidence capture and final visual/profile acceptance remain open.** Feature branch `feature/phase1-terminal-profile-20261020`; `main` unchanged.

## Verified on macOS — October 21, 2026, `ab3ad41`

- `just check`: **PASS** — compileall, Ruff format/lint, `ty`, full pytest **194 passed, 3 skipped**, 137 legacy size-marker warnings.
- `just phase1`: **54 passed, 1 skipped**. Previously, `just test-tty` **35 passed** and `just test-kitty` **5 passed**.
- Real Kitty image transmission works; prior screenshot shows normal plotting but low text contrast against a dark margin. Default Rich `noop` fallback is visible, while Rich Kitty inline graphics remain unsupported.

## New implementation — unverified on macOS

- `just evidence` runs all four validation suites and launches a dedicated Kitty window for each Matplotlib/Rich/noop visual scenario.
- Exact-title CoreGraphics lookup and window-only macOS `screencapture` collect isolated screen PNGs, reference PNGs and command logs; failures are recorded rather than replaced by unrelated desktop captures.
- Run-specific manifest records git state, timestamps, return codes, screenshots, rcParams and file SHA-256; a matching ZIP is generated even on partial failure.
- Five deterministic runner tests cover archives, errors, skipped modes and scoped screenshots.

## Remaining acceptance

- Execute `just check` and `just evidence` on the new branch in macOS/Kitty. The new capture/ZIP workflow has **not** yet been run there.
- Visually inspect captured plotting pixels and theme/size behavior; screenshot presence alone is not a visual pass.
- Profile unknown terminal colors and other capabilities only with safely owned input; do not override user rcParams.
- Legacy test-size warnings remain; Rich Kitty graphics require Phase 2/4.

## Handoff

Do not merge or declare Phase 1 complete until new code passes macOS checks and the ZIP/screenshots are inspected.
