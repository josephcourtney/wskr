# Changelog

Notable **completed** user-visible changes are recorded here, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Design requirements and unfinished work are not release changes.

## [Unreleased]

### Changed
- harden optional GUI window-manager probing and separate live Kitty image-submission smoke from screenshot comparison
- repair the remaining baseline-script lint issue and preserve test helper JSON failure behavior
- improve Phase 0 diagnostic scripts, Ruff compatibility checks, and GUI screenshot-test timeout/window discovery
- stabilize float assertions in legacy tests without altering their behavior
- add reproducible baseline diagnostics, installed-wheel smoke test and behavior-characterization tests
- replace copied development recipes with wskr-specific `uv`/Ruff/`ty`/pytest/Kitty commands
- remove unrelated Cwide Ruff overrides and temporarily disable strict test-category enforcement during baseline establishment
- clarify supported Kitty and Rich workflows and distinguish currently experimental or unavailable transports in the README
- organize the target design, implementation plan, short-horizon status, immediate tasks, and architectural decision rationale according to POLICY.md

## [0.0.16] - 2025-08-29

### Changed
- move terminal I/O helpers to `wskr.terminal.io` and OSC query helper to `wskr.terminal.osc`

## [0.0.15] - 2025-08-28

### Removed
- drop deprecated shim modules `wskr.kitty.*`, `wskr.tty.*`, `wskr.mpl.*`, and `wskr.ttyools`

### Changed
- update imports to `wskr.terminal.core`, `wskr.protocol.kgp`, and `wskr.render.*`

## [0.0.14] - 2025-08-27

### Added
- add compatibility shims for legacy imports (`wskr.config`, `wskr.errors`, `wskr.tty.*`, `wskr.mpl.*`, `wskr.kitty.*`)

### Changed
- fix top-level imports in `wskr.__init__` to use new package layout

## [0.0.13] - 2025-08-27

### Fixed
- ensure NoOp transport registers even after registry reset

## [0.0.12] - 2025-08-27

### Changed
- split Kitty-dependent functionality into a dedicated subpackage

## [0.0.11] - 2025-08-27

### Added
- add demonstration CLI via `python -m wskr.demo`
- add `darkdetect`-based fallback for dark-mode detection
- add `query_kitty_color` helper for theme-aware plotting
- add `load_entry_points` function for third-party transports

## [0.0.10] - 2025-08-27

### Added
- add transport runtime error and command runner error types
- log Kitty operations with additional diagnostic context

### Changed
- standardize backend logging and diagnostics

## [0.0.9] - 2025-08-27

### Added
- add dark-mode detection strategies and `wskr.init` hook
- expose central configuration with environment and runtime overrides

### Changed
- source Kitty timeouts from configuration
- remove dark-mode styling from backend modules

## [0.0.8] - 2025-08-27

### Added
- add `CommandRunner` helper for subprocess execution

### Changed
- replace direct subprocess calls in Kitty transports with `CommandRunner`

## [0.0.7] - 2025-08-27

### Added
- add terminal sizing helpers and `TerminalMetrics` data class
- add `TtyIO` interface and Kitty chunk parser

### Changed
- centralize pixel-to-inch conversion in Matplotlib size helpers
- deduplicate render-buffer logic in Rich plotting
- route Kitty chunk handling through a dedicated parser

## [0.0.6] - 2025-08-27

### Added
- add configuration constants and transport enumeration
- add Rich-image fallback and context manager hooks
- add TTL caching for Kitty window size

### Changed
- replace magic numbers with configuration and pathlib for sockets
- document backend selection and mark slow tests

## [0.0.5] - 2025-08-27

### Added
- add `MorePredicate` type alias and optional `fd` parameter to `read_tty`

### Fixed
- fix `query_tty` to reuse a single file descriptor and close it exactly once
