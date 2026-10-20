# wskr — Implementation Plan

**Purpose:** Execution strategy for the adopted [DESIGN.md](DESIGN.md), not a completion report. For current progress see [STATUS.md](STATUS.md); for immediate tasks see [TODO.md](TODO.md). Phase numbers are stable references.

## Approach and constraints

Refactor in small, testable stages rather than transplanting the standalone `mplkitty` prototype wholesale. Retain existing `wskr_kitty` backend selection, useful `RichPlot`/`RichImage` imports and protocol interfaces through a compatibility interval. Favor explicit deprecations over surprise removals. Kitty is the only required functional graphics transport for the initial consolidation. Do not present Sixel and iTerm2 placeholders as complete.

The migration may temporarily contain parallel implementations behind internal interfaces; these are transitional only. It must not create a second public Matplotlib API. Prefer small functional seams (query parser, style resolver, protocol codec, image manager), and do not simultaneously refactor all layers without contract tests.

Design invariants `INV-01` through `INV-12` apply at every phase. Architecture rationale belongs in [ADRs](docs/adr/), not here.

## Phase 0 — Characterize and constrain the baseline

**Objective:** Establish what the current code actually does and which behaviors require preservation or correction.

- Enumerate installed backend names, entry points, supported Matplotlib/Python versions, `wskr.init`, `RichPlot`/`RichImage`, `ImageProtocol`, registry behavior and `WSKR_*` settings.
- Pin baseline behavior for `plt.show`, `plt.ion`, multi-figure state, `savefig`, redirected/non-TTY output, sizing, OSC dark-mode detection and Rich placement.
- Identify unsupported/incorrect functionality explicitly: the current `kitty` transport requires the external binary and uses `icat`; the experimental direct path needs proper Kitty PNG framing/Base64; Sixel and iTerm2 are placeholders; global import modifies Matplotlib settings.
- Review existing test fixtures and real-Kitty screenshot helper dependencies. Do not assume an automated test implies a successful live Kitty display.
- Record a compatibility map and toolchain blockers, including mismatched boilerplate in `justfile` and `pyproject.toml`.

**Gate P0:** Baseline tests can be run locally and each known behavior has an evidence-backed pass/fail/untested classification. A documented migration map exists.

## Phase 1 — Terminal profile, safe queries, style defaults

**Design references:** `INV-02`–`INV-06`, DESIGN ``5–6.

Implementation ordering:

1. Extract an immutable `TerminalProfile` with per-field provenance and missing-value handling.
2. Build atomic, bounded terminal-query sessions using the existing `terminal.io` seam; test input isolation, response framing, timeout, descriptor ownership and restoration.
3. Gather rows/columns/pixel dimensions, `OSC 10/11/4`, Kitty extended colors, font/DPI/opacity if available, and actual graphics capability.
4. Fix dark-mode chaining so both `True` and `False` terminate upon a valid result; prefer terminal colors over `COLORFGBG` and OS dark mode.
5. Build a pure style resolver that produces Matplotlib-compatible defaults from the profile. Apply defaults during figure construction only when backend-owned; remove import-time rcParams mutations.

**Gate P1:** Deterministic unit and PTY tests prove safe probing, no import-time terminal I/O, correct fallback semantics, and explicit user style precedence.

## Phase 2 — Standards-correct Kitty transport

**Design references:** `INV-07`–`INV-09`, DESIGN `7, [ADR-003](docs/adr/0003-kitty-transport-and-placement.md).

1. Introduce a codec tested independently from terminal writes: explicit PNG `f=100`, Base64 payloads, ≤4096-byte chunks, `m` continuation flags, and proper command framing.
2. Create image and placement abstractions with IDs, cleanup and optional acknowledgments.
3. Implement capability negotiation and safe binary TTY output; do not rely on `KITTY_WINDOW_ID` alone.
4. Replace or retire the faulty experimental `KittyPyTransport` and make the direct protocol the primary implementation; keep `kitty icat` only as an optional comparison/diagnostic.
5. Make unsupported graphics observable rather than silently mapping to `NoOpProtocol`.

**Gate P2:** Protocol round-trip tests, simulated acknowledgments, and direct transmission in a real Kitty instance pass. No output escapes into redirected streams.

## Phase 3 — Stock Matplotlib lifecycle and live behavior

**Design references:** `INV-01`, `INV-02`, `INV-08`, DESIGN ``4, 6.

1. Refactor the Agg-derived canvas/manager to use supported Matplotlib hooks without global style mutation or unconditional manager destruction.
2. Track which figures have backend-derived default dimensions. Respect explicit `figsize`, `dpi`, `set_size_inches` and export settings.
3. Map terminal cell allocations to actual pixel buffer dimensions; distinguish extent, scale and density. Avoid device-specific DPI constants, arbitrary monitor assumptions, and fixed prompt-row deductions.
4. Support `plt.ion()`, IPython/REPL, pandas plotting, `draw_idle()` and multiple figures without recursive render loops.
5. Make `show(block=False)` nonblocking and `block=None` follow interactive semantics. Provide managed `block=True` redraw/quit behavior without leaking terminal state.
6. On resize/theme changes, debounce and update existing placements; preserve explicit user styling.

**Gate P3:** Installed wheel and module-backend workflows, savefig PNG/SVG, interactive PTY tests, theme/resize updates and multi-figure lifecycle pass. Real Kitty visual output is separately verified.

## Phase 4 — Shared Rich graphics

**Design references:** `INV-08`, `INV-11`, DESIGN `8.

