# ======================================================================
# Global shell + environment
# ======================================================================

set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load := true
set export := true


# ======================================================================
# Configuration
# ======================================================================

MODE           := env("MODE", "dev")  # dev | debug | ci
ROOT_DIR       := justfile_directory()
PACKAGE        := file_stem(ROOT_DIR)
PYTHON_PACKAGE := env("PYTHON_PACKAGE", "cwide")
VERBOSE        := env("VERBOSE", "0")

REPO_CACHE_DIR := ROOT_DIR + "/.cache"
UV_CACHE_DIR   := REPO_CACHE_DIR + "/uv"
RUFF_CACHE_DIR := REPO_CACHE_DIR + "/ruff"

PY_SRC      := "src"
PY_TESTPATH := "tests"
PY_SCRIPTS  := "scripts"


# ======================================================================
# Tool wrappers
# ======================================================================

UV                  := "uv --cache-dir " + UV_CACHE_DIR
PYTHON              := UV + " run python"
RUFF                := UV + " run ruff"
RUFF_LINT           := RUFF + " check --cache-dir " + RUFF_CACHE_DIR
RUFF_FORMAT         := RUFF + " format --cache-dir " + RUFF_CACHE_DIR
PYTEST              := UV + " run pytest"
TY                  := UV + " run ty"
COVERAGE            := UV + " run coverage"
VULTURE             := UV + " run vulture"
RADON               := UV + " run radon"
IMPORTLINTER        := UV + " run lint-imports"
IMPORTLINTER_CONFIG := ROOT_DIR + "/import-linter.toml"

JSCPD := "npx --yes jscpd@4.0"


# ======================================================================
# pytest options
# ======================================================================

PYTEST_TIMEOUT := env("PYTEST_TIMEOUT", "300")
PYTEST_BASE_OPTS := "--timeout=" + PYTEST_TIMEOUT + " --cov-context=test"  # per-test context only in full runs
PYTEST_QUIET_OPTS := "-q --tb=short -r fE --show-capture=no -o log_cli=false"
PYTEST_DEBUG_OPTS := "-vv --tb=long -l --show-capture=all -o log_cli=true"
PYTEST_LOG_OPTS := "-q --tb=short -r fE --show-capture=no -o log_cli=true --log-cli-level=INFO"
PYTEST_FAST_OPTS := "-m 'not slow' --durations=25 --durations-min=0.1 --timeout=30"
PYTEST_FAILING_OPTS := "--lf"

# All interactive test modes run the same source-controlled, argument-safe
# Python wrapper with no coverage and explicit acceleration choices.
DEV_TESTS := UV + " run --no-sync python scripts/dev_tests.py"


# ======================================================================
# Meta / defaults
# ======================================================================

[private]
default: help


# List available recipes; also the default entry point.
help:
  @just _log_start help
  @just --list --unsorted --list-prefix "  "
  @just _log_end help


# Print resolved runtime configuration.
env:
  @just _log_start env
  @echo "MODE={{MODE}}"
  @echo "PACKAGE={{PACKAGE}}"
  @echo "PYTHON_PACKAGE={{PYTHON_PACKAGE}}"
  @echo "PY_SRC={{PY_SRC}}"
  @echo "PY_TESTPATH={{PY_TESTPATH}}"
  @echo "PY_SCRIPTS={{PY_SCRIPTS}}"
  @echo "UV={{UV}}"
  @echo "RUFF={{RUFF}}"
  @echo "PYTEST={{PYTEST}}"
  @echo "TY={{TY}}"
  @echo "VULTURE={{VULTURE}}"
  @echo "RADON={{RADON}}"
  @echo "IMPORTLINTER={{IMPORTLINTER}}"
  @echo "JSCPD={{JSCPD}}"
  @{{UV}} --version || true
  @{{PYTEST}} --version || true
  @{{RUFF}} --version || true
  @just _log_end env


# ======================================================================
# Logging / command runners
# ======================================================================

