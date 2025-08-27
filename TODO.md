# dark mode

* [x] Configure the default chain order to be Env → OSC
* [x] Add a Chain-of-Responsibility in `mpl/utils.py` to try strategies in sequence
* [x] Move all `detect_dark_mode()` calls out of the Matplotlib backend modules (`base.py`, `kitty.py`, `sixel.py`, `iterm2.py`)
* [x] Move all `plt.style.use("dark_background")` calls out of the backend modules
* [x] Introduce a new opt-in startup hook (`wskr.init(style="auto-dark")`) to drive dark-mode styling
* [x] Refactor `src/wskr/mpl/utils.py` to support pluggable dark-mode strategies
* [x] Implement an `EnvColorStrategy` class for dark-mode detection via environment variables
* [x] Implement an `OscQueryStrategy` class for dark-mode detection via OSC 11 queries

# configuration

* [x] Expose a configurable timeout for OSC queries (instead of hard-coded)
* [x] Create a new `wskr.config` module to centralize configuration
* [x] Support both environment variables and keyword args in `wskr.config`, with defined precedence
* [x] Expose knobs via config for timeouts, cache TTLs, fallback behavior, dark-mode policy, etc.
* [x] Remove any remaining hard-coded `timeout=1.0` in Kitty transport and source timeouts from `WSKR_TIMEOUT_S` in config

# testing

* [x] Add a test that renders via both old call sites and asserts the two byte strings are identical
* [x] Cover real terminal I/O (not just mocks) in those dark-mode integration tests
* [x] Write pseudo-TTY integration tests using Python’s `pty` module to simulate OSC 11 for `is_dark_mode_osc`
* [x] Add unit tests for that parser covering OK, error, and partial responses
* [x] Write fault-injection tests simulating partial writes and slow TTY drains to validate `_send_chunk` framing
* [x] Use a fake `stdout.buffer` in those fault-injection tests for isolation

# transport

* [x] Map failures in `src/wskr/tty/registry.py` to those new error types
* [x] Update `get_image_transport()` to distinguish “unknown key” vs “init failed” vs “disabled”
* [x] Only fall back to `NoOpTransport` when `WSKR_FALLBACK=noop` (or `error`) is explicitly configured
* [x] Change `WskrFigureManager` to accept an `ImageTransport` factory `Callable[[], ImageTransport]`
* [x] Spike a pure-Python Kitty transport behind a `WSKR_TRANSPORT=kitty_py` feature flag
* [x] Add CLI flags to `demo` for width, height, zoom, and transport choice
* [x] Replace import-time `ImportError` stubs in `mpl/sixel.py` with a `FeatureUnavailable` check
* [x] Replace import-time `ImportError` stubs in `mpl/iterm2.py` with a `FeatureUnavailable` check
* [x] Make those backends register as “disabled” unless the corresponding `WSKR_ENABLE_*` env var is set

# plugin infrastructure

* [x] Keep `register_image_transport()` but extend it to auto-load entry points

# logging

* [x] Add `logger.debug` calls at each fallback or gate decision point
* [x] Include `exc_info=True` in relevant log calls for backends
* [x] Standardize logger names and messaging conventions across the repo
* [x] In Kitty operations logs, include key fields: transport, timeout, bytes sent, image ID, etc.

# error messages

* [x] Audit exception messages across the codebase and assign each to a local variable before raising
* [x] Define a `TransportInitError` exception
* [x] Define a `TransportUnavailableError` exception
* [x] Define a `TransportRuntimeError` exception
* [x] Surface structured errors (custom exception types) from `CommandRunner`
* [x] Wrap entry-point loading in `try/except` and emit clear diagnostics on failure

# code reorganization

* [x] Extract all pixel→inch conversion logic into `src/wskr/mpl/size.py`
* [x] Update backends and `RichPlot` to use the centralized autosizing module
* [x] Share or centralize any buffer-sizing code between terminal backends and Rich integration
* [x] Extract the `_send_chunk`/response parsing logic in `src/wskr/tty/kitty.py` into its own parser class
* [x] Define a `TtyIO` interface to encapsulate `query_tty()`
* [x] Move `read_tty()` behind the `TtyIO` interface
* [x] Move `write_tty()` behind the `TtyIO` interface
* [x] Create a `TerminalMetrics` parameter object (`w_px, h_px, n_col, n_row, dpi, zoom`)
* [x] Update `compute_terminal_figure_size()` (and related functions) to accept `TerminalMetrics` instead of long arg lists
* [x] Deduplicate the two versions of `_render_to_buffer` in `plt.py` into a single implementation

# subprocess wrapper

* [x] Introduce a `CommandRunner` helper class with a `.run()` method
* [x] Add a `.check_output()` method to `CommandRunner`
* [x] Implement default timeouts in `CommandRunner`
* [x] Add retry logic to `CommandRunner`
* [x] Replace direct `subprocess` calls in `src/wskr/tty/kitty.py` with `CommandRunner`
* [x] Replace subprocess calls in `src/wskr/tty/kitty_remote.py` with `CommandRunner`

# research and demos

* [ ] Research a pure-Python Kitty protocol implementation (socket or OSC-in-stdin) to replace external CLI
* [ ] Implement a `python -m wskr.demo` CLI entry point to render a sample plot
* [ ] Implement `load_entry_points()` support for third-party transports
