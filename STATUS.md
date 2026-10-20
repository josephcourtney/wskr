# wskr — Current Status

This file is a short handoff snapshot. Architecture lives in [DESIGN.md](DESIGN.md); milestones in [PLAN.md](PLAN.md); immediate tasks in [TODO.md](TODO.md).

## Current focus

**Phase 0 — baseline characterization.** The terminal-native Matplotlib/Rich target is specified, but the repository's existing implementation has **not** been migrated to it. This status is based on source inspection, not a fresh successful local test run.

## Implemented in the current tree

- Matplotlib Agg-based backend registration (`wskr`, `wskr_kitty`), and a Kitty adapter that invokes the external `kitty +kitten icat` command.
- `ImageProtocol` registry and an experimental `KittyPyTransport`.
- Rich `RichImage`/`RichPlot` renderables and terminal-size/OSC dark-mode helpers.
- Unit, PTY and opt-in Kitty integration test sources (their current pass state has not been established here).

## Known gaps and risks

- The target direct Kitty PNG transport is **not ready**: experimental chunks use an incompatible format/encoding. ID/placement management is incomplete.
- Terminal sizing uses fixed prompt-row and pixel fallback assumptions; default Matplotlib appearance is not derived from live terminal colors/font metrics.
- Matplotlib import changes global `text.usetex`; draw/show behavior and explicit-size preservation require characterization.
- The current dark-mode fallback can ignore a valid light result; terminal queries may fail when no TTY is safely available.
- Sixel and iTerm2 backend modules are unimplemented stubs, despite registered names.
- The borrowed `justfile` and portions of `pyproject.toml` still reference unrelated Cwide modules, tooling or tests; local validation recipes need repair before being trusted.
- Real Kitty visual compatibility and headless/redirected safety remain unverified.

## Next handoff

Perform [PLAN Phase 0](PLAN.md#phase-0--characterize-and-constrain-the-baseline), follow the unfinished [TODO](TODO.md), then implement safe terminal/profile handling before protocol replacement. No code changes were made as part of this documentation reconciliation.
