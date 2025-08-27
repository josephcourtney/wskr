## [0.0.6] - 2025-08-27

### Added
- add configuration constants and transport enumeration
- add rich image fallback and context-manager hooks
- add cache ttl for kitty window size

### Changed
- replace magic numbers with config module and use pathlib for sockets
- document backend selection and mark slow tests

## [0.0.5] - 2025-08-27

### Added
- add `MorePredicate` type alias and optional `fd` parameter to `read_tty` for reusable TTY access

### Fixed
- fix `query_tty` to reuse a single TTY file descriptor and close it exactly once

