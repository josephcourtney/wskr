# Changelog

Notable completed user-visible changes, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Introduced provenance-aware terminal measurements, guarded OSC queries, and a pure resolver for terminal-derived Matplotlib defaults.

### Fixed
- Showed an in-layout Rich text fallback when no graphics protocol is configured, instead of silently rendering an empty panel.
- Stopped package import from disabling Matplotlib's TeX setting.
- Made a valid light-theme detection definitive and avoided automatic queries against shared terminal input.
- Prevented legacy PTY color queries from hanging while waiting for terminal output to drain.

### Changed
- Clarified which Kitty, Matplotlib, Rich, Sixel and iTerm2 features are supported today, with the intended architecture documented separately.
- Replaced the copied development workflow with reproducible wskr-specific quality, package, terminal and wheel smoke checks.
- Improved the real Kitty screenshot test to recognize image content across terminal themes and positions instead of requiring identical whole-window pixels.

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
