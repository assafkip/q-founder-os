#!/usr/bin/env python3
"""Stop hook with stop_hook_active honor + gate exhaustion (prd-os variant)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


MAX_SAME_SIGNATURE_FIRINGS = 3
FIRINGS_FILENAME = "prdos-stop-gate-firings.json"
RUNNER_TIMEOUT_SECONDS = 5
CONFIG_RELPATH = ".prd-os/config.json"


def _runner_path() -> Path:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root:
        return Path(root) / "scripts" / "issue_runner.py"
    return Path(__file__).resolve().parent.parent / "scripts" / "issue_runner.py"


def _discover_repo_with_config() -> Path | None:
    start: Path | None = None
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        try:
            candidate = Path(env).resolve()
        except (OSError, ValueError):
            candidate = None
        if candidate is not None and candidate.is_dir():
            start = candidate
    if start is None:
        try:
            start = Path.cwd().resolve()
        except (OSError, ValueError):
            return None
    for candidate in (start, *start.parents):
        if (candidate / CONFIG_RELPATH).is_file():
            return candidate
        if (candidate / ".git").exists():
            return None
    return None


def _firings_path(repo: Path) -> Path:
    return repo / ".claude" / "state" / FIRINGS_FILENAME


def _read_firings(repo: Path) -> dict:
    path = _firings_path(repo)
    if not path.is_file():
        return {"signature": None, "count": 0, "last_fired": None}
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return {"signature": None, "count": 0, "last_fired": None}
        return data
    except (json.JSONDecodeError, OSError):
        return {"signature": None, "count": 0, "last_fired": None}


def _write_firings(repo: Path, data: dict) -> None:
    path = _firings_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _clear_firings(repo: Path) -> None:
    path = _firings_path(repo)
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

    if os.environ.get("PRDOS_GATE_OFF") == "1":
        return 0

    repo = _discover_repo_with_config()
    if repo is None:
        return 0
    runner = _runner_path()
    try:
        result = subprocess.run(
            [sys.executable, str(runner), "--repo-root", str(repo), "gate"],
            capture_output=True,
            text=True,
            timeout=RUNNER_TIMEOUT_SECONDS,
        )
    except Exception:
        return 0

    if result.returncode == 0:
        _clear_firings(repo)
        return 0

    if result.returncode != 2:
        return 0

    signature = _signature(result.stderr or "")
    state = _read_firings(repo)
    if state.get("signature") == signature:
        count = int(state.get("count") or 0) + 1
    else:
        count = 1
    _write_firings(repo, {
        "signature": signature,
        "count": count,
        "last_fired": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    if count > MAX_SAME_SIGNATURE_FIRINGS:
        sys.stderr.write(
            f"prd-os stop gate: already notified {count - 1} times with same state. "
            "Exhausted -- allowing session end. Complete the issue to reset, or set "
            "PRDOS_GATE_OFF=1 in the Claude Code env to silence the gate.\n"
        )
        return 0

    stderr_text = (result.stderr or "prd-os stop gate: issue not closed\n").rstrip("\n")
    sys.stderr.write(f"{stderr_text} (firing {count}/{MAX_SAME_SIGNATURE_FIRINGS})\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