1. Route `RichImage` and `RichPlot` through the same protocol encoder/image manager as pyplot.
2. Implement Kitty virtual placements and correct Unicode placeholder row/column diacritics and ID encoding.
3. Derive Rich layout sizing from `ConsoleOptions` and live terminal metrics; remove frozen terminal-size caching and monitor-specific DPI constants.
4. Reuse uploaded images for unchanged content and keep scroll/wrap behavior compatible with Rich layouts.
5. Keep Rich optional for core Matplotlib installs and provide a safe textual fallback in unsupported terminals.

**Gate P4:** Nested Rich table/panel measurement, upload reuse, virtual-placement handling, cleanup and real Kitty screenshot validation pass.

## Phase 5 — Release hardening and migration cleanup

1. Simplify direct dependencies, remove unneeded runtime test/science tooling, and correct entry-point/installation docs without adding speculative transports.
2. Preserve or explicitly deprecate historical module paths and environment configuration.
3. Remove misleading advertised Sixel/iTerm2 stubs; retain protocol extensibility but demand independent end-to-end tests for new transports.
4. Validate source/wheel builds, install from wheel, normal imports, terminal/headless output and reproducible local test commands.
5. Update `README.md`, `STATUS.md`, `TODO.md` and curated `CHANGELOG.md` to reflect only completed work; document remaining limitations.
6. Review all changes against `POLICY.md` and `AGENTS.md`.

**Gate P5:** All acceptance requirements in DESIGN `10 have evidence, observed live-Kitty runs are reported separately, and no unimplemented capability is marketed as complete.

## Compatibility migration map

| Current location | Intended responsibility or disposition |
| --- | --- |
| `wskr.terminal.io` and `terminal.osc` | Bounded TTY session, safe response parser |
| `wskr.terminal.capabilities` / `terminal.kitty.capabilities` | Provenance-aware terminal profile |
| `wskr.render.matplotlib.utils` | Pure theme/default style computation |
| `wskr.render.matplotlib.size` | Cell-to-pixel and pixel-to-inches sizing; ownership tracking |
| `wskr.protocol.base` / `registry` | Explicit protocol contract and real negotiated availability |
| `wskr.protocol.kitty` | Standards-correct direct Kitty codec/transport and ID lifecycle |
| `wskr.render.matplotlib.core` / `kitty` | Stock Matplotlib manager/canvas lifecycle |
| `wskr.render.rich.img` / `plt` | Reuse image manager; correct virtual placement placeholders |
| `wskr.render.matplotlib.iterm2` / `sixel` | Remain unsupported until independently implemented |
| `jkit.plot` | Remain separate application-level plotting utilities |
| `mplkitty` local prototype | Behavioral reference and validation cases, not a duplicate public API |

## Verification matrix and test strategy

### Pure tests (isolated)

- Color and capability parsing: `OSC 4/10/11`, Kitty extended queries, permitted terminators, malformed responses, font/DPI/opacity, uncommon palettes and invalid RGB encodings.
- Dark/light strategy precedence: measured light and dark, valid false result, explicit override, environment hint, OS fallback, complete failure.
- Geometry: cell/window measurements, inferred provenance, missing/nonpositive values, different cell aspect ratios, narrow/short viewport, DPI variation and exact pixel targets.
- Style: explicit rcParams/artist overrides, theme changes only for backend-owned values, transparency and contrast behavior; import causes no I/O or style changes.
- Graphics codec: png `f=100`, raw `f=24/32` when used, Base64 round-trip, bounded chunks and continuation, placement/ID/cleanup/ack behavior.
- Rich: sizing, Unicode diacritics, virtual placement encoding, cache invalidation and non-Kitty text fallback.
- Export: normal PNG/SVG output with correct requested dimensions and no graphics escape transmission.

### Pseudo-terminal tests

- TTY opened/closed correctly; termios restoration on success, timeout, error and interruption.
- Match expected response types and preserve unrelated input; bound incomplete or oversized responses.
- Redirected stdout, missing controlling TTY, unsupported graphics and tmux without passthrough fail safely.
- `plt.ion()`, `draw_idle`, interactive REPL, nonblocking and blocking `show`, multi-figure cleanup.
- Simulated geometry/theme changes redraw backend-owned content without image accumulation.

### Real Kitty tests (opt-in, local)

Test at least: light/dark/manual/automatic theme changes; opaque and semitransparent backgrounds; several ANSI palettes; ~60/100/160 columns; short screen and live resize; multiple font sizes/families; standard and high-DPI geometry; normal script, REPL/pandas, managed view, multi-figure and Rich table/panel; SSH/tmux when available; pipe/no-TTY behavior; savefig exports.

Use the existing `tests/test_e2e_kitty.py` infrastructure where suitable but avoid requiring `yabai` for core tests. Screenshot checks may compare location, clipping, readable contrast and stable image lifecycle. Host-specific font rasterization differences require explicit tolerances. Never count mocked screenshots as proof of actual on-screen rendering.

### Local tooling and release

Use `uv`, Ruff, `ty`, pytest and coverage per current repository configuration, recording any blocked command exactly. No GitHub Actions required. Test built wheel/sdist rather than only an editable checkout. Benchmark query/render/transfer latency if a performance optimization is proposed. Record user-visible behavior changes in `CHANGELOG.md` only after implementation completes.

## Transition and scope discipline

The phases specify intended order, not status. Completed items are removed from [TODO.md](TODO.md), and [STATUS.md](STATUS.md) is updated as evidence changes. PLAN may be shortened as completed transitional stages cease to matter; DESIGN remains the long-lived normative architecture and ADRs retain decision rationale.
