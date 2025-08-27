* [ ] Centralize dark-mode styling — Move `detect_dark_mode()` calls and `plt.style.use("dark_background")` out of backends (`src/wskr/mpl/base.py`, `kitty.py`, `sixel.py`, `iterm2.py`) into a single opt-in startup hook (e.g., `wskr.init(style="auto-dark")`) to decouple styling from rendering.
* [ ] Add dark-mode strategy injection — Refactor `src/wskr/mpl/utils.py` to support pluggable strategies (`EnvColorStrategy`, `OscQueryStrategy`) with a simple Chain-of-Responsibility; default to env→OSC; make timeout configurable.
* [ ] Provide `WSKR_DARK_MODE` override — Allow explicit `true/false/auto` env or config flag to bypass detection; document precedence: explicit > env var > detection > default.
* [ ] Abstract TTY query I/O — Wrap `query_tty`, `read_tty`, `write_tty` from `src/wskr/ttyools.py` behind an interface (e.g., `TtyIO`) to enable dependency injection and easier mocking.
* [ ] Consolidate subprocess execution — Introduce `CommandRunner` helper with `run()`, `check_output()`, default timeouts, retries, and structured errors; use in `src/wskr/tty/kitty.py` and `src/wskr/tty/kitty_remote.py`.
* [ ] Make timeouts configurable — Replace hardcoded `timeout=1.0` in Kitty transport calls with values sourced from config/env (e.g., `WSKR_TIMEOUT_S`) and passed via `CommandRunner`.
* [ ] Replace runtime stubs with feature gates — For `src/wskr/mpl/sixel.py` and `src/wskr/mpl/iterm2.py`, turn import-time `ImportError` into a `FeatureUnavailable` check that cleanly registers a disabled backend unless `WSKR_ENABLE_*` is set.
* [ ] Promote transports to first-class plugins — Keep `register_image_transport()` but add `load_entry_points` support (optional) to auto-register transports from third-party packages; guard with try/except and clear diagnostics.
* [ ] Clarify backend error surfaces — Introduce `TransportInitError`, `TransportUnavailableError`, `TransportRuntimeError` and map failures in `src/wskr/tty/registry.py` to these; improve logs with `exc_info=True`.
* [ ] Improve `get_image_transport()` semantics — Distinguish “unknown key” vs “init failed” vs “disabled”; only fall back to `NoOpTransport` when configured to do so (`WSKR_FALLBACK=noop|error`).
* [ ] Encapsulate figure autosizing policy — Move pixel→inches logic used by backends and `RichPlot` into a single module (e.g., `src/wskr/mpl/size.py`) to remove duplication and ensure consistent sizing.
* [ ] Add parameter object for sizing — Define `TerminalMetrics(w_px,h_px,n_col,n_row,dpi,zoom)` and pass around instead of long parameter lists (`compute_terminal_figure_size` & friends).
* [ ] Guard `WskrFigureCanvas.draw()` reentrancy explicitly — Replace ad-hoc `_in_draw` flag with a private contextmanager `_guard_draw()` and document why; add unit test for re-entrant protection.
* [ ] Dependency inversion for transports — Allow `WskrFigureManager` to accept a factory `Callable[[], ImageTransport]` (defaulting to registry) for better testability.
* [ ] Cache invalidation for Kitty window size — Add TTL for `KittyTransport._cached_size` and an explicit `invalidate_cache()`; expose `WSKR_CACHE_TTL_S` env to tune.
* [ ] Strengthen Kitty protocol parsing — Extract the `_send_chunk`/response parse in `src/wskr/tty/kitty.py` into a small parser class with tests for OK/error/partial responses.
* [ ] Fault-injection tests for Kitty chunking — Add tests simulating partial writes/slow TTY to validate `_send_chunk` framing and flush behavior (leverage a fake `stdout.buffer`).
* [ ] Add pseudo-TTY tests for OSC 11 — Use `pty` in tests to simulate ANSI responses for `is_dark_mode_osc()`; verify happy-path and malformed responses.
* [ ] Centralize configuration — Add `wskr.config` module supporting env + kwargs with precedence; surface knobs (timeouts, cache TTLs, fallback behavior, dark-mode policy).
* [ ] Improve structured logging — Standardize logger names and messages; include key fields (transport, timeout, bytes, img\_id) for Kitty operations; add `logger.debug` on decisions (fallbacks, gates).
* [ ] Strengthen error messages (style preference) — Assign exception messages to variables before raising (personal style) across the codebase for consistency.
* [ ] Use type aliases & annotations — Add precise types for callables: e.g., `type MorePredicate = Callable[[bytes], bool]` in `ttyools.py`; annotate public APIs throughout.
* [ ] Path handling with `pathlib` — Replace raw string paths with `Path` in `RichImage`, payload scripts, and kitty\_remote helper paths; ensure encoding explicitness when reading files.
* [ ] Prefer `dataclass` for config structs — Convert `WindowConfig` (already a dataclass) patterns to similar small structs where appropriate (e.g., `TerminalMetrics`, `KittyInitResponse`).
* [ ] Add `__slots__` to high-churn classes — For `RichImage` and lightweight transport helpers to reduce memory overhead during repeated renders.
* [ ] Avoid global Console — In `src/wskr/rich/img.py`/`plt.py`, avoid module-level `Console()`; take console from Rich call context only to reduce hidden globals.
* [ ] Document backend selection — README: document Matplotlib backend entry points and how to choose (`MPLBACKEND=wskr_kitty`) plus feature gates; clarify test environment hints.
* [ ] Harden `tty_attributes` usage — Ensure the fd is captured once, use it consistently, and avoid multiple `os.open()` calls; add tests that assert a single open/close per operation.
* [ ] Unify PNG rendering path — Deduplicate `_render_to_buffer` in `plt.py` (two versions exist) to a single function; add test that asserts identical bytes for both call sites.
* [ ] Graceful teardown hooks — Provide `close()`/context manager for transports that may hold resources later; no-op for current transports; add to interface for forward compatibility.
* [ ] Replace magic numbers — Extract `_IMAGE_CHUNK_SIZE = 4096`, rows=24 heuristic, etc., into `wskr.config` with sensible defaults and docstrings.
* [ ] Enum over strings — Introduce `Enum` for transport names (KITTY/NOOP/…) to reduce typos; keep registry mapping but validate against enum.
* [ ] Improve RichImage fallback — When `init_image` fails (returns -1), automatically fall back to single `send_image` drawing path; emit one warning not per row.
* [ ] Add pure-Python Kitty option (investigate) — Spike a socket/OSC-to-stdin approach (no `+kitten icat` dependency); guard behind `WSKR_TRANSPORT=kitty_py` feature flag.
* [ ] CLI demo tool — `python -m wskr.demo` to render a sample plot with explicit flags for width/height/zoom/transport to aid user troubleshooting.
* [ ] CI: add a “slow” mark — Separate fault-injection and pseudo-PTY tests behind `-m slow` and run them in nightly pipeline to keep PR checks fast.
* [ ] Coverage for error branches — Add tests that exercise: unknown registry key, transport init failure, bad Kitty response, bad OSC parse, invalid `COLORFGBG`.
* [ ] Improve `plot.create_share_dict` — Add docstring examples and input validation; support dict-style input `{group_id: [idx...]}`; raise informative errors on overlap/group misuse.
* [ ] Validate subplot overlaps early — In `check_for_overlaps`, return a structured report (ranges causing conflicts); use in tests to assert detection quality.