[private]
_log_start NAME:
  @if [ "{{VERBOSE}}" != "0" ]; then printf "\n=== START: %s ===\n" "{{NAME}}"; fi

[private]
_log_end NAME:
  @if [ "{{VERBOSE}}" != "0" ]; then printf "=== END: %s ===\n\n" "{{NAME}}"; fi

[private]
_cache_dirs:
  @mkdir -p {{REPO_CACHE_DIR}} {{UV_CACHE_DIR}} {{RUFF_CACHE_DIR}}


# Run a command quietly on success and print its captured output on failure.
[private]
_run NAME CMD:
  #!/usr/bin/env bash
  set -euo pipefail

  name="$NAME"
  cmd="$CMD"

  set +e
  out="$(bash -c "$cmd" 2>&1)"
  status=$?
  set -e

  if [ "$status" -eq 0 ]; then
    printf "\033[1;32m✓ %s\033[0m\n" "$name"
  else
    printf "\033[1;31m✗ %s\033[0m\n" "$name"
    printf "%s\n" "$out"
    exit "$status"
  fi


# Like `_run`, but continue after a failure.
# Intended for best-effort fixing workflows, never validation gates.
[private]
_run_soft NAME CMD:
  #!/usr/bin/env bash
  set -euo pipefail

  name="$NAME"
  cmd="$CMD"

  set +e
  out="$(bash -c "$cmd" 2>&1)"
  status=$?
  set -e

  if [ "$status" -eq 0 ]; then
    printf "\033[1;32m✓ %s\033[0m\n" "$name"
  else
    printf "\033[1;31m✗ %s\033[0m\n" "$name"
    printf "%s\n" "$out"
    exit "$status"
  fi


# ======================================================================
# Environment
# ======================================================================

# Bring the local environment in sync with the committed lockfile.
[group('environment')]
[arg("force", long="force", value="true")]
sync force="false":
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start sync
  just _cache_dirs

  stamp=".venv/.sync-state"

  # `uv sync` currently has one optional repository-level flag. Keep it
  # scalar so macOS Bash 3.2 never has to expand an empty array under `set -u`.
  sync_arg=""

  if grep -Eq '^[[:space:]]*\[tool\.uv\.workspace\][[:space:]]*(#.*)?$' pyproject.toml; then
    sync_arg="--all-packages"
  fi

  fingerprint() {
    {
      # Fingerprint the sync policy itself.
      printf '%s\n' "sync"
      printf '%s\n' "uv sync"
      printf 'uv-sync-arg=%s\n' "$sync_arg"

      for file in pyproject.toml uv.lock uv.toml .python-version; do
        [[ ! -f "$file" ]] || cat "$file"
      done

      git ls-files '*pyproject.toml' | LC_ALL=C sort | while IFS= read -r file; do
        [[ "$file" == "pyproject.toml" ]] || cat "$file"
      done
    } | shasum -a 256 | cut -d' ' -f1
  }

  current="$(fingerprint)"

  if [[ "{{force}}" != "true" ]] &&
     [[ -d .venv ]] &&
     [[ -f "$stamp" ]] &&
     [[ "$(cat "$stamp")" == "$current" ]]; then
    echo "already up to date."
    just _log_end sync
    exit 0
  fi

  if [ -n "$sync_arg" ]; then
    {{UV}} sync "$sync_arg"
  else
    {{UV}} sync
  fi

  # uv sync may update uv.lock.
  fingerprint > "$stamp"

  just _log_end sync


# Upgrade all dependencies allowed by pyproject.toml, then sync.
[group('environment')]
upgrade:
  {{UV}} lock --upgrade
  {{UV}} sync


# Upgrade one dependency.
[group('environment')]
upgrade-package package:
  {{UV}} lock --upgrade-package {{package}}
  just sync --force


# ======================================================================
# Code quality
# ======================================================================

