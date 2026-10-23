# wskr local developer commands. Do not import unrelated projects' recipes.
set shell := ["bash", "-euo", "pipefail", "-c"]

default: help

# Show the available commands.
help:
  @just --list --unsorted

# Resolve/install the environment from pyproject.toml and uv.lock.
sync:
  uv sync

# Check Python source, tests, and local scripts for syntax errors.
syntax:
  uv run python -m compileall -q src tests scripts

# Static lint without mutating source.
lint:
  uv run ruff check --no-fix src tests scripts

# Check, rather than overwrite, source formatting.
format:
  uv run ruff format --check src tests scripts

# Static typing; do not suppress failures.
typecheck:
  uv run ty check src tests scripts

# Current pytest suite with coverage as defined in pyproject.toml.
test:
  uv run pytest -q

# Short feedback cycle, not a release gate.
test-fast:
  uv run pytest -q -m "not slow"

# Opt-in tests that use local PTYs.
test-tty:
  WSKR_RUN_TTY=1 uv run pytest -q tests/test_dark_mode.py tests/test_tty_extras.py tests/test_tty_kitty.py

# Opt-in real Kitty suite; tests may still skip if optional GUI dependencies are absent.
test-kitty:
  WSKR_RUN_E2E=1 WSKR_RUN_TTY=1 uv run pytest -q tests/test_e2e_kitty.py

# Phase 1: bounded queries, measured geometry, themes, and figure defaults.
phase1:
  uv run pytest -q tests/test_terminal_color.py tests/test_terminal_profile.py tests/test_terminal_query.py tests/test_terminal_theme.py tests/test_terminal_figure.py tests/test_backend_profile_defaults.py tests/test_dark_mode.py

# Phase 2: PNG framing, image lifecycle, virtual placement, ACK/query safety.
phase2:
  uv run pytest -q tests/test_kitty_native.py tests/test_kitty_pty_transactions.py tests/test_kitty_native_pty_integration.py tests/test_phase2_visual_smoke.py tests/test_tty_kitty.py tests/test_rich_renderables.py

# Phase 3: explicit Matplotlib ownership, non-destructive multi-figure show,
# and scoped native display replacement.
phase3:
  uv run pytest -q tests/test_phase3_figure_ownership.py tests/test_phase3_interactive_lifecycle.py tests/test_phase0_baseline.py tests/test_mpl_base.py tests/test_mpl_kitty.py tests/test_canvas.py tests/test_backend_profile_defaults.py tests/test_terminal_figure.py

# Manual visual smoke run, inside Kitty. For Rich, set WSKR_PROTOCOL=kitty.
visual-smoke mode="matplotlib":
  uv run python scripts/phase1_visual_smoke.py --mode '{{mode}}'

# Complete validation plus isolated Kitty screenshots and one run-specific ZIP.
evidence *args:
  uv run python scripts/phase1_evidence.py {{args}}

# Structured, diagnostic baseline report with no active graphics output.
baseline:
  uv run python scripts/phase0_baseline.py

# Required nonmutating local verification.
check:
  just syntax
  just format
  just lint
  just typecheck
  just test

# Source distribution and wheel; no implicit publishing.
build:
  uv build --no-sources

# Validate installation from the built wheel, in an isolated environment.
wheel-smoke:
  uv run python scripts/phase0_wheel_smoke.py

# Development repair commands (deliberately separate from check).
fix:
  uv run ruff format src tests scripts
  uv run ruff check --fix src tests scripts

# Remove generated files only, keeping the Python virtual environment.
clean:
  rm -rf build dist .pytest_cache .ruff_cache .coverage .coverage.* coverage.xml
  find src tests scripts -type d -name __pycache__ -prune -exec rm -rf {} +
