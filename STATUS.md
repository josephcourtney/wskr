# wskr — Current Status

Current handoff: [DESIGN](DESIGN.md), [PLAN](PLAN.md), [TODO](TODO.md), [Phase 2 evidence](docs/phase2-validation.md).

## Active focus

**Phase 2 direct Kitty transport implemented on [draft PR #18](https://github.com/josephcourtney/wskr/pull/18); acceptance remains open.** Phase 1 merged and passed its complete macOS gate at code commit `5e35aa6`.

## Implemented

- Kitty PNG `f=100` Base64 codec (≤4096-byte chunks), control framing, ACK/error parsing, and explicit image/placement/delete operations.
- Native transport with scoped image IDs, physical/virtual placements and cleanup. Main `kitty` backend uses direct packets; `kitty_legacy` retains external `icat` as a diagnostic.
- Bounded PTY output and caller-owned capability interrogation; foreign terminal input preserved and terminal attributes restored. Writes bind to stdout's actual TTY and reject redirection.
- Shared virtual-placeholder primitives (Unicode/ID/diacritic encoding) prepared for Phase 4. **Rich still renders honest text fallbacks, not inline graphics.**
- Dedicated protocol, fault-injection, PTY and five-scenario visual-evidence tests committed; `just phase2` includes the portable PTY suite.

## Verified and outstanding

**Portable local subset passed:** 14 isolated tests and `compileall` on Python 3.13/Linux, testing three exact Git-blob-matched codec/I/O/manager source files. Includes real Linux PTY transactions, positive/negative ACKs, timeouts and image lifecycle. See the exact SHA/evidence matrix in [docs/phase2-validation.md](docs/phase2-validation.md).

**Not verified:** full repository `just check` (Ruff, `ty`, all tests), real Kitty display and screenshots, actual image deletion/virtual placement in an emulator. No macOS run is assumed or requested for the ongoing work. PR #18 stays draft; Gate P2 is **not yet certified**.

Phase 3 retains viewport fitting, Matplotlib lifecycle/resize/contrast. Phase 4 retains real Rich inline placement and `ConsoleOptions` sizing. See [TODO](TODO.md).