# Check for Python syntax errors.
[group('code quality')]
syntax:
  #!/usr/bin/env bash
  set -uo pipefail

  just _log_start syntax

  status=0

  for path in "{{PY_SRC}}" "{{PY_TESTPATH}}" "{{PY_SCRIPTS}}"; do
    set +e
    output="$({{PYTHON}} -m compileall -q "$path" 2>&1)"
    rc=$?
    set -e

    if [ "$rc" -ne 0 ]; then
      printf '\033[1;31m✓ syntax: %s\033[0m\n' "$path"
      printf '%s\n' "$output" >&2
      status="$rc"
    else
      printf '\033[1;32m✓ syntax: %s\033[0m\n' "$path"
    fi
  done

  if [ "$status" -ne 0 ]; then
    exit "$status"
  fi

  just _log_end syntax


# Lint with Ruff. By default fixes safe violations; use --no-fix for validation.
[group('code quality')]
[arg("no-fix", long, value="true")]
lint no-fix="false":
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start lint
  just _cache_dirs

  args=({{RUFF_LINT}})

  if [ "{{no-fix}}" = "true" ]; then
    args+=(--no-fix)
  else
    args+=(--fix)
  fi

  args+=("{{PY_SRC}}" "{{PY_TESTPATH}}" "{{PY_SCRIPTS}}")
  "${args[@]}"

  just _log_end lint


# Format with Ruff. Use --check for non-mutating validation.
[group('code quality')]
[arg("check", long, value="true")]
format check="false":
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start format
  just _cache_dirs

  args=({{RUFF_FORMAT}})

  if [ "{{check}}" = "true" ]; then
    args+=(--check)
  fi

  args+=("{{PY_SRC}}" "{{PY_TESTPATH}}" "{{PY_SCRIPTS}}")

  "${args[@]}"

  just _log_end format


# Validate import architecture.
[group('code quality')]
lint-imports:
  just _log_start lint-imports
  {{IMPORTLINTER}} --verbose --config "{{IMPORTLINTER_CONFIG}}"
  just _log_end lint-imports


# Static type checking.
#
# Outside CI this remains tolerant of an absent `ty` executable so the recipe
# can still be used in partially bootstrapped environments. `just check`
# explicitly runs it with MODE=ci and therefore treats absence as a failure.
[group('code quality')]
typecheck:
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start typecheck

  if {{TY}} --version >/dev/null 2>&1; then
    {{TY}} check "{{PY_SRC}}" "{{PY_TESTPATH}}" "{{PY_SCRIPTS}}"
  elif [ "{{MODE}}" = "ci" ]; then
    echo "[typecheck] ERROR: ty is not available" >&2
    echo "[typecheck] run: just sync" >&2
    exit 1
  else
    echo "[typecheck] skipping: ty not available (MODE={{MODE}})"
  fi

  just _log_end typecheck


# Scan for likely dead code.
[group('code quality')]
dead-code:
  @just _log_start dead-code
  {{VULTURE}} --min-confidence 61 {{PY_SRC}} {{PY_TESTPATH}} {{PY_SCRIPTS}}
  @just _log_end dead-code


# Report complexity; use --raw for raw metrics or --strict to enforce a ceiling.
[group('code quality')]
[arg("raw", long, value="true")]
[arg("strict", long, value="true")]
complexity raw="false" strict="false" min_complexity="11":
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start complexity

  if [ "{{raw}}" = "true" ] && [ "{{strict}}" = "true" ]; then
    echo "[complexity] ERROR: choose at most one of --raw or --strict" >&2
    exit 2
  fi

  if [ "{{raw}}" = "true" ]; then
    {{RADON}} raw "{{PY_SRC}}"
  elif [ "{{strict}}" = "true" ]; then
    echo "[complexity] failing if any block has complexity >= {{min_complexity}}"
    output="$({{RADON}} cc -s -n "{{min_complexity}}" "{{PY_SRC}}" || true)"
    if [ -n "$output" ]; then
      echo "$output"
      exit 1
    fi
    echo "[complexity] all blocks are below {{min_complexity}}"
  else
    {{RADON}} cc -s -a "{{PY_SRC}}"
  fi

  just _log_end complexity


