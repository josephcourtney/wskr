# wskr — Immediate Tasks

Phase 1 qualification; see [PLAN.md](PLAN.md) and [validation evidence](docs/phase1-validation.md).

- [ ] Preserve or reconcile local `just fix` changes before pulling the feature branch. Then run `just check` and `just phase1` on the new commit, correcting only observed failures.
- [ ] Repeat `just test-tty` and `just test-kitty` after the fixes to establish no transport regression.
- [ ] Re-run the Kitty Matplotlib visual probe with a logged snapshot of `figure.figsize`, `figure.dpi`, `figure.facecolor`, `axes.facecolor`, `text.color` and current background. Decide which are explicitly user-owned before changing display colors or dimensions.
- [ ] Treat Rich inline graphics/virtual placement as planned Phase 2/4; the Kitty registry now recognizes selection but explicitly refuses the broken inline path.
- [ ] Classify remaining legacy test sizes truthfully without weakening checks.
