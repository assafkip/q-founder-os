# PRD: Self-Healing Pipeline with Test Gates

**Date:** 2026-04-09
**Author:** Assaf Kipnis
**Status:** Draft
**Priority:** P2 (medium)

---

## 1. Problem

Value-drop and KTLYST product pipelines (extraction, imports, dedup) break during normal operation. When they break, Assaf spends multiple sessions manually iterating: run pipeline, read stderr, guess at fix, re-run, repeat. Claude can do this loop autonomously if it has test assertions and a self-healing agent pattern, but that infrastructure doesn't exist yet.

- **Evidence:** Usage report horizon section: "Claude Code can autonomously run a pipeline, catch failures, diagnose root causes, and re-run against test assertions in a loop." Pipeline debugging sessions span multiple days. Manual iteration is the norm for every pipeline failure.
- **Impact:** Assaf (founder). Happens on every pipeline break -- estimated 2-5 incidents per week based on current pipeline complexity. Each incident burns 1-3 sessions of manual debugging. Total cost: 5-15 sessions per week on pipeline rescue work.
- **Root cause:** No test assertion files defining expected pipeline stage outputs. No self-healing agent pattern. No runner that captures stderr, diagnoses, patches, and re-runs. Claude sees each failure fresh with no prior test context.

## 2. Scope

### In Scope
- Test assertion schema for pipeline stages (JSON Schema format)
- Self-healing agent prompt template (how the agent should loop: run -> capture -> diagnose -> patch -> re-run)
- Pipeline test gate runner script that executes the pipeline, validates output against assertions, captures stderr
- CLAUDE.md section documenting the self-healing pattern
- The pattern itself (cross-instance applicable)

### Out of Scope
- Specific test assertions for value-drop or KTLYST pipelines (those live in the product instance at `~/Desktop/ktlyst-hub/product/`, separate PRD per pipeline)
- Pipeline code itself (owned by product instance per cluster rules)
- Auto-applying patches without human review for high-risk changes (human approval required for first N runs)
- Integration with Linear/GitHub for automated issue creation

### Non-Goals
- Zero manual pipeline intervention (edge cases will always need humans)
- Self-healing for pipelines outside the product instance
- Replacing existing audit harness or bus validator (those are post-hoc, this is in-loop)

## 3. Changes

### Change 1: Pipeline Test Gate Schema

- **What:** JSON Schema defining the structure of a test assertion file that describes expected pipeline stage outputs
- **Where:** `/Users/assafkip/Desktop/kipi-system/q-system/.q-system/agent-pipeline/schemas/pipeline-test-gate.schema.json`
- **Why:** Without a schema, every pipeline will invent its own assertion format. Standard schema enables the runner (Change 3) and self-healing agent (Change 2) to work across pipelines.
- **Exact change:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "pipeline-test-gate.schema.json",
  "title": "Pipeline Test Gate",
  "description": "Defines expected outputs and assertions for a pipeline stage. Consumed by pipeline-test-gate.py runner and self-healing agent template.",
  "type": "object",
  "required": ["pipeline_id", "stage", "command", "assertions"],
  "properties": {
    "pipeline_id": {
      "type": "string",
      "description": "Stable identifier, e.g. value-drop-extraction"
    },
    "stage": {
      "type": "string",
      "description": "Stage name within the pipeline, e.g. extract, dedup, import"
    },
    "command": {
      "type": "string",
      "description": "Shell command to execute this stage"
    },
    "working_dir": {
      "type": "string",
      "description": "Directory to run the command in (absolute path)"
    },
    "timeout_seconds": {
      "type": "integer",
      "minimum": 1,
      "default": 300
    },
    "assertions": {
      "type": "array",
      "description": "Conditions that must hold after the command runs",
      "items": {
        "type": "object",
        "required": ["type", "target"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["file_exists", "file_line_count", "json_key", "json_array_length", "stderr_absent", "exit_code"]
          },
          "target": {"type": "string", "description": "File path, JSON key path, or pattern depending on type"},
          "expected": {"description": "Expected value (number, string, bool)"},
          "operator": {
            "type": "string",
            "enum": ["equals", "gte", "lte", "contains", "not_contains"],
            "default": "equals"
          }
        }
      }
    },
    "max_heal_attempts": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10,
      "default": 3,
      "description": "How many times the self-healing agent can iterate before giving up"
    },
    "heal_approval_required": {
      "type": "boolean",
      "default": true,
      "description": "If true, pause for human approval before each patch attempt"
    }
  }
}
```

- **Scope:** Skeleton (propagates to all instances via `kipi update`). Product instance writes its own test gate files consuming this schema.

### Change 2: Self-Healing Agent Template

- **What:** Agent prompt template that defines the run-diagnose-patch-rerun loop, including token discipline rules and stop conditions
- **Where:** `/Users/assafkip/Desktop/kipi-system/q-system/.q-system/agent-pipeline/templates/self-healing-agent.md`
- **Why:** Without a standard prompt, every self-healing invocation will be ad-hoc. Template encodes the loop structure, stop conditions, and escalation rules.
- **Exact change:**

```markdown
# Self-Healing Pipeline Agent