# Detect duplicated source/test code (requires Node/npx; opt-in diagnostic).
[group('code quality')]
dup:
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start dup

  {{JSCPD}} \
    --pattern "{{PY_SRC}}/*/*.py" \
    --pattern "{{PY_SRC}}/*/*/*.py" \
    --pattern "{{PY_SRC}}/*/*/*/*.py" \
    --pattern "{{PY_TESTPATH}}/*.py" \
    --pattern "{{PY_TESTPATH}}/*/*.py" \
    --pattern "{{PY_TESTPATH}}/*/*/*.py" \
    --pattern "{{PY_TESTPATH}}/*/*/*/*.py" \
    --pattern "{{PY_SCRIPTS}}/*.py" \
    --pattern "{{PY_SCRIPTS}}/*/*.py" \
    --reporters console

  just _log_end dup


# ======================================================================
# Security / supply chain
# ======================================================================

# Secret scan. Report-only when TruffleHog is not installed.
[group('security')]
secrets:
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start secrets

  if command -v trufflehog >/dev/null 2>&1; then
    tmp_file="$(mktemp)"
    trap 'rm -f "$tmp_file"' EXIT
    printf ".venv\n.cache\nbuild\ndist\n" > "$tmp_file"
    trufflehog filesystem . --exclude-paths "$tmp_file"
  else
    echo "[secrets] skipping: trufflehog not found on PATH"
  fi

  just _log_end secrets


# Audit installed dependencies.
[group('security')]
sec-deps:
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start sec-deps

  if [ ! -x "{{ROOT_DIR}}/.venv/bin/pip-audit" ]; then
    echo "[sec-deps] ERROR: pip-audit not found" >&2
    exit 1
  fi

  PIP_NO_CACHE_DIR=1 "{{ROOT_DIR}}/.venv/bin/pip-audit"

  just _log_end sec-deps


# ======================================================================
# Testing
# ======================================================================

[group('testing')]
[arg("strict", long, value="true")]
[arg("fast", long, value="true")]
[arg("failing", long, value="true")]
[arg("dev", long, value="true")]
[arg("quiet", long, value="quiet")]
[arg("logs", long, value="logs")]
[arg("debug", long, value="debug")]
[doc("""
Run the test suite.

  --strict    propagate pytest failure (default)
  --fast      skip only slow-marked tests; still runs the broad suite WITH coverage
  --failing   rerun only previously failing tests
  --dev       alias of serial test-impact; requires seeded testmon DB, no second collection
  --quiet     compact output
  --logs      compact output with live INFO logs
  --debug     verbose output and full captured diagnostics

Use --strict=false only for explicitly best-effort development runs.
""")]
test strict="true" fast="false" dev="false" quiet="" logs="" debug="" failing="false":
  #!/usr/bin/env bash
  set -euo pipefail

  mode_count=0
  [ -n "{{quiet}}" ] && mode_count=$((mode_count + 1))
  [ -n "{{logs}}" ]  && mode_count=$((mode_count + 1))
  [ -n "{{debug}}" ] && mode_count=$((mode_count + 1))

  if [ "$mode_count" -gt 1 ]; then
    echo "[test] ERROR: choose at most one of --quiet, --logs, or --debug" >&2
    exit 2
  fi

  mode="default"
  if [ -n "{{quiet}}" ]; then mode="quiet"; fi
  if [ -n "{{logs}}" ];  then mode="logs";  fi
  if [ -n "{{debug}}" ]; then mode="debug"; fi

  case "$mode" in
    default) mode_flags="" ;;
    quiet)   mode_flags='{{PYTEST_QUIET_OPTS}}' ;;
    logs)    mode_flags='{{PYTEST_LOG_OPTS}}' ;;
    debug)   mode_flags='{{PYTEST_DEBUG_OPTS}}' ;;
  esac

  args=({{PYTEST}})

  eval "args+=({{PYTEST_BASE_OPTS}})"

  if [ -n "$mode_flags" ]; then
    eval "args+=($mode_flags)"
  fi

  # Append optional flags directly. This avoids expanding a potentially empty
  # array under `set -u`, which fails with the Bash 3.2 shipped by macOS.
  if [ "{{fast}}" = "true" ]; then
    eval "args+=({{PYTEST_FAST_OPTS}})"
  fi

  if [ "{{failing}}" = "true" ]; then
    eval "args+=({{PYTEST_FAILING_OPTS}})"
  fi

  test_paths=("{{ROOT_DIR}}/{{PY_TESTPATH}}")

  if [ "{{dev}}" = "true" ]; then
    if [ "{{fast}}" = "true" ] || [ "{{failing}}" = "true" ] || \
       [ "{{strict}}" != "true" ] || [ "$mode" != "default" ]; then
      echo "[test] --dev is impact selection; do not combine it with --fast, --failing or display overrides" >&2
      echo "[test] use test-focus for a selection, or test-impact-seed then test-impact" >&2
      exit 2
    fi
    just test-impact
    exit $?
  fi

  args+=("${test_paths[@]}")

  printf '[test]'
  printf ' %q' "${args[@]}"
  printf '\n'

  set +e
  "${args[@]}"
  status=$?
  set -e

  if [ "{{strict}}" = "true" ]; then
    exit "$status"
  fi

  if [ "$status" -ne 0 ]; then
    echo "[test] WARNING: pytest exited with status $status (--strict=false)" >&2
  fi

  exit 0


