# ADR-002: Terminal-measured appearance and sizing defaults

- **Date:** 2026-10-19
- **Status:** Accepted
- **Decision scope:** Geometry, coloring, fonts, DPI and theme precedence

## Context

The `git-wut` plots showed that fixed figures and hardcoded palettes can look out of place in short terminal dashboards. The backend should discover what the user is actually looking at: terminal cells/pixels, foreground/background, ANSI palette, font and (if available) Kitty DPI/opacity. The host OS's light/dark preference can differ from Kitty's current colors. Matplotlib's physical `figsize`/`dpi` controls are confusing as primary terminal layout settings.

## Decision

Derive default figure extent, typography, color cycle and contrast from a safe, provenance-aware runtime `TerminalProfile`. Use measured cell/pixel geometry to compute ordinary Matplotlib defaults; distinguish rendering DPI from physical display DPI. Infer effective light/dark mode from the terminal background before using environmental or OS fallbacks. Preserve all explicit user sizing, colors and styles. Do not add a new public unit system or substitute Matplotlib plotting API.

## Alternatives considered

- Hardcode a Kitty-themed Matplotlib style: straightforward but incorrect across terminal color themes and font settings.
- Parse `kitty.conf`: cannot reliably represent the effective runtime theme, remote terminal or dynamic changes.
- Follow macOS appearance directly: may disagree with Kitty's chosen theme.
- Require terminal-specific width/height/scale parameters for every figure: breaks the desired stock Matplotlib experience.

## Consequences

Positive: theme consistency, legible plots and fewer application-specific renderer options. Negative: terminal queries may be unavailable or unsafe in a shared TTY, so fallbacks and input isolation are necessary. Explicit artist styling complicates automatic recoloring; preserve user intent on uncertainty.

**Design references:** [DESIGN ``5–6](../../DESIGN.md), `INV-02`, `INV-03`, `INV-04`, `INV-06`.
