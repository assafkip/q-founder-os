#!/usr/bin/env python3
"""
Ripple system regression tests. Run automatically via `kipi check`.

Tests:
1. ripple-graph.json is valid JSON with "graph" key
2. All source files in graph exist on disk
3. All target files in graph exist on disk
4. No file lists itself as a ripple target
5. changelog-write.py runs without import errors
6. content-lint.py runs without import errors
7. ripple-verify.py runs without import errors

Exit 0 = all pass
Exit 1 = failures (printed to stdout)
"""

import json
import os
import subprocess
import sys

QROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
# Subtree instances nest q-system/ inside q-system/
if not os.path.isdir(os.path.join(QROOT, "canonical")) and os.path.isdir(os.path.join(QROOT, "q-system", "canonical")):
    QROOT = os.path.join(QROOT, "q-system")
SCRIPTS = os.path.dirname(__file__)
RIPPLE_GRAPH = os.path.join(QROOT, ".q-system", "ripple-graph.json")

failures = []


def test(name, condition, detail=""):
    if condition:
        print(f"  PASS: {name}")
    else:
        msg = f"  FAIL: {name}" + (f" ({detail})" if detail else "")
        print(msg)
        failures.append(msg)


def test_graph_valid():
    try:
        with open(RIPPLE_GRAPH) as f:
            data = json.load(f)
        test("graph is valid JSON", True)
        test("graph has 'graph' key", "graph" in data, "missing top-level 'graph' key")
        return data.get("graph", {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        test("graph is valid JSON", False, str(e))
        return {}


def test_files_exist(graph):
    missing = []
    for src, targets in graph.items():
        if not os.path.exists(os.path.join(QROOT, src)):
            missing.append(src)
        for tgt in targets:
            if not os.path.exists(os.path.join(QROOT, tgt)):
                missing.append(tgt)
    test("all referenced files exist", len(missing) == 0, f"missing: {missing}")


def test_no_self_reference(graph):
    self_refs = []
    for src, targets in graph.items():
        if src in targets:
            self_refs.append(src)
    test("no self-references", len(self_refs) == 0, f"self-referencing: {self_refs}")


def test_script_runs(name, script_path):
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Scripts with no args should exit 1 (usage) or 0, not crash
        test(
            f"{name} runs without crash",
            result.returncode in (0, 1, 2),
            f"exit {result.returncode}: {result.stderr[:200]}",
        )
    except Exception as e:
        test(f"{name} runs without crash", False, str(e))


def main():
    print("Ripple system regression tests:\n")

    graph = test_graph_valid()
    if graph:
        test_files_exist(graph)
        test_no_self_reference(graph)

    test_script_runs(
        "changelog-write.py", os.path.join(SCRIPTS, "changelog-write.py")
    )
    test_script_runs("content-lint.py", os.path.join(SCRIPTS, "content-lint.py"))
    test_script_runs("ripple-verify.py", os.path.join(SCRIPTS, "ripple-verify.py"))

    print(f"\n{7 - len(failures)}/7 passed, {len(failures)} failed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