# Impact selection requires a complete initial baseline. Seed is intentionally
# a FULL serial no-coverage test run; do not launch it automatically on edits.
# Store the DB under ignored .cache/testmon/<python-minor>/ in this worktree.
[group('testing')]
test-impact-seed:
  @{{DEV_TESTS}} seed


# Re-run only affected tests after a successful baseline. This is a development
# optimization and never counts as full acceptance.
[group('testing')]
test-impact:
  @{{DEV_TESTS}} impact


# Explicit bounded parallel testing; avoid xdist startup for focused tests.
# The default is 4 workers and load distribution, not the host CPU count.
[group('testing')]
test-parallel workers="4":
  @{{DEV_TESTS}} parallel --workers "{{workers}}"


# Experimental combination: opt-in only because selected tests and subprocess
# scheduling can have different cold/warm performance and isolation demands.
[group('testing')]
test-impact-parallel workers="4":
  @{{DEV_TESTS}} impact-parallel --workers "{{workers}}"


# Capture the slowest test cases without coverage or testmon selection.
[group('testing')]
test-timings:
  @{{DEV_TESTS}} timings


# Fast local feedback: run an explicitly selected test module, node ID or
# directory. This keeps strict pytest marker validation while omitting broad
# discovery and coverage overhead. It is NOT a substitute for just check.
[group('testing')]
[doc("""
Run one focused pytest selection without coverage (stop at first failure).

  just test-focus tests/test_p2_policy_engine.py
  just test-focus tests/test_p2_policy_engine.py::test_p2_nine_orthogonal_axes_and_immutable_profiles

The selection must be explicit: --fast alone still runs the broad suite.
""")]
test-focus selection:
  @{{DEV_TESTS}} focus "{{selection}}"


# Fast, source-nonmutating static feedback; Ruff and ty also parse Python,
# so avoid the redundant repository-wide compileall in this edit-loop recipe.
[group('convenience')]
dev-check:
  @just _log_start dev-check
  @just _run format "just format --check"
  @just _run lint "just lint --no-fix"
  @just _run typecheck "just typecheck"
  @just _run lint-imports "just lint-imports"
  @just _log_end dev-check


# ======================================================================
# Test quality
# ======================================================================

# Report coverage from the most recent coverage-producing test run.
[group('test quality')]
[arg("lines", long, value="true")]
cov lines="false":
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start cov

  if [ "{{lines}}" = "true" ]; then
    {{COVERAGE}} report --show-missing
  else
    {{COVERAGE}} report
  fi

  just _log_end cov