You are a self-healing pipeline agent. Your job is to run a pipeline stage, check assertions, diagnose failures, propose minimal patches, and re-run until assertions pass or max attempts reached.

## Inputs

- `test_gate_file`: Path to a test gate JSON file conforming to `pipeline-test-gate.schema.json`
- `attempt_number`: Current attempt (starts at 1)
- `max_attempts`: From test gate file (default 3)

## Loop (repeat until pass or max_attempts exhausted)

1. **Run.** Execute the test gate's `command` in `working_dir`. Capture stdout, stderr, exit code. Enforce `timeout_seconds`.
2. **Assert.** Run `pipeline-test-gate.py --check <test_gate_file>` to validate assertions. If all pass: STOP and report success.
3. **Diagnose.** If assertions fail, analyze stderr and output. Identify the smallest plausible root cause. Do NOT guess at multiple causes.
4. **Approve (if required).** If `heal_approval_required: true`, output the proposed patch and wait for human "approve" or "reject." If rejected, STOP and report.
5. **Patch.** Apply the minimal fix. One change per attempt. Log the patch to `q-system/output/heal-log-<pipeline_id>-<date>.json`.
6. **Increment `attempt_number`.** If `attempt_number > max_attempts`, STOP and escalate.

## Stop Conditions (hard)

- All assertions pass -> report success
- `attempt_number > max_attempts` -> report exhausted, list every attempt + patch
- Same stderr signature appears 2+ times -> report infinite loop, stop
- Patch requires modifying files outside the pipeline's directory -> escalate, do not auto-patch
- Any file-too-large or file-not-found error during diagnosis -> escalate

## Token Discipline (MANDATORY)

- Before each attempt, estimate token cost. If cumulative cost > 100K tokens, escalate to human.
- Do NOT spawn sub-agents. Use Grep/Read/Edit directly.
- Do NOT re-read the same error log twice. Cache the diagnosis.

## Output Format

Every attempt logs:
```json
{
  "attempt": 1,
  "timestamp": "2026-04-09T14:30:00Z",
  "stderr_signature": "first 200 chars of stderr",
  "diagnosis": "one-sentence root cause",
  "patch": "file + line + change summary",
  "result": "pass|fail|escalate"
}
```