* [ ] Feature-gate or fail-fast stub backends - Replace the runtime-only “not implemented” stubs for iTerm2 and Sixel with import-time errors or feature flags so consumers aren’t surprised by a late NotImplementedError.
* [ ] Decouple dark-mode detection from backends - Move calls to `detect_dark_mode()` out of the Matplotlib backend modules into user-configurable startup code to separate styling concerns from rendering logic.
* [ ] Abstract subprocess invocation - Encapsulate all `subprocess.run` and `shutil.which` calls in a helper class with built-in timeouts and retry logic to make command execution testable and robust against hangs.
* [ ] Enhance transport registry error handling - Refine `get_image_transport` to distinguish fatal misconfiguration from transient failures—log tracebacks for debugging rather than silently falling back to NoOpTransport.
* [ ] Add pseudo-TTY integration tests for OSC queries - Write end-to-end tests using Python’s `pty` module to simulate OSC 11 responses and verify `is_dark_mode_osc`, covering real terminal I/O rather than purely mocked behavior.
* [ ] Introduce fault-injection tests for `_send_chunk` - Simulate slow or partial writes in `KittyTransport._send_chunk` to ensure that flush logic and chunk framing behave correctly under backpressure conditions.
* [ ] Evaluate pure-Python Kitty protocol implementation - Research replacing the external `kitty +kitten` CLI calls with a direct socket or OSC-in-stdin approach to remove the external dependency and simplify installation.
* [ ] Unify buffer-sizing logic between backends and `RichPlot` - Share or centralize the code that computes figure dimensions in both the terminal backend and Rich integration to eliminate duplication and ensure consistency.