# ======================================================================
# Build / packaging / publishing
# ======================================================================

# Build source and wheel distributions.
[group('production')]
build:
  @just _log_start build
  {{UV}} build
  @just _log_end build


# Build without applying local [tool.uv.sources] overrides.
# This is the appropriate artifact build for release validation.
[group('production')]
build-release:
  @just _log_start build-release
  {{UV}} build --no-sources
  @just _log_end build-release


# Warm the uv cache for the *current project's version* wheel and dependencies.
# Network access is allowed *only* here; the subsequent qualification is offline.
[group('production')]
standalone-prepare:
  #!/usr/bin/env bash
  set -euo pipefail
  just _log_start standalone-prepare
  {{UV}} run --no-sync python scripts/check_standalone_wheel.py --prepare
  just _log_end standalone-prepare


# Install the current project's release wheel offline in a fresh audio-free environment.
[group('production')]
standalone-check:
  #!/usr/bin/env bash
  set -euo pipefail
  just _log_start standalone-check
  {{UV}} run --no-sync python scripts/check_standalone_wheel.py
  just _log_end standalone-check


# Publish artifacts in dist/.
# Publishing is intentionally separate from validation so it is never an
# accidental consequence of another recipe.
[group('production')]
publish:
  @just _log_start publish
  {{UV}} publish
  @just _log_end publish


# ======================================================================
# Cleaning / maintenance
# ======================================================================

# Remove generated repository state while preserving the virtual environment.
[group('cleaning')]
clean:
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start clean

  # Avoid traversing .venv when deleting Python bytecode caches.
  find . \
    -path './.venv' -prune -o \
    -name '__pycache__' -type d -prune -exec rm -rf '{}' +

  rm -rf \
    .cache \
    .ruff_cache \
    .pytest_cache \
    .mypy_cache \
    .pytype \
    .import_linter_cache \
    .coverage \
    .coverage.* \
    coverage.xml \
    htmlcov \
    .hypothesis \
    .ropefolder \
    .ropeproject \
    .wily \
    mutants \
    dist \
    build \
    logs

  just _log_end clean


# Stash only untracked, non-ignored files before destructive `git clean`.
[group('cleaning')]
stash-untracked:
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start stash-untracked

  files=()
  file_count=0

  while IFS= read -r -d '' file; do
    files+=("$file")
    file_count=$((file_count + 1))
  done < <(git ls-files --others --exclude-standard -z)

  # Do not inspect or expand the array until we know it is non-empty. Empty
  # arrays are unsafe with `set -u` in the Bash 3.2 shipped by macOS.
  if [ "$file_count" -eq 0 ]; then
    echo "No untracked non-ignored files to stash."
    exit 0
  fi

  msg="scour:untracked:$(date -u +%Y%m%dT%H%M%SZ)"
  git stash push --include-untracked -m "$msg" -- "${files[@]}" >/dev/null

  just _log_end stash-untracked


# Remove ignored repository files while retaining .venv.
[group('cleaning')]
scour:
  #!/usr/bin/env bash
  set -euo pipefail

  just _log_start scour
  just clean
  just stash-untracked

  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git clean -fXd -e .venv/
  else
    echo "[scour] not a git repository; skipping"
  fi

  just _log_end scour


# ======================================================================
# Composite workflows
# ======================================================================

# Best-effort local repair loop: mutate/fix static code only.
#
# Full tests/coverage are intentionally excluded from normal interactive
# editing. Run just test-focus <selection> for focused feedback and just check
# before accepting changes. The historical heavier workflow is just fix-full.
# Mutating/static repair steps continue after individual failures so one
# problem does not hide unrelated fixable problems.
[group('convenience')]
fix:
  @just _log_start fix
  @just _run_soft sync "just sync"
  @just _run_soft syntax "just syntax"
  @just _run_soft format "just format"
  @just _run_soft lint "just lint"
  @just _run_soft typecheck "just typecheck"
  @just _run_soft lint-imports "just lint-imports"
  @just _log_end fix


