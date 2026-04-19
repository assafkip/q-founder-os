#!/usr/bin/env python3
"""Stop hook with stop_hook_active honor + gate exhaustion.

Primary loop break: honor Claude Code's `stop_hook_active` field on stdin.
When the hook is already in a Stop chain, exit 0 unconditionally.

Backup: signature-based exhaustion for cases where stdin is absent or the
hook runs outside Claude Code.

Counter lives at <repo>/.claude/state/stop-gate-firings.json (local, gitignored).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


MAX_SAME_SIGNATURE_FIRINGS = 3
FIRINGS_FILENAME = "stop-gate-firings.json"


def _runner_path() -> Path:
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        return Path(plugin_root) / "scripts" / "issue_runner.py"
    return Path(__file__).resolve().parents[1] / "scripts" / "issue_runner.py"


def _repo_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return candidate
    return cwd


def _firings_path() -> Path:
    return _repo_root() / ".claude" / "state" / FIRINGS_FILENAME


def _read_firings() -> dict:
    path = _firings_path()
    if not path.is_file():
        return {"signature": None, "count": 0, "last_fired": None}
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return {"signature": None, "count": 0, "last_fired": None}
        return data
    except (json.JSONDecodeError, OSError):
        return {"signature": None, "count": 0, "last_fired": None}


def _write_firings(data: dict) -> None:
    path = _firings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _clear_firings() -> None:
    path = _firings_path()
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


def _signature(stderr_text: str) -> str:
    return hashlib.sha1(stderr_text.strip().encode("utf-8")).hexdigest()[:16]


def _read_stdin_payload() -> dict:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def main() -> int:
    payload = _read_stdin_payload()
    if payload.get("stop_hook_active") is True:
        return 0

    if os.environ.get("ISSUE_GATE_OFF") == "1":
        return 0

    try:
        result = subprocess.run(
            ["python3", str(_runner_path()), "gate"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return 0

    if result.returncode == 0:
        _clear_firings()
        return 0

    signature = _signature(result.stderr or "")
    state = _read_firings()
    if state.get("signature") == signature:
        count = int(state.get("count") or 0) + 1
    else:
        count = 1
    _write_firings({
        "signature": signature,
        "count": count,
        "last_fired": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    if count > MAX_SAME_SIGNATURE_FIRINGS:
        sys.stderr.write(
            f"DSSE stop gate: already notified {count - 1} times with same state. "
            "Exhausted -- allowing session end. Complete the DSSE flow to reset, "
            "or set ISSUE_GATE_OFF=1 in the Claude Code env to silence the gate.\n"
        )
        return 0

    stderr_text = (result.stderr or "DSSE stop gate: issue not closed\n").rstrip("\n")
    sys.stderr.write(
        f"{stderr_text} (firing {count}/{MAX_SAME_SIGNATURE_FIRINGS})\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
