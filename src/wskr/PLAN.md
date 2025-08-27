# Reorganization Plan

> **Objective:** decouple terminal‑capability discovery, graphics‑protocol encoders, and front‑end renderers (Matplotlib, Rich, etc.) so that each concern can evolve independently with minimal cross‑impact.

## 1. Guiding Principles

* **Single‑direction dependencies** – upper layers (renderers) may depend on lower layers (protocols → terminal → core) but never the other way around.
* **Tiny, explicit interfaces** – a new terminal detector **or** a new graphics protocol can be added by implementing one protocol class and registering it via an `entry_point`.
* **Headless‑friendly** – all I/O escapes terminal‑oriented helpers; tests can stub any layer in isolation.
* **Soft deprecation** – keep thin re‑export shims for one minor release to avoid breaking existing imports.

## 2. Layered Architecture

| Layer (pkg)   | Responsibility                                                            | Depends on      |
| ------------- | ------------------------------------------------------------------------- | --------------- |
| **`render/`** | Adapt external libs (Matplotlib, Rich, …) to *any* image protocol.        | `proto`, `core` |
| **`protocol/`**  | Encode/stream images for a specific graphics protocol (Kitty, Sixel, …).  | `term`, `core`  |
| **`terminal/`**   | Query per‑terminal capabilities (window size, OSC colours, dark‑mode, …). | `core`          |
| **`core/`**   | Pure helpers – config, errors, misc utilities.                            | —               |

> **Rule:** A higher layer may import only the layers listed to its right.

## 3. Target Package Layout

```text
wskr/
├── core/
│   ├── __init__.py          # re‑exports config, errors, util
│   ├── config.py
│   ├── errors.py
│   └── util.py
│
├── terminal/
│   ├── __init__.py          # auto‑detect & registry helpers
│   ├── io.py               # TTY read/write + context mgrs (from ttyools)
│   ├── osc.py              # OSC/ANSI helpers (query_tty, etc.)
│   ├── generic.py          # POSIX fallback detector
│   └── kitty.py            # Kitty‑specific colour/window queries
│        # (future) iterm2.py, wezterm.py, …
│
├── protocol/
│   ├── __init__.py          # public registry API
│   ├── base.py             # `ImageProtocol` ABC
│   ├── kitty.py            # chunks + parser only
│   ├── sixel.py
│   ├── noop.py
│   └── registry.py         # entry‑point loading & policy
│
├── render/
│   ├── __init__.py          # high‑level helpers (wskr.render.mpl.use)
│   ├── mpl/
│   │   ├── __init__.py
│   │   ├── backend.py      # canvas, autosize, interactive glue
│   │   ├── autosize.py
│   │   └── dark_mode.py
│   └── rich/
│       ├── __init__.py
│       ├── image.py        # RichImage
│       └── plot.py         # RichPlot
│
├── cli/
│   └── demo.py              # thin wrapper around render.mpl
└── plugins/                 # 3rd‑party entry‑points
```

## 4. Public Interfaces

### 4.1 `terminal` – Terminal capabilities

```python
class TerminalCapabilities(Protocol):
    def window_px(self) -> tuple[int, int]: ...
    def is_dark(self) -> bool: ...
```

### 4.2 `protocol` – Image encoders

```python
class ImageProtocol(Protocol):
    def send_once(self, png: bytes) -> None: ...
    def upload(self, png: bytes) -> int: ...
```

### 4.3 `render` helpers

```python
mpl.use(protocol="kitty", caps="kitty")
rich.Image(fig, protocol="sixel", caps="wezterm")
```

## 5. Migration Roadmap

1. **Scaffold folders** above; add `__init__.py` stubs.
2. **Move** `ttyools.py` → `terminal/io.py` & `terminal/osc.py` (split query helpers).
3. **Extract** Kitty colour/window queries to `terminal/kitty.py`.
4. **Move** `kitty/parser.py` + protocol parts of `kitty/transport.py` → `protocol/kitty.py`.
5. **Create** `protocol/base.py`, port `NoOpTransport` → `protocol/noop.py`.
6. **Refactor registries**

   * protocol registry: `protocol/registry.py`
   * (optional) terminal‑cap detector registry later.
7. **Port renderers**

   * Move all of `mpl/` into `render/mpl/`
   * Move `kitty/rich/*` into `render/rich/`
8. **Add shims** in original paths that import from new locations & emit `DeprecationWarning`.
9. **Update imports & tests** (`ruff —fix` & `pyupgrade`).
10. **Doc update** – README, AGENTS.md, CHANGELOG bump.

## 6. Deprecation & Compatibility

* **Shims** remain for ≥ one minor release (`0.0.x → 0.1.0`).
* Raising `TransportUnavailableError` now lives in `proto.errors` but re‑exported in `wskr.errors`.
* CI will run both new & deprecated import paths until removal window expires.

## 7. Testing Strategy

* Move unit tests alongside code (`tests/render/`, `tests/protocol/`, `tests/terminal/`).
* Provide fixtures for `TerminalCapabilities` & `ImageProtocol` to isolate layers.
* Preserve pixel‑perfect reference test for Kitty by importing through new layout.
