## [0.0.5] - 2025-08-27

### Added
- add `MorePredicate` type alias and optional `fd` parameter to `read_tty` for reusable TTY access

### Fixed
- fix `query_tty` to reuse a single TTY file descriptor and close it exactly once

