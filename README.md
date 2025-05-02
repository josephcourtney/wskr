# wskr

**wskr** is a minimal Python CLI template designed to get you up and running fast

---

## 🚀 Quick Start

Install it locally for development:

```bash
git clone 
cd wskr
uv sync
```

Or install directly with uv:

```bash
uv add wskr
```

---

## ✨ Features

- Does a thing!

---

## 🧠 Example

Say your CLI just says hello:

```python
from clio.click_utils import command_with_io

@command_with_io
def main(name: str) -> str:
    return f"Hello, {name}!"
```

Now run:

```bash
echo "World" | python -m wskr
# → Hello, World!
```

From env:

```bash
export NAME=Alice
python -m wskr --input-source env --input-name NAME
# → Hello, Alice!
```

From file:

```bash
echo "Charlie" > name.txt
python -m wskr --input-source file --input-name name.txt
# → Hello, Charlie!
```

To file:

```bash
echo "Dana" | python -m wskr --output-dest file --output-name greeting.txt --force
cat greeting.txt
# → Hello, Dana!
```

## Keeping `__all__` in sync

This project ships with [`awl`](https://github.com/josephcourtney/awl) enabled as a pre‑commit hook. On each commit, `awl` will scan your `src/…/__init__.py` files and automatically update their `__all__` lists so you don’t have to remember to do it by hand.

If you want to run it manually:

````bash
awl --dry-run       # preview changes
awl --diff          # see unified diffs
awl                 # apply in‑place


## 📊 Project Visualization with Grobl

We use [grobl](https://github.com/josephcourtney/grobl) to quickly generate a Markdown‑formatted tree of the entire project (plus file contents) and copy it to the clipboard. This helps reviewers and automated tools get instant visibility into our structure.

**Key Features** :contentReference[oaicite:0]{index=0}
- **Recursive traversal** of all subdirectories
- **Markdown escaping** to handle special characters
- **Clipboard integration** for one‑step copying
- **Configurable ignore patterns** via a `.groblignore`
- **File metadata** (line/character counts) alongside contents
- **Built‑in testing** suite ensuring stable behavior

**Installation & Usage**
```bash
# Install via pipx for sandboxed CLI:
pipx install grobl

# From the project root, run:
grobl

## 🧪 Testing

Tests use `pytest` + `clio`:

```bash
pytest
````

Run with coverage:

```bash
pytest --cov
```

---

## 🛠 Dev Tools

This project includes:

- `ruff` for linting
- `basedpyright` for type checking
- `pytest` for testing
- `hatchling` for builds

---

## 📁 Project Structure

```
wskr/
├── src/
│   └── wskr/
│       ├── __init__.py
│       ├── cli.py        # main entrypoint
│       ├── core.py       # business logic
│       └── __main__.py   # supports `python -m wskr`
├── tests/
│   └── test_cli.py       # CLI tests
```

---

## 📜 License

GPLv3 © [Joseph M. Courtney](https://github.com/josephcourtney)
