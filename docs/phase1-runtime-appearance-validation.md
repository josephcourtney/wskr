# P1 runtime appearance completion — November 1, 2026

## Scope

This note supplements [original Phase 1 acceptance](phase1-validation.md) without changing its recorded source commit. Phase 1's initial safety/defaults gate was accepted on October 21; the later work completes optional runtime appearance capture and integration for input-owning applications.

The foreground-only `probe_owned_profile()` gathers OSC 10/11/4 colors, optional CSI 14/16 pixels, and Kitty XTGETTCAP font family/point size, DPI, colors and opacity. Unsupported and invalid data remain unknown. Standard OSC color replies take precedence over Kitty fallbacks. A `use_profile(profile)` context makes measured defaults available to stock Matplotlib figure construction without changing global `rcParams`. Explicit user styling and physical `figsize`/`dpi` remain authoritative. New-figure defaults use cell-rooted text/line/marker sizing, local monospace fallback and known-opacity transparency.

## Verification at code commit `e77c5950667ee01fefc972a5ccc8fa9eb0f7844a`

- [Ubuntu/macOS quality run 41359344268](https://github.com/josephcourtney/wskr/actions/runs/41359344268): **372 passed, 3 skipped** on both platforms; compilation, Ruff, ty, wheel build and installed backend/export smoke passed.
- [Real Kitty/Xvfb graphical regression 41359344259](https://github.com/josephcourtney/wskr/actions/runs/41359344259): **passed**, covering the existing native protocol/placement and Matplotlib graphical regressions.
- Dedicated deterministic tests exercise correct/mismatched/negative XTGETTCAP replies, numeric and provenance validation, foreground ownership refusal, nested appearance scopes, explicit Matplotlib style precedence, dark/light profile changes and muted/transparent styling.
- Real PTY transactions exercise matched and foreign Kitty DCS responses, timeout handling, unrelated keyboard input forwarding and termios restoration; no actual Kitty software is required for those tests.

## Boundaries

**The new XTGETTCAP appearance feature has not been visually/protocol-qualified against native macOS Kitty in this increment.** Hosted real Kitty graphics tests confirm that the existing renderer still works; they do not establish that Kitty answered a new appearance query. A separate macOS owned-input query capture is needed to claim that platform-specific integration.

Ordinary nonblocking pyplot does not own the shell/REPL input stream, so it cannot safely perform unsolicited active color queries. It uses kernel geometry until an owning caller scopes a measured profile. Reprobe and scope new figures to adapt to the current terminal theme; changing already-created artist colors is an outstanding **P3 lifecycle feature**, not a completed P1 behavior. Rich inline composition is P4.
