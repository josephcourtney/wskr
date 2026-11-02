"""Run an existing P3 harness in the isolated Kitty GUI, then expose its exit status.

The outer yabai controller owns window operations; this entrypoint leaves the
actual harness as foreground TTY owner and a visible zsh prompt after it exits.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed local harness argv
import sys
from pathlib import Path

CASES = ("resize", "paging", "lifecycle", "appearance")


def command(case: str, height: int, mode: str) -> list[str]:
    modules = {
        "resize": "scripts.phase3_native_macos_resize",
        "paging": "scripts.phase3_native_macos_paging",
        "lifecycle": "scripts.phase3_native_macos_lifecycle",
        "appearance": "scripts.phase3_native_macos_appearance",
    }
    result = [sys.executable, "-m", modules[case], "--mode", mode]
    if case == "resize":
        result += ["--height", str(height), "--clean-scrollback"]
    elif case == "paging":
        result += ["--require-capacity-change"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--height", type=int, choices=(2, 6), default=2)
    parser.add_argument("--mode", choices=("unmanaged", "yabai"), required=True)
    args = parser.parse_args()
    control = os.environ.get("WSKR_NATIVE_CONTROL_DIR")
    if not control:
        parser.error("Only the explicit native yabai controller may launch this entrypoint")
    base = Path("artifacts") / f"phase3-native-{args.case}"
    before = set(base.glob("*.zip"))
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed argv
        command(args.case, args.height, args.mode), check=False
    )
    new_archives = list(set(base.glob("*.zip")) - before)
    evidence = str(new_archives[0].resolve()) if len(new_archives) == 1 else None
    result = {
        "returncode": completed.returncode,
        "case": args.case,
        "height": args.height,
        "mode": args.mode,
        "evidence_archive": evidence,
        "archive_count": len(new_archives),
    }
    directory = Path(control)
    tmp = directory / "completed.tmp"
    tmp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    tmp.replace(directory / "completed.json")
    print(f"WSKR_NATIVE_AUTO_EXIT:{completed.returncode}", flush=True)
    # A deterministic real zsh prompt is independently checkable through
    # Kitty's window-scoped get-text API; no synthetic keyboard input needed.
    os.environ["PROMPT"] = "WSKR_NATIVE_AUTO_PROMPT> "
    os.execv(  # ruff: ignore[start-process-with-no-shell] - test-only owned terminal
        "/bin/zsh", ["/bin/zsh", "-f", "-i"]
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