# Historical comprehensive repair-and-fast-suite behavior, now explicitly
# opt-in. This still executes most tests and instruments coverage.
[group('convenience')]
fix-full:
  @just _log_start fix-full
  @just _run fix "just fix"
  @just _run "test --fast" "just test --fast"
  @just _run_soft cov "just cov"
  @just _log_end fix-full


# M2 contract test development (does not assert full checklist closure).
[group('testing')]
m2-contracts:
  @just _run m2-contracts "{{PYTEST}} -q --tb=short tests/m2_acceptance"


# M2 contract acceptance: audited tests, required coverage, SHA-bound receipt.
# Run independently from release packaging; output is deliberately untracked.
[group('testing')]
m2-accept:
  @just _log_start m2-accept
  @just _run m2-contract "{{PYTEST}} -q --tb=short --m2-evidence .artifacts/m2-acceptance.json tests/m2_acceptance"
  @just _log_end m2-accept


# M3 nested document, explicit registry and contextual safety contracts.
# These are in addition to the repository/release gates; do not infer acceptance
# from this focused suite without a clean-SHA just check and release-check.
[group('testing')]
m3-contracts:
  @just _run m3-contracts "{{PYTEST}} -q --tb=short tests/test_m3_nested_routing.py tests/test_document_dispatch.py tests/test_embedded_domain_contract.py tests/test_extension_registry.py tests/test_contextual_proposals.py tests/test_contextual_resolution.py"


# M4 expert-domain golden readings and parser-verified source evidence.
# The corpus records unimplemented context/dialect candidates separately.
[group('testing')]
m4-contracts:
  @just _run m4-contracts "{{PYTEST}} -q --tb=short tests/test_m4_expert_goldens.py tests/test_m4_domain_provenance.py tests/test_m4_contextual_domains.py tests/test_structured_domains.py tests/test_phase2_source.py tests/test_markdown_tables.py"

# P0 golden-first typed-semantics and policy contract. These tests execute only
# frozen M6 outputs and validate future target fixtures; they do not claim P1–P5.
[group('testing')]
p0-contracts:
  @just _run p0-contracts "{{PYTEST}} -q --tb=short tests/test_p0_semantic_policy_contract.py tests/test_m4_expert_goldens.py tests/test_m6a_release_contract.py tests/test_m6b_quality_and_witnesses.py tests/test_m6b_cross_representation.py tests/test_stage_pipeline.py"


# P1 host-independent immutable semantic document and one-registry contracts.
# Future P2/P3 policy realization is explicitly out of scope.
[group('testing')]
p1-contracts:
  @just _run p1-contracts "{{PYTEST}} -q --tb=short tests/test_p1_semantic_document.py tests/test_p0_semantic_policy_contract.py tests/test_stage_pipeline.py tests/test_extension_registry.py tests/test_structured_contracts.py"


# P2 typed compositional policy, caller authority, bounded native date/time
# re-realization, CLI compatibility and cross-representation fallback contracts.
[group('testing')]
p2-contracts:
  @just _run p2-contracts "{{PYTEST}} -q --tb=short tests/test_p2_policy_engine.py tests/test_p2_cli_policy.py tests/test_p1_semantic_document.py tests/test_p0_semantic_policy_contract.py tests/test_m4_expert_goldens.py tests/test_cli_presentation.py tests/test_m6b_cross_representation.py"


# Current P2 edit loop: run ONLY policy/CLI test files without coverage.
# Use p2-contracts for broader milestone regressions; check remains mandatory.
[group('testing')]
p2-focus:
  @just _run p2-focus "{{DEV_TESTS}} focus tests/test_p2_policy_engine.py tests/test_p2_cli_policy.py"