Final output: Success/Exhausted/Escalated + full attempt history.
```

- **Scope:** Skeleton (propagates to all instances via `kipi update`). Product instance invokes this template when running pipeline fixes.

### Change 3: Pipeline Test Gate Runner Script

- **What:** Python script that loads a test gate JSON file, runs the command, validates assertions against actual output, returns structured pass/fail
- **Where:** `/Users/assafkip/Desktop/kipi-system/q-system/.q-system/scripts/pipeline-test-gate.py`
- **Why:** Deterministic runner (per project convention: "Always prefer deterministic, script-based solutions"). Removes LLM ambiguity from the assertion check step.
- **Exact change:**

```python
#!/usr/bin/env python3
"""
Pipeline Test Gate Runner.

Loads a test gate JSON file (conforming to pipeline-test-gate.schema.json),
runs the specified command, and validates assertions against the output.

Usage:
  python3 pipeline-test-gate.py --run <test_gate.json>      # Run command + check
  python3 pipeline-test-gate.py --check <test_gate.json>    # Check only (assumes command already ran)

Exit codes:
  0 = all assertions pass
  1 = one or more assertions failed
  2 = command failed (non-zero exit or timeout)
  3 = schema validation error or file not found
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def load_test_gate(path):
    if not os.path.exists(path):
        print(f"ERROR: test gate file not found: {path}", file=sys.stderr)
        sys.exit(3)
    with open(path) as f:
        return json.load(f)


def run_command(gate):
    cmd = gate["command"]
    cwd = gate.get("working_dir", os.getcwd())
    timeout = gate.get("timeout_seconds", 300)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": f"TIMEOUT after {timeout}s"}


def check_assertion(assertion, run_result):
    atype = assertion["type"]
    target = assertion["target"]
    expected = assertion.get("expected")
    operator = assertion.get("operator", "equals")

    if atype == "file_exists":
        actual = os.path.exists(target)
        return actual == (expected if expected is not None else True), f"file_exists({target})={actual}"

    if atype == "file_line_count":
        if not os.path.exists(target):
            return False, f"file missing: {target}"
        with open(target) as f:
            actual = sum(1 for _ in f)
        return compare(actual, expected, operator), f"line_count({target})={actual} {operator} {expected}"

    if atype == "json_key":
        if not os.path.exists(target.split("::")[0]):
            return False, f"file missing: {target}"
        path, key = target.split("::", 1)
        with open(path) as f:
            data = json.load(f)
        actual = data
        for part in key.split("."):
            actual = actual.get(part) if isinstance(actual, dict) else None
        return compare(actual, expected, operator), f"json_key({target})={actual}"

    if atype == "json_array_length":
        path, key = target.split("::", 1)
        with open(path) as f:
            data = json.load(f)
        arr = data
        for part in key.split("."):
            arr = arr.get(part) if isinstance(arr, dict) else arr
        actual = len(arr) if isinstance(arr, list) else 0
        return compare(actual, expected, operator), f"array_length({target})={actual}"

    if atype == "stderr_absent":
        actual = target not in run_result["stderr"]
        return actual, f"stderr_absent({target})={actual}"

    if atype == "exit_code":
        return compare(run_result["exit_code"], expected, operator), f"exit_code={run_result['exit_code']}"

    return False, f"unknown assertion type: {atype}"


def compare(actual, expected, operator):
    if operator == "equals":
        return actual == expected
    if operator == "gte":
        return actual >= expected
    if operator == "lte":
        return actual <= expected
    if operator == "contains":
        return expected in (actual or "")
    if operator == "not_contains":
        return expected not in (actual or "")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", help="Run command then check assertions")
    parser.add_argument("--check", help="Check assertions only (command already ran)")
    args = parser.parse_args()

    gate_path = args.run or args.check
    if not gate_path:
        print("ERROR: --run or --check required", file=sys.stderr)
        sys.exit(3)

    gate = load_test_gate(gate_path)

    if args.run:
        run_result = run_command(gate)
        if run_result["exit_code"] != 0 and "exit_code" not in [a["type"] for a in gate["assertions"]]:
            print(json.dumps({"status": "command_failed", "run": run_result}, indent=2))
            sys.exit(2)
    else:
        run_result = {"exit_code": 0, "stdout": "", "stderr": ""}

    results = []
    all_pass = True
    for assertion in gate["assertions"]:
        passed, detail = check_assertion(assertion, run_result)
        results.append({"assertion": assertion, "passed": passed, "detail": detail})
        if not passed:
            all_pass = False

    output = {
        "pipeline_id": gate["pipeline_id"],
        "stage": gate["stage"],
        "status": "pass" if all_pass else "fail",
        "results": results,
    }
    print(json.dumps(output, indent=2))
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
```

- **Scope:** Skeleton (propagates to all instances via `kipi update`). Any pipeline in any instance can use this runner.

### Change 4: Self-Healing Pattern Section in CLAUDE.md

- **What:** Add a "Self-Healing Pipeline Pattern" section documenting when and how to invoke the pattern
- **Where:** `/Users/assafkip/Desktop/kipi-system/CLAUDE.md` (after "Token Discipline" section)
- **Why:** Without documentation, Claude won't know the pattern exists. This is discoverability, not enforcement.
- **Exact change:**

```markdown
## Self-Healing Pipeline Pattern

When a pipeline breaks (extraction, import, dedup, build), use the self-healing pattern instead of manual iteration.

**Prerequisites:**
- A test gate JSON file exists for the pipeline stage (schema: `q-system/.q-system/agent-pipeline/schemas/pipeline-test-gate.schema.json`)
- Test gate defines command, assertions, and max_heal_attempts

**Invocation:**
1. Load the self-healing agent template: `q-system/.q-system/agent-pipeline/templates/self-healing-agent.md`
2. Pass the test gate file path as input
3. Agent loops: run -> check via `pipeline-test-gate.py` -> diagnose -> patch -> re-run
4. Agent stops on success, max attempts, or escalation condition

**When NOT to use:**
- First-time pipeline setup (no test gate yet)
- Changes that require refactoring (pattern is for drift fixes, not redesign)
- Pipelines outside this instance (cross-instance work follows cluster rules)

**Cross-instance note:** Product pipelines live in `~/Desktop/ktlyst-hub/product/`. The skeleton owns the pattern (schema, template, runner). The product instance owns the test gate files and invokes the pattern.
```

- **Scope:** Skeleton (propagates to all instances via `kipi update`)

## 4. Change Interaction Matrix

| Change A | Change B | Interaction | Resolution |
|----------|----------|-------------|------------|
| Change 1 (schema) | Change 2 (agent template) | Template references schema for input validation | Template must cite schema path. Schema is authoritative. |
| Change 1 (schema) | Change 3 (runner) | Runner consumes files conforming to schema | Runner does not re-validate schema (trusts input); schema enforcement is separate concern |
| Change 2 (template) | Change 3 (runner) | Template tells agent to invoke runner for assertion checks | Template must reference exact runner path. Runner exit codes must match template stop conditions. |
| Change 4 (CLAUDE.md) | Changes 1-3 | Documentation points to all three artifacts | CLAUDE.md paths must match actual file paths in Changes 1-3 |
| Change 3 (runner) | Existing audit-morning.py | Both are deterministic validators but serve different stages | No conflict. audit-morning.py is post-routine. pipeline-test-gate.py is in-loop. |
| Change 2 (template) | Existing token-discipline rule | Template enforces token rules mid-loop | Template must not spawn sub-agents (per token discipline). Already encoded in template. |

## 5. Files Modified

| File | Change Type | Lines Added | Lines Removed |
|------|------------|-------------|---------------|
| `q-system/.q-system/agent-pipeline/schemas/pipeline-test-gate.schema.json` | Add | +65 | -0 |
| `q-system/.q-system/agent-pipeline/templates/self-healing-agent.md` | Add | +60 | -0 |
| `q-system/.q-system/scripts/pipeline-test-gate.py` | Add | +155 | -0 |
| `CLAUDE.md` | Edit | +22 | -0 |

## 6. Test Cases

### Change 1 Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 1.1 | DET | Schema is valid JSON Schema | `python3 -c "import json, jsonschema; jsonschema.Draft7Validator.check_schema(json.load(open('pipeline-test-gate.schema.json')))"` | No error | Exit 0 |
| 1.2 | DET | Example test gate file validates against schema | Create sample gate file, validate | Validation passes | Exit 0 |
| 1.3 | DET | Missing required field is rejected | Create gate without `pipeline_id` | Validation fails | Validation error raised |

### Change 2 Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 2.1 | BEH | Agent stops at max_heal_attempts | Test gate with max_heal_attempts=2 and unfixable failure | Agent stops after 2 attempts and escalates | Log shows 2 attempts, then escalation |
| 2.2 | BEH | Agent stops on repeated stderr signature | Same error twice in a row | Agent detects loop and stops | Log shows "infinite loop detected" |
| 2.3 | BEH | Agent does not spawn sub-agents | Any pipeline run | No Agent tool calls in trace | Token guard logs show 0 subagents |

### Change 3 Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 3.1 | DET | Run command with all assertions passing | Test gate with `command: "echo hello > /tmp/test.txt"` and `file_exists: /tmp/test.txt` | status: pass | Exit 0 |
| 3.2 | DET | Run command with failing assertion | Same gate but assertion `file_exists: /tmp/missing.txt` | status: fail | Exit 1 |
| 3.3 | DET | Command times out | Test gate with `command: "sleep 5"` and `timeout_seconds: 1` | command_failed with TIMEOUT | Exit 2 |
| 3.4 | DET | Missing test gate file | `--run /tmp/nonexistent.json` | file not found error | Exit 3 |
| 3.5 | DET | json_key assertion | Gate with `target: "/tmp/out.json::data.count"`, `expected: 5`, `operator: gte` | Reads file, extracts key, compares | Returns correct pass/fail |
| 3.6 | DET | Negative: command succeeds but assertion specifies failure | Command writes wrong count, assertion requires exact match | status: fail | Exit 1 |

### Change 4 Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 4.1 | BEH | Claude discovers pattern from CLAUDE.md | Ask Claude to fix a broken pipeline with an existing test gate file | Claude invokes self-healing agent template instead of manual iteration | Observed in 3 out of 3 pipeline failures within 2 weeks |

## 7. Regression Tests

| # | What to Verify | How to Verify | Pass Criteria |
|---|----------------|---------------|---------------|
| R-1 | Existing schemas still load | `for f in q-system/.q-system/agent-pipeline/schemas/*.json; do python3 -c "import json; json.load(open('$f'))"; done` | No errors |
| R-2 | Existing audit-morning.py still works | `python3 q-system/.q-system/audit-morning.py` against yesterday's log | Exit 0 |
| R-3 | Token guard still enforces subagent limits | Attempt to spawn 26 agents in one message | Blocked at 25 |
| R-4 | Existing templates directory structure unchanged | `ls q-system/.q-system/agent-pipeline/templates/` shows content/, debrief/, deck/, outreach/ plus new self-healing-agent.md | All 4 subdirs present |

## 8. Rollback Plan

| Change | Rollback Steps | Risk |
|--------|---------------|------|
| Change 1 (schema) | Delete `pipeline-test-gate.schema.json` | None. No other file references it yet. |
| Change 2 (template) | Delete `self-healing-agent.md` | None. Standalone template. |
| Change 3 (runner) | Delete `pipeline-test-gate.py` | None. Standalone script. |
| Change 4 (CLAUDE.md) | Remove "Self-Healing Pipeline Pattern" section | None. Behavioral guidance only. |

All four changes are additive and isolated. Rollback is deletion.

## 9. Change Review Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Changes are additive (no breaking removals) | PASS | All new files + additive CLAUDE.md section |
| No conflicts with existing enforced rules | PASS | Template enforces token discipline (no sub-agents, no re-reads) |
| No hardcoded secrets | PASS | No secrets in any change |
| Propagation path verified (kipi update, global, etc.) | PENDING | All four files are in skeleton paths that propagate |
| Exit codes preserved (hooks exit 0) | N/A | No hook changes. Runner exit codes are intentional (0/1/2/3). |
| AUDHD-friendly (no pressure/shame language added) | PASS | Template uses factual language; escalation is informational not shameful |
| Test coverage for every change | PASS | DET tests for schema, runner. BEH tests for template and CLAUDE.md. |

## 10. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Manual pipeline debug sessions per week | 5-15 | <3 | Count sessions tagged "pipeline-debug" in session effort logs |
| Time to pipeline green after break | Hours to days | <30 minutes for drift fixes | Measure wall-clock from break to first green run |
| Self-healing success rate (first 10 invocations) | N/A | >60% | Count attempts where agent reached success without escalation |
| Escalation rate | N/A | <40% | Count escalations per total invocations |

## 11. Implementation Order

1. **Change 1 (schema)** -- no dependencies. Write and validate schema file.
2. **Change 3 (runner)** -- depends on Change 1 (consumes schema format). Write runner and test against sample gate files.
3. **Change 2 (template)** -- depends on Changes 1 and 3 (references both). Write template referencing exact paths.
4. **Change 4 (CLAUDE.md)** -- depends on Changes 1-3 (documents them). Add section with correct paths.
5. **Run DET tests** (1.1-1.3, 3.1-3.6) against schema and runner.
6. **Run `kipi update --dry`** to verify propagation.
7. **First real test**: pick one broken pipeline in product instance, write a test gate file for it, run self-healing agent. Capture result. Adjust template based on learnings.
8. **Run `kipi update`** to push to all instances once first real test succeeds.

## 12. Open Questions

| Question | Owner | Deadline | Resolution |
|----------|-------|----------|------------|
| Should the first 5 real invocations require human approval on every patch (not just `heal_approval_required` flag)? | Assaf | 2026-04-16 | Start with `heal_approval_required: true` as default. Flip after 5 clean runs. |
| Where do heal logs live? `q-system/output/` or a new `q-system/output/heal-logs/` subdir? | Assaf | 2026-04-16 | Start with `q-system/output/heal-log-<id>-<date>.json`. Move to subdir if volume justifies. |
| Does the product instance need its own copy of these files or can it reference skeleton via `--add-dir`? | Assaf | 2026-04-16 | Skeleton files propagate via `kipi update`, so product instance gets its own copy. |
| How do we avoid the self-healing agent patching canonical files? | Assaf | 2026-04-16 | Template stop condition: "Patch requires modifying files outside the pipeline's directory -> escalate." Already encoded. |

## 13. Wiring Checklist (MANDATORY)

| Check | Status | Notes |
|-------|--------|-------|
| PRD file saved to `q-system/output/prd-self-healing-pipeline-2026-04-09.md` | DONE | This file |
| All code/config changes implemented and tested | PENDING | |
| New files listed in folder-structure rule (if any created) | PENDING | Add `pipeline-test-gate.schema.json`, `self-healing-agent.md`, `pipeline-test-gate.py` to folder-structure.md |
| New conventions referenced in root CLAUDE.md (if any added) | PENDING | "Self-Healing Pipeline Pattern" section is the convention |
| New rules referenced in folder-structure rules list (if any created) | N/A | No new rules files created |
| Memory entry saved for decisions/patterns worth recalling | PENDING | Save: "Self-healing pipeline pattern (test gate + agent loop + deterministic runner)" |
| `kipi update --dry` confirms propagation diff (if skeleton files changed) | PENDING | |
| `kipi update` run to push to all instances (if skeleton files changed) | PENDING | |
| PRD Status field updated to "Done" | PENDING | |
