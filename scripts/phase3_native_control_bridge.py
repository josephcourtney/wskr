"""Bounded file-based coordination between a native Kitty worker and its GUI controller.

The worker never reads another process's terminal input. An isolated controller
owns GUI resizing, window capture and remote input. No background threads.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

_TIMEOUT = 90.0


def enabled() -> bool:
    return bool(os.environ.get("WSKR_NATIVE_CONTROL_DIR"))


def request(action: str, **details: Any) -> dict:
    """Wait for one controller acknowledgement without touching foreground stdin."""
    directory = os.environ.get("WSKR_NATIVE_CONTROL_DIR")
    if not directory:
        msg = "Automation request without a controller directory"
        raise RuntimeError(msg)
    root = Path(directory)
    events = root / "events"
    acks = root / "acks"
    identifier = uuid.uuid4().hex
    payload = {"id": identifier, "action": action, "details": details, "pid": os.getpid()}
    tmp = events / f".{identifier}.tmp"
    target = events / f"{identifier}.json"
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(target)
    reply = acks / f"{identifier}.json"
    deadline = time.monotonic() + _TIMEOUT
    while time.monotonic() < deadline:
        if reply.exists():
            result = json.loads(reply.read_text(encoding="utf-8"))
            reply.unlink()
            if not result.get("ok"):
                msg = f"Native controller rejected {action}: {result.get('error', 'unknown error')}"
                raise RuntimeError(msg)
            return result
        time.sleep(0.05)
    msg = f"Native controller did not acknowledge {action} within {_TIMEOUT:.0f}s"
    raise TimeoutError(msg)
