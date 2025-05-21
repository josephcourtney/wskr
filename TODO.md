* [ ] Feature-gate or fail-fast stub backends - Replace the runtime-only “not implemented” stubs for iTerm2 and Sixel with import-time errors or feature flags so consumers aren’t surprised by a late NotImplementedError.
* [ ] Decouple dark-mode detection from backends - Move calls to `detect_dark_mode()` out of the Matplotlib backend modules into user-configurable startup code to separate styling concerns from rendering logic.
* [ ] Abstract subprocess invocation - Encapsulate all `subprocess.run` and `shutil.which` calls in a helper class with built-in timeouts and retry logic to make command execution testable and robust against hangs.
* [ ] Enhance transport registry error handling - Refine `get_image_transport` to distinguish fatal misconfiguration from transient failures—log tracebacks for debugging rather than silently falling back to NoOpTransport.
* [ ] Add pseudo-TTY integration tests for OSC queries - Write end-to-end tests using Python’s `pty` module to simulate OSC 11 responses and verify `is_dark_mode_osc`, covering real terminal I/O rather than purely mocked behavior.
* [ ] Introduce fault-injection tests for `_send_chunk` - Simulate slow or partial writes in `KittyTransport._send_chunk` to ensure that flush logic and chunk framing behave correctly under backpressure conditions.
* [ ] Evaluate pure-Python Kitty protocol implementation - Research replacing the external `kitty +kitten` CLI calls with a direct socket or OSC-in-stdin approach to remove the external dependency and simplify installation.
* [ ] Unify buffer-sizing logic between backends and `RichPlot` - Share or centralize the code that computes figure dimensions in both the terminal backend and Rich integration to eliminate duplication and ensure consistency.

