# Phase 0 — Source-backed baseline evidence

**Review date:** 2026-10-19  
**Baseline parent:** `526d71d439c74cee053aa11b0ff025fe0009f47f`  
**Phase:** [PLAN.md Phase 0](../PLAN.md#phase-0--characterize-and-constrain-the-baseline)

This file is a **testable audit snapshot**, not a changelog, task queue, current design, or claim of successful terminal rendering. The first table records facts visible in code at the baseline; the second records which runtime checks remain unverified. Future changes should replace the known-defect assertions in `tests/test_phase0_baseline.py` with desired-behavior tests.

## A. Compatibility and configuration inventory

| Surface | Current source-backed behavior | Evidence |
| --- | --- | --- |
| Package | `wskr`, version `0.0.17`; Python `>=3.13,<3.15`; GPL-3.0-only | `pyproject.toml` |
| Backend names | `wskr`, `wskr_kitty`, `wskr_sixel`, `wskr_iterm2` are registered under `matplotlib.backend` | `pyproject.toml` |
| Backend module URI | `module://wskr.render.matplotlib.kitty` available for explicit selection | `src/wskr/render/matplotlib/kitty.py` |
| Backend lifecycle | `FigureCanvasAgg` and manager classes; `TerminalBackend.show` calls the active manager then `Gcf.destroy_all()` | `src/wskr/render/matplotlib/core.py` |
| Auto sizing | `autosize_figure` is called in the display path, using viewport pixels and `WSKR_SCALE`; explicit sizes are not differentiated | `src/wskr/render/matplotlib/core.py`, `size.py` |
| Kitty transport | Main `KittyTransport` requires a `kitty` executable and invokes `kitty +kitten icat` for PNG display and dimensions | `src/wskr/protocol/kitty.py`, `terminal/kitty/capabilities.py` |
| Direct path | `KittyPyTransport` is experimental; frames raw PNG chunks while declaring `f=32`, with no Base64 encoding | `src/wskr/protocol/kitty.py` |
| Protocol registry | `get_image_protocol` resolves explicit name, then `WSKR_PROTOCOL`, then `noop`; failures may fall back to NoOp | `src/wskr/protocol/registry.py` |
| Configuration hook | `wskr.init(style="auto-dark", ...)` optionally installs dark_background | `src/wskr/__init__.py` |
| Import side effects | Importing `wskr` sets Matplotlib `text.usetex=False` globally | `src/wskr/__init__.py` |
| Theme selection | `WSKR_DARK_MODE`; `COLORFGBG` → OSC 11 → optional darkdetect. A successful `False` strategy does not end the chain | `src/wskr/render/matplotlib/utils.py` |
| Rich APIs | `RichPlot` and `RichImage` renderables; `desired_width`/`desired_height` in terminal cells; `zoom`/`dpi` | `src/wskr/render/rich/plt.py`, `img.py` |
| Rich placement | Unicode-image placeholder attempt with `U+10EEEE` and row/column diacritics; identity/encoding and live rendering need validation | `src/wskr/render/rich/img.py` |
| Rich sizing | `get_terminal_size` caches until process exit; fallback assumptions include 8×16 cell pixels, and hardware-specific DPI constants exist | `src/wskr/render/rich/plt.py` |
| Sixel/iTerm2 | Imported stubs raise `FeatureUnavailableError` by default and `NotImplementedError` on display if bypassed | `src/wskr/render/matplotlib/sixel.py`, `iterm2.py` |
| Explicit env knobs | `WSKR_PROTOCOL`, `WSKR_SCALE`, `WSKR_DARK_MODE`, `WSKR_DARK_MODE_POLICY`, `WSKR_FALLBACK`, `WSKR_CACHE_TTL_S`, `WSKR_TIMEOUT_S`, `WSKR_OSC_TIMEOUT_S`, `WSKR_ENABLE_SIXEL`, `WSKR_ENABLE_ITERM2` | `src/wskr/core/config.py` and respective modules |
| Test opt-ins | `WSKR_RUN_TTY=1` and `WSKR_RUN_E2E=1` gate some PTY and GUI tests | `tests/test_dark_mode.py`, `tests/test_e2e_kitty.py` |

Current source indicates **KNOWN DEFECTS** rather than proposed changes: overwriting explicit figure sizing, misleading no-op transport fallback, broken direct PNG framing, unsafe stdout fallback after TTY-write failure, import-time rcParams mutation, theme strategy treating valid light results as nonfinal, hardcoded viewport deductions, and an incomplete real Kitty placeholder path. These remain for Phase 1–4 correction.

## B. Baseline executable probes

The Phase 0 feature branch adds:

| Probe | Command | What it can establish |
| --- | --- | --- |
| Core environment | `just baseline` | Backend registrations, importability, file export, default protocol (no real Kitty output) |
| Characterization tests | `uv run pytest -q tests/test_phase0_baseline.py` | Stable API shape, Agg exports and **pre-migration** known behavior |
| Syntax/type/lint/format/tests | `just check` | Local toolchain readiness; Ruff checks are nonmutating |
| Built package | `just build` then `just wheel-smoke` | Install in a fresh temporary venv and exercise installed backend imports/Agg PNG |
| PTY | `just test-tty` | Opt-in simulated terminal interactions |
| Real Kitty | `just test-kitty` | Optional GUI tests; some currently require Kitty/Yabai/window automation |

**Do not interpret `just test-kitty` skipping tests as live validation.** Record actual launched Kitty version, terminal width/rows and screenshot observations separately. The current `tests/test_e2e_kitty.py` contains mocks as well as opt-in GUI code; passing a mocked screenshot assertion does not prove the backend places graphics correctly.

## C. Verification status and execution constraints

| Check | Source inspection | Executed against full checkout | Result |
| --- | --- | --- | --- |
| Backend entry-point names and modules | Yes | No | Declared; installed-wheel import unverified |
| Ordinary Agg PNG/SVG export | Code/test present | No | Probe added, not yet executed on this branch |
| Explicit-size mutation | Yes | No | Known by direct `autosize_figure` call; characterization test added |
| Import-time rcParams effect | Yes | No | Known by assignment in `wskr.__init__` |
| Light/dark fallback defect | Yes | No | Known by `if strat.detect():`; characterization test added |
| Registry default/no-op fallback | Yes | No | Known from registry; characterization test added |
| PTY reply and state restoration | Tests present | No | Needs local PTY run; source review insufficient |
| Actual Kitty display/placement | Partial code; broken experimental path | No | **Blocked: requires real Kitty and optional GUI tools** |
| Full formatting/lint/type/pytest | Tooling configured | No | **Blocked: full repository checkout and local dependencies unavailable here** |
| Isolated wheel install | Probe scripted | No | **Blocked: package index/network unavailable in execution container** |

The assistant's execution container cannot clone GitHub (DNS/network unavailable), and neither `just` nor a live Kitty GUI is present. Source/API access through the connected GitHub repository permitted code inspection and commits only; no local test, wheel, or visual-validation success is claimed. No GitHub Actions were added or run.

## D. Remaining acceptance gate

`PLAN.md` Phase 0 closes when `just check`, `just baseline`, `just build`, `just wheel-smoke`, and the opt-in PTY/live Kitty probes have been run in an appropriate environment and results recorded, or when each unavailable test has an explicitly accepted external-validation waiver. The code and scripts on this branch establish a reproducible starting point, but **the evidence gate is not yet complete**.
