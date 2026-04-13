#!/usr/bin/env python3
"""
Verify that all ripple targets were addressed after canonical edits.

Usage:
    python3 ripple-verify.py <changelog-path> <date> [--json]

Reads today's changelog entries, looks up ripple targets for each,
checks if those targets also have changelog entries for today.

Exit 0 = all targets addressed
Exit 1 = missing targets (printed to stdout)
Exit 2 = ripple-graph.json missing or malformed
"""

import json
import os
import re
import sys

QROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
RIPPLE_GRAPH = os.path.join(QROOT, ".q-system", "ripple-graph.json")


def load_ripple_graph():
    try:
        with open(RIPPLE_GRAPH) as f:
            return json.load(f)["graph"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: ripple-graph.json: {e}", file=sys.stderr)
        sys.exit(2)


def parse_changelog_entries(changelog_path, target_date):
    entries = []
    files_touched = set()
    try:
        with open(changelog_path) as f:
            content = f.read()
    except FileNotFoundError:
        return entries, files_touched

    pattern = rf"### {re.escape(target_date)} \| ([^\|]+) \| ([^\n]+)"
    for match in re.finditer(pattern, content):
        file_key = match.group(2).strip()
        entries.append({"file": file_key})
        files_touched.add(file_key)

    return entries, files_touched


def get_all_ripple_targets(graph, entries):
    required = {}
    for entry in entries:
        file_key = entry["file"]
        targets = graph.get(file_key, [])
        for t in targets:
            if t != file_key:
                if t not in required:
                    required[t] = []
                required[t].append(file_key)
    return required


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: ripple-verify.py <changelog-path> <date> [--json]",
            file=sys.stderr,
        )
        sys.exit(1)

    changelog_path = sys.argv[1]
    target_date = sys.argv[2]
    json_mode = "--json" in sys.argv

    graph = load_ripple_graph()
    entries, files_touched = parse_changelog_entries(changelog_path, target_date)

    if not entries:
        if json_mode:
            print(json.dumps({"status": "no_entries", "date": target_date}))
        else:
            print(f"No changelog entries for {target_date}. Nothing to verify.")
        sys.exit(0)

    required = get_all_ripple_targets(graph, entries)

    missing = {}
    for target, sources in required.items():
        if target not in files_touched:
            missing[target] = sources

    if json_mode:
        print(
            json.dumps(
                {
                    "date": target_date,
                    "entries": len(entries),
                    "files_touched": sorted(files_touched),
                    "ripple_targets_required": len(required),
                    "missing": missing,
                    "complete": len(missing) == 0,
                },
                indent=2,
            )
        )
    else:
        if missing:
            print(f"INCOMPLETE RIPPLE ({len(missing)} targets not addressed):\n")
            for target, sources in missing.items():
                print(f"  x {target}")
                for s in sources:
                    print(f"      triggered by: {s}")
            print(f"\nRun content-lint.py after addressing these.")
        else:
            print(
                f"Ripple complete. {len(entries)} edits, "
                f"{len(required)} targets, all addressed."
            )

    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
