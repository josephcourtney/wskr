# wskr — Current Status

Handoff: [DESIGN](DESIGN.md), [PLAN](PLAN.md), [TODO](TODO.md), [Phase 3 evidence](docs/phase3-validation.md).

## Recently qualified

**Phase 2 accepted and merged**, with hosted quality, real Kitty Linux/Xvfb screenshots and native macOS Kitty acceptance; see [Phase 2 validation](docs/phase2-validation.md).

**Phase 3 is in progress; Gate P3 remains OPEN.** The merged first slice ([PR #21](https://github.com/josephcourtney/wskr/pull/21)) preserves caller figure geometry, honors explicit `WSKR_SCALE` as display-only PNG scaling, preserves multiple managers across `show()`, and replaces prior native Kitty images on redraw.

The next slice ([PR #22](https://github.com/josephcourtney/wskr/pull/22)) corrects the disappearing static plot seen on native macOS after pressing Enter: **ordinary noninteractive terminal plots survive Python interpreter exit**. A Matplotlib atexit shutdown marker distinguishes this from explicit `plt.close()` and managed interactive cleanup, which still delete their scoped images. Only the final static image is relinquished; other owned uploads are cleaned normally.

**Hosted qualification:** full pytest **241 passed, 3 skipped** on both Ubuntu and macOS 15, focused Phase 3 **40 passed** and Phase 2 **54 passed** each; syntax, Ruff and ty green. Real Linux Kitty/Xvfb rendered physical and Unicode virtual graphics plus an actual post-interpreter-exit retained Matplotlib chart. See [Phase 3 validation](docs/phase3-validation.md).

## Current boundaries and next focus

Native macOS GUI reproduction of **post-exit persistence** is outstanding; prior Phase 3 and Phase 2 screenshots already characterize local geometry/transport. The yabai-managed lower-half screenshot remains confounded by terminal geometry; a separate yabai-disabled run shows that a 1800×1800 caller-owned image can overflow a shorter viewport. `WSKR_SCALE=0.4` was observed to display the complete figure without mutating its 6×6-inch, 300-DPI source.

**Newly qualified in PR #23:** foreground `plt.show(block=True)` waits for Enter with same-TTY/foreground ownership, then explicitly closes managed figures; ordinary `plt.show()` stays nonblocking and preserves static output. Native Kitty now uses guarded `draw_idle` so `plt.ion()` changes transmit image updates without recursive redraw. Real child-process PTY tests passed on both Ubuntu and macOS, with **253 full tests passed, 3 skipped**, **52 focused Phase 3** and **54 Phase 2** tests each; hosted real-Kitty screenshots passed.

Remaining Phase 3 work: deliberate oversize/viewport policy, debounced live resizing and image placement, richer REPL/pandas workflows, scrollback lifetime, and wheel/module-backend qualification. Rich inline composition remains Phase 4.