# Scope-and-export traceability; this does not qualify downstream release gates.
[group('testing')]
m6a-contracts:
  @just _run m6a-contracts "{{PYTEST}} -q --tb=short tests/test_m6a_release_contract.py tests/test_m4_expert_goldens.py tests/m2_acceptance"


# M6b frozen supported-syntax review, cross-renderer truth and metamorphic proof.
[group('testing')]
m6b-contracts:
  @just _run m6b-contracts "{{PYTEST}} -q --tb=short tests/test_m6b_quality_and_witnesses.py tests/test_m6b_cross_representation.py tests/test_m6b_metamorphic.py tests/test_m4_expert_goldens.py tests/test_m4_domain_provenance.py tests/test_structured_domains.py tests/test_phase2_numeric.py tests/test_phase2_temporal_provenance.py tests/test_phase2_math_provenance.py tests/test_phase2_special_math_provenance.py tests/test_phase2_multiline_code_provenance.py tests/test_url_field_provenance.py tests/test_path_component_provenance.py tests/test_hierarchical_presentation.py tests/test_markdown_cell_provenance.py tests/test_document_dispatch.py tests/test_m3_nested_routing.py tests/test_phase2_source.py tests/test_m4_contextual_domains.py tests/test_presentation_contract.py tests/test_m2b_intelligibility_corpus.py tests/test_m2c_locale_and_native_bounds.py tests/test_pls_interchange.py"


# M6c security/resource qualification exercises source and file trust boundaries.
[group('testing')]
m6c-contracts:
  @just _run m6c-contracts "{{PYTEST}} -q --tb=short tests/test_m6c_security_bounds.py tests/test_m6c_cli_payload_limits.py tests/test_m6c_property_bounds.py tests/test_m6c_benchmark_contract.py tests/test_m6b_metamorphic.py tests/test_m4_contextual_domains.py tests/test_contextual_proposals.py tests/test_m2c_locale_and_native_bounds.py tests/test_m2c_native_lexicon_entry_limit.py tests/test_pls_interchange.py tests/test_structured_contracts.py tests/test_source_pronunciation.py tests/test_m3_nested_routing.py tests/test_m6b_cross_representation.py"

# Local offline baseline measurement; results are not invented release thresholds.
[group('testing')]
m6c-benchmark:
  @just _run m6c-benchmark "{{UV}} run python scripts/m6c_benchmark.py --repeat 12 --warmup 2 --output .artifacts/m6c-benchmark.json"


# Canonical repository validation gate.
#
# Every validation step is strict. A failing lint, format, typing,
# architecture, or test check causes this recipe to fail.
[group('convenience')]
check:
  @just _log_start check
  @just _run syntax "just syntax"
  @just _run format "just format --check"
  @just _run lint "just lint --no-fix"
  @just _run typecheck "MODE=ci just typecheck"
  @just _run lint-imports "just lint-imports"
  @just _run test "just test"
  @just _run cov "just cov"
  @just _log_end check



# M6d authored release contract, source-controlled installed-wheel consumer,
# offline verifier and historical semantic/provenance/security regression gates.
[group('testing')]
m6d-contracts:
  @just _run m6d-contracts "{{PYTEST}} -q --tb=short tests/test_m6d_release_artifacts.py tests/test_m6a_release_contract.py tests/test_standalone_dependency_contract.py tests/test_reader_distribution_boundary.py tests/test_package_integration.py tests/test_m6b_cross_representation.py tests/test_m6c_security_bounds.py"

# The final M6d proof is deliberately SHA-bound. It refuses dirty trees,
# captures logs and wheel hash, but never publishes a package or commits.
[group('production')]
m6d-qualify:
  @just _run m6d-qualify "{{UV}} run python scripts/m6d_qualify.py"


# Release preflight: validate the repository and prove that a distribution can
# be built without local uv source overrides.
[group('production')]
release-check:
  @just _log_start release-check
  @just _run check "just check"
  @just _run build-release "just build-release"
  @just _run standalone-prepare "just standalone-prepare"
  @just _run standalone-check "just standalone-check"
  @just _log_end release-check
