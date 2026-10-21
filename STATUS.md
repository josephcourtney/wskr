# wskr — Current Status

Handoff: [DESIGN.md](DESIGN.md), [PLAN.md](PLAN.md), [TODO.md](TODO.md), [Phase 1 validation](docs/phase1-validation.md).

## Current focus

**Phase 1 focused tests and Kitty transmission are evidenced, but final quality qualification remains open.** Changes are on `feature/phase1-terminal-profile-20261020` in [draft PR #17](https://github.com/josephcourtney/wskr/pull/17); Phase 0 is merged into `main`.

## Latest macOS check — October 21, 2026, `11343a1`

- `just syntax`: **PASS**. `just format`: **PASS**, 87 files already formatted.
- `just lint`: **FAIL**, three `scripts/phase1_evidence.py` findings (oversized try block, raise within try, imperative docstring); `ty` and full pytest were **not reached**.
- Refactored the Kitty screenshot path into a bounded helper and corrected the docstring in `adeeec4`; **this code has not yet been locally checked**.

## Earlier macOS evidence — `207005d`

- `just phase1`: **55 passed, 1 skipped**; `just test-tty`: **35 passed**; `just test-kitty`: **5 passed**. `just evidence` produced a ZIP with 14 verified hashes and 3/3 scoped real Kitty screenshots.
- At **712×619**, normal Matplotlib PNG output is **severely clipped** (title/legend and portions of axes/labels offscreen). The reference PNG is complete. Rich Kitty and noop fallbacks appear correctly.
- User-owned nondefault 6×6-inch, 300-DPI, transparent background/black text settings must not be silently overridden. Display fitting and resize behavior remain Phase 3 concerns.

## Known limits and next action

- Caller-owned OSC probing exists but unattended live color negotiation is not complete; native Kitty codec, Rich inline graphics and interactive display lifecycle remain in Phases 2–4.
- **Run `just check` on the latest branch head**; if green, run `just evidence` and review three real screenshots. Preserve unverified/failing outcomes and do not merge until Phase 1 qualification is evidenced. See [TODO.md](TODO.md).
