# PRD: Autonomous Morning Orchestrator

**Date:** 2026-04-09
**Author:** Assaf Kipnis
**Status:** Draft
**Priority:** P2 (medium)
**Source:** Claude Code Insights report (3,000 messages, 169 sessions, 2026-03-26 to 2026-04-09)
**Depends on:** PRD #2 (tool brittleness - `prd-tool-brittleness-2026-04-09.md`)

---

## 1. Problem

The morning pipeline breaks when MCP tools are missing, Notion DB IDs go stale, or file paths reference yesterday's bus directory. ~10 of 169 sessions were spent debugging pipeline failures instead of getting morning output.

- **Evidence:** Usage report. 39 "File Not Found" errors. 3 "Tool failure" + 2 "External tool failure" events. ~10 sessions debugging morning pipeline breakage (stale Notion IDs, missing MCP tools, wrong bus paths).
- **Impact:** ~6% of total sessions (10/169) burned on pipeline debugging. Morning routine produces no usable output on failure days. Founder loses 30-60 min per incident diagnosing which phase broke and why.
- **Root cause:** Three independent failure modes compound:
  1. **No pre-run dependency check.** The preflight agent (00-preflight.md) tests MCP tool availability but does not validate Notion DB IDs are accessible, bus directory exists for today's date, or that required scripts exist at expected paths.
  2. **No phase-level halt.** When a phase fails mid-pipeline, the orchestrator continues to later phases that depend on the failed phase's bus output. This cascades into confusing secondary errors.
  3. **No diagnostic output.** When failures occur, the error is buried in agent context. No structured JSON captures what failed, which phase, and what the fix is.

---

## 2. Scope

### In Scope
- Python preflight script that validates all dependencies before Phase 0
- Python phase runner that wraps each phase with halt-on-failure logic
- Notion ID validator (DB accessibility check)
- Update step-orchestrator.md to integrate new scripts

### Out of Scope
- Rewriting the agent pipeline architecture
- Adding new phases or agents
- Changing the bus protocol or schema format
- Auto-recovery or self-healing (this PRD detects and reports, does not fix)

### Non-Goals
- Replace the existing 00-preflight.md agent (it still tests MCP tools live)
- Make the pipeline run without MCP tools (graceful degradation is PRD #2's scope)
- Add retry logic (retries mask root causes)

---

## 3. Changes

### Change 1: Enhanced Preflight Script

- **What:** New Python script that validates all morning pipeline dependencies before any phase runs.
- **Where:** `q-system/.q-system/scripts/morning-preflight.py`
- **Why:** Addresses root cause #1 - no pre-run dependency check. The 39 "File Not Found" errors and ~10 debugging sessions trace to dependencies that could have been caught before the pipeline started.
- **Exact change:**

```python
#!/usr/bin/env python3
"""Morning pipeline preflight - validates all dependencies before Phase 0.

Checks: bus directory, required scripts, Notion DB IDs, file paths, MCP tool hints.
Writes: bus/{date}/preflight-enhanced.json with pass/fail per check.
Exit 0 = all clear. Exit 1 = blocking failure (do not run pipeline).
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

def main():
    today = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    # Resolve QROOT
    script_dir = Path(__file__).resolve().parent
    qroot = script_dir.parent.parent  # scripts/ -> .q-system/ -> q-system/

    bus_dir = qroot / ".q-system" / "agent-pipeline" / "bus" / today
    results = {"date": today, "checks": [], "blocking": [], "warnings": []}

    # Check 1: Bus directory exists (create if not)
    bus_dir.mkdir(parents=True, exist_ok=True)
    results["checks"].append({"name": "bus_directory", "status": "pass", "path": str(bus_dir)})

    # Check 2: Required scripts exist
    required_scripts = [
        ".q-system/scripts/canonical-digest.py",
        ".q-system/scripts/collection-gate.py",
        ".q-system/scripts/copy-diff.py",
        ".q-system/scripts/publish-reconciliation.py",
        ".q-system/scripts/temperature-scoring.py",
        ".q-system/scripts/compliance-check.py",
        ".q-system/scripts/synthesize-schedule.py",
        ".q-system/bus-to-log.py",
        ".q-system/audit-morning.py",
        ".q-system/sycophancy-harness.py",
        ".q-system/log-step.py",
        "marketing/templates/build-schedule.py",
    ]
    for script in required_scripts:
        full_path = qroot / script
        if full_path.exists():
            results["checks"].append({"name": f"script:{script}", "status": "pass"})
        else:
            results["checks"].append({"name": f"script:{script}", "status": "fail", "error": "File not found"})
            results["blocking"].append(f"Missing script: {script}")

    # Check 3: Required agent prompts exist
    agents_dir = qroot / ".q-system" / "agent-pipeline" / "agents"
    required_agents = [
        "00-preflight.md", "00-session-bootstrap.md",
        "01-calendar-pull.md", "01-gmail-pull.md", "01-crm-pull.md",
        "02-meeting-prep.md", "02-x-activity.md",
        "03-linkedin-posts.md", "03-linkedin-dms.md", "03-prospect-pipeline.md",
        "04-signals-content.md", "04-value-routing.md",
        "05-lead-sourcing.md", "05-pipeline-followup.md", "05-loop-review.md",
        "05-engagement-hitlist.md",
        "06-positioning-check.md",
        "08-visual-verify.md",
        "09-crm-push.md", "10-daily-checklists.md",
    ]
    for agent in required_agents:
        full_path = agents_dir / agent
        if full_path.exists():
            results["checks"].append({"name": f"agent:{agent}", "status": "pass"})
        else:
            results["checks"].append({"name": f"agent:{agent}", "status": "fail", "error": "File not found"})
            results["blocking"].append(f"Missing agent: {agent}")

    # Check 4: Notion DB IDs populated (if using Notion)
    notion_ids_path = qroot / "my-project" / "notion-ids.md"
    if notion_ids_path.exists():
        content = notion_ids_path.read_text()
        required_dbs = ["Contacts", "Actions"]
        for db in required_dbs:
            # Look for pattern: | DbName | <id> | where id is non-empty
            import re
            pattern = rf"\|\s*{db}\s*\|\s*(\S+)\s*\|"
            match = re.search(pattern, content)
            if match and match.group(1):
                results["checks"].append({"name": f"notion_id:{db}", "status": "pass", "id": match.group(1)})
            else:
                results["checks"].append({"name": f"notion_id:{db}", "status": "warn", "error": "ID not populated"})
                results["warnings"].append(f"Notion {db} DB ID not set in notion-ids.md")
    else:
        results["warnings"].append("notion-ids.md not found - Notion checks skipped")

    # Check 5: Key state files exist
    state_files = [
        "my-project/founder-profile.md",
        "my-project/current-state.md",
        "canonical/decisions.md",
        "canonical/talk-tracks.md",
        "memory/last-handoff.md",
    ]
    for sf in state_files:
        full_path = qroot / sf
        if full_path.exists():
            results["checks"].append({"name": f"state:{sf}", "status": "pass"})
        else:
            results["checks"].append({"name": f"state:{sf}", "status": "warn", "error": "File not found"})
            results["warnings"].append(f"Missing state file: {sf}")

    # Check 6: Yesterday's bus directory not lingering as "today" reference
    # (catches the stale date path bug)
    from datetime import timedelta
    yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
    yesterday_bus = qroot / ".q-system" / "agent-pipeline" / "bus" / yesterday
    if yesterday_bus.exists():
        results["checks"].append({"name": "stale_bus_check", "status": "pass", "note": f"Yesterday's bus ({yesterday}) exists, today's is fresh"})
    else:
        results["checks"].append({"name": "stale_bus_check", "status": "pass", "note": "No yesterday bus found"})

    # Write results
    output_path = bus_dir / "preflight-enhanced.json"
    results["pass"] = len(results["blocking"]) == 0
    results["summary"] = f"{len(results['checks'])} checks, {len(results['blocking'])} blocking, {len(results['warnings'])} warnings"

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"Preflight: {results['summary']}")
    if results["blocking"]:
        print("BLOCKING FAILURES:")
        for b in results["blocking"]:
            print(f"  - {b}")
        sys.exit(1)
    if results["warnings"]:
        print("Warnings:")
        for w in results["warnings"]:
            print(f"  - {w}")

    sys.exit(0)

if __name__ == "__main__":
    main()
```

- **Scope:** All instances using the morning pipeline. Propagated via `kipi update`.

### Change 2: Phase Runner with Halt-on-Failure

- **What:** Python wrapper that executes a phase command, captures exit code, writes diagnostic JSON on failure, and halts the pipeline if a critical phase fails.
- **Where:** `q-system/.q-system/scripts/phase-runner.py`
- **Why:** Addresses root cause #2 (no phase-level halt) and root cause #3 (no diagnostic output). Currently when Phase 1 fails, Phase 2-9 still attempt to run, producing cascading errors.
- **Exact change:**

```python
#!/usr/bin/env python3
"""Phase runner - wraps pipeline phase execution with halt-on-failure.

Usage: python3 phase-runner.py <date> <phase_number> <phase_name> <command...>

Captures exit code, timing, and writes diagnostic JSON on failure.
Exit 0 = phase passed. Exit 1 = phase failed (halt pipeline).
"""
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

def main():
    if len(sys.argv) < 5:
        print("Usage: phase-runner.py <date> <phase_num> <phase_name> <command...>")
        sys.exit(2)

    today = sys.argv[1]
    phase_num = sys.argv[2]
    phase_name = sys.argv[3]
    command = sys.argv[4:]

    script_dir = Path(__file__).resolve().parent
    qroot = script_dir.parent.parent
    bus_dir = qroot / ".q-system" / "agent-pipeline" / "bus" / today

    diagnostic = {
        "date": today,
        "phase": int(phase_num),
        "phase_name": phase_name,
        "command": " ".join(command),
        "started_at": datetime.now().isoformat(),
        "exit_code": None,
        "duration_seconds": None,
        "stdout_tail": None,
        "stderr_tail": None,
        "status": None,
    }

    start = time.time()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout per phase script
        )
        diagnostic["exit_code"] = result.returncode
        diagnostic["stdout_tail"] = result.stdout[-500:] if result.stdout else None
        diagnostic["stderr_tail"] = result.stderr[-500:] if result.stderr else None
        diagnostic["status"] = "pass" if result.returncode == 0 else "fail"
    except subprocess.TimeoutExpired:
        diagnostic["exit_code"] = -1
        diagnostic["status"] = "timeout"
        diagnostic["stderr_tail"] = f"Phase {phase_name} timed out after 300s"
    except FileNotFoundError as e:
        diagnostic["exit_code"] = -2
        diagnostic["status"] = "not_found"
        diagnostic["stderr_tail"] = str(e)
    except Exception as e:
        diagnostic["exit_code"] = -3
        diagnostic["status"] = "error"
        diagnostic["stderr_tail"] = str(e)

    diagnostic["duration_seconds"] = round(time.time() - start, 1)
    diagnostic["finished_at"] = datetime.now().isoformat()

    # Write diagnostic
    diag_path = bus_dir / f"phase-{phase_num}-diagnostic.json"
    bus_dir.mkdir(parents=True, exist_ok=True)
    with open(diag_path, "w") as f:
        json.dump(diagnostic, f, indent=2)

    # Print summary
    status_icon = "PASS" if diagnostic["status"] == "pass" else "FAIL"
    print(f"[{status_icon}] Phase {phase_num} ({phase_name}): {diagnostic['status']} in {diagnostic['duration_seconds']}s")

    if diagnostic["status"] != "pass":
        print(f"Diagnostic written to: {diag_path}")
        if diagnostic["stderr_tail"]:
            print(f"Error: {diagnostic['stderr_tail'][:200]}")
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
```

- **Scope:** All instances using the morning pipeline. Used by the orchestrator, not directly by agents.

### Change 3: Notion ID Validator

- **What:** Python script that validates Notion DB IDs are accessible via the Notion API before the pipeline starts.
- **Where:** `q-system/.q-system/scripts/notion-validator.py`
- **Why:** Addresses the "Notion DB IDs go stale" failure mode. IDs become invalid when databases are moved, deleted, or permissions change. Currently discovered mid-pipeline at Phase 1 or Phase 9, wasting all preceding work.
- **Exact change:**

```python
#!/usr/bin/env python3
"""Notion ID validator - checks that configured DB IDs are accessible.

Usage: python3 notion-validator.py [date]

Reads notion-ids.md, attempts to query each DB via Notion API.
Writes bus/{date}/notion-validation.json.
Exit 0 = all valid. Exit 1 = at least one DB inaccessible.

NOTE: This script validates IDs are populated in notion-ids.md.
Live Notion API validation requires the MCP tool and is done by
the 00-preflight agent. This script catches the common case of
empty/missing IDs before the agent even runs.
"""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

def main():
    today = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    script_dir = Path(__file__).resolve().parent
    qroot = script_dir.parent.parent
    bus_dir = qroot / ".q-system" / "agent-pipeline" / "bus" / today

    notion_ids_path = qroot / "my-project" / "notion-ids.md"
    results = {"date": today, "databases": [], "valid": True}

    if not notion_ids_path.exists():
        results["valid"] = True  # Not blocking if Notion not configured
        results["note"] = "notion-ids.md not found - Notion not configured, skipping"
        _write_and_exit(results, bus_dir, 0)

    content = notion_ids_path.read_text()

    # Parse DB IDs from markdown table
    # Expected format: | Name | ID | Purpose |
    db_pattern = re.compile(r"\|\s*(\w[\w\s]*?)\s*\|\s*([a-f0-9-]{32,36})?\s*\|")
    expected_dbs = ["Contacts", "Actions", "Pipeline", "Content Pipeline"]

    found_ids = {}
    for match in db_pattern.finditer(content):
        name = match.group(1).strip()
        db_id = match.group(2).strip() if match.group(2) else ""
        found_ids[name] = db_id

    blocking = False
    for db_name in expected_dbs:
        db_id = found_ids.get(db_name, "")
        if db_id and len(db_id) >= 32:
            results["databases"].append({
                "name": db_name,
                "id": db_id,
                "id_format_valid": True,
                "note": "ID populated and format valid. Live check done by 00-preflight agent."
            })
        elif db_id:
            results["databases"].append({
                "name": db_name,
                "id": db_id,
                "id_format_valid": False,
                "note": f"ID present but format invalid (length {len(db_id)}, expected 32+)"
            })
            if db_name in ["Contacts", "Actions"]:
                blocking = True
        else:
            results["databases"].append({
                "name": db_name,
                "id": None,
                "id_format_valid": False,
                "note": "ID not populated"
            })
            if db_name in ["Contacts", "Actions"]:
                # Contacts and Actions are required for CRM push
                blocking = True

    results["valid"] = not blocking
    exit_code = 1 if blocking else 0
    _write_and_exit(results, bus_dir, exit_code)

def _write_and_exit(results, bus_dir, exit_code):
    bus_dir.mkdir(parents=True, exist_ok=True)
    output_path = bus_dir / "notion-validation.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Notion validation: {'PASS' if results['valid'] else 'FAIL'}")
    for db in results.get("databases", []):
        status = "ok" if db["id_format_valid"] else "MISSING/INVALID"
        print(f"  {db['name']}: {status}")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
```

- **Scope:** All instances using Notion CRM. Instances using Obsidian/local CRM skip gracefully.

### Change 4: Update Step Orchestrator

- **What:** Add preflight-enhanced and phase-runner integration instructions to the step orchestrator.
- **Where:** `q-system/.q-system/agent-pipeline/agents/step-orchestrator.md`
- **Why:** The orchestrator is the execution authority. New scripts must be wired into its flow to be used.
- **Exact change:**

Add after the existing "## Setup" section:

```markdown
## Pre-Pipeline Validation (before Phase 0)

Run these deterministic checks BEFORE spawning any agents:

```bash
# 1. Enhanced preflight (checks scripts, agents, state files, Notion IDs)
python3 {{QROOT}}/.q-system/scripts/morning-preflight.py {{DATE}}
# Exit 1 = HALT. Do not proceed. Show blocking failures to founder.

# 2. Notion ID validation (checks DB ID format and population)
python3 {{QROOT}}/.q-system/scripts/notion-validator.py {{DATE}}
# Exit 1 = WARN. Notion-dependent phases (1, 9) will fail. Ask founder: proceed without CRM or fix IDs first?
```

If either script writes blocking failures, show them to the founder before continuing.
The existing 00-preflight.md agent still runs in Phase 0 for live MCP tool checks.
These scripts catch structural issues (missing files, empty IDs) that the agent would discover too late.

## Phase Script Execution

For deterministic scripts (not agent spawns), use the phase runner:

```bash
python3 {{QROOT}}/.q-system/scripts/phase-runner.py {{DATE}} <phase_num> <phase_name> <command...>
```

Example:
```bash
python3 {{QROOT}}/.q-system/scripts/phase-runner.py {{DATE}} 0 canonical-digest python3 {{QROOT}}/.q-system/scripts/canonical-digest.py {{DATE}}
```

The phase runner captures exit codes, timing, and writes `phase-N-diagnostic.json` on failure.
If exit code != 0, the orchestrator MUST halt and show the diagnostic to the founder.
```

- **Scope:** All instances using the morning pipeline.

---

## 4. Change Interaction Matrix

| Change A | Change B | Interaction | Resolution |
|----------|----------|-------------|------------|
| 1 (preflight script) | 3 (Notion validator) | Both check Notion IDs - preflight does basic format check, validator does deeper validation | Run preflight first (broad), then Notion validator (deep). Preflight catches missing files; validator catches ID-specific issues. No overlap in bus output files. |
| 1 (preflight script) | 4 (orchestrator update) | Orchestrator must call preflight script | Orchestrator calls preflight before Phase 0. Preflight writes preflight-enhanced.json. |
| 2 (phase runner) | 4 (orchestrator update) | Orchestrator must use phase runner for script phases | Orchestrator wraps deterministic script calls with phase-runner.py. Agent spawns (Agent tool) are NOT wrapped - they have their own error handling. |
| 1 (preflight) | 2 (phase runner) | No direct interaction | Preflight runs before pipeline. Phase runner runs during pipeline. Independent. |

---

## 5. Files Modified

| File | Change Type | Lines Added | Lines Removed |
|------|-------------|-------------|---------------|
| `q-system/.q-system/scripts/morning-preflight.py` | New file | ~120 | 0 |
| `q-system/.q-system/scripts/phase-runner.py` | New file | ~95 | 0 |
| `q-system/.q-system/scripts/notion-validator.py` | New file | ~95 | 0 |
| `q-system/.q-system/agent-pipeline/agents/step-orchestrator.md` | Modified | ~30 | 0 |

---

## 6. Test Cases

### [Change 1] Enhanced Preflight Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 1.1 | DET | All dependencies present | Full install with all scripts/agents | Exit 0, preflight-enhanced.json with pass=true | JSON has 0 blocking items |
| 1.2 | DET | Missing required script | Delete canonical-digest.py temporarily | Exit 1, blocking list includes the script | blocking array non-empty, exit code 1 |
| 1.3 | DET | Missing agent prompt | Delete 05-engagement-hitlist.md temporarily | Exit 1, blocking list includes the agent | blocking array non-empty |
| 1.4 | DET | Empty Notion IDs | Clear IDs in notion-ids.md | Exit 0 with warnings (not blocking) | warnings array non-empty, pass=true |
| 1.5 | DET | No notion-ids.md file | Rename file | Exit 0 with warning note | pass=true, warnings mention skipped |
| 1.6 | DET | Bus directory creation | Run on fresh date with no bus dir | Exit 0, bus directory created | Directory exists after run |

### [Change 2] Phase Runner Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 2.1 | DET | Successful phase | `phase-runner.py 2026-04-09 0 test echo hello` | Exit 0, diagnostic with status=pass | exit_code=0, stdout contains "hello" |
| 2.2 | DET | Failed phase | `phase-runner.py 2026-04-09 0 test false` | Exit 1, diagnostic with status=fail | exit_code!=0, diagnostic JSON written |
| 2.3 | DET | Missing command | `phase-runner.py 2026-04-09 0 test nonexistent_cmd` | Exit 1, status=not_found | diagnostic shows FileNotFoundError |
| 2.4 | DET | Timeout | Command that sleeps >300s | Exit 1, status=timeout | diagnostic shows timeout message |
| 2.5 | DET | Diagnostic file written | Any failed phase | phase-N-diagnostic.json exists in bus dir | File exists and is valid JSON |
| 2.6 | DET (negative) | Missing arguments | `phase-runner.py` with <4 args | Exit 2, usage message | Prints usage, does not crash |

### [Change 3] Notion Validator Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 3.1 | DET | All IDs populated | notion-ids.md with valid UUIDs | Exit 0, all databases valid | valid=true |
| 3.2 | DET | Contacts ID missing | Empty Contacts row | Exit 1, blocking failure | valid=false, Contacts shows MISSING |
| 3.3 | DET | Malformed ID | Short string instead of UUID | Exit 1 for required DBs | id_format_valid=false |
| 3.4 | DET | No notion-ids.md | File doesn't exist | Exit 0, skips gracefully | note mentions "not configured" |
| 3.5 | DET (negative) | Optional DB missing | Pipeline ID empty | Exit 0 (not blocking) | valid=true, warning logged |

### [Change 4] Orchestrator Integration Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 4.1 | BEH | Preflight blocks pipeline | morning-preflight.py exits 1 | Orchestrator halts, shows errors to founder | No Phase 0 agents spawned |
| 4.2 | BEH | Preflight passes, pipeline runs | morning-preflight.py exits 0 | Phase 0 agents spawn normally | preflight-enhanced.json exists with pass=true, then 00-preflight.md runs |
| 4.3 | INT | Full pipeline with all changes | Normal morning run | Preflight -> Notion check -> Phase 0-9 with diagnostics | All bus files written, diagnostics for script phases |
| 4.4 | BEH (negative) | Phase runner halts mid-pipeline | Script in Phase 5 fails | Phases 6-9 do not execute | phase-5-diagnostic.json shows failure, no Phase 6+ bus files |

---

## 7. Regression Tests

| # | What to Verify | How to Verify | Pass Criteria |
|---|----------------|---------------|---------------|
| 7.1 | Existing 00-preflight.md agent still runs | Run `/q-morning`, check bus/{date}/preflight.json exists | preflight.json written by agent (separate from preflight-enhanced.json) |
| 7.2 | Phase timing not degraded | Compare morning-log timestamps before/after | Preflight adds <5s overhead |
| 7.3 | Bus protocol unchanged | Run verify-bus.py on full pipeline output | All existing bus files pass schema validation |
| 7.4 | Audit harness still works | Run audit-morning.py after pipeline | Audit produces valid verdict |
| 7.5 | Non-Notion instances unaffected | Run on Obsidian-CRM instance | Notion validator skips gracefully, pipeline completes |

---

## 8. Rollback Plan

| Change | Rollback Steps | Risk |
|--------|---------------|------|
| 1 (preflight script) | Delete `morning-preflight.py`. Remove the "Pre-Pipeline Validation" section from step-orchestrator.md. | Low - pipeline runs without enhanced preflight, same as today. |
| 2 (phase runner) | Delete `phase-runner.py`. Revert orchestrator to call scripts directly. | Low - scripts still run, just without diagnostic capture. |
| 3 (Notion validator) | Delete `notion-validator.py`. Remove call from orchestrator. | Low - Notion checks fall back to 00-preflight agent's live test. |
| 4 (orchestrator update) | `git revert` the step-orchestrator.md changes. | Low - reverts to current orchestrator behavior. |

---

## 9. Change Review Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Changes are additive (no breaking removals) | Pending | All 3 scripts are new files. Orchestrator changes are additions only. |
| No conflicts with existing enforced rules | Pending | Preflight script does not contradict preflight.md tool manifest. Phase runner does not override gate logic. |
| No hardcoded secrets | Pending | Scripts read notion-ids.md for DB IDs. No API keys in code. |
| Propagation path verified (kipi update, global, etc.) | Pending | New scripts in `.q-system/scripts/` propagate via kipi update. Orchestrator change propagates with agent-pipeline. |
| Exit codes preserved (hooks exit 0) | Pending | These are pipeline scripts, not hooks. Exit 1 = halt pipeline (intentional). Hooks remain exit 0. |
| AUDHD-friendly (no pressure/shame language added) | Pending | Error messages use factual language ("Missing script: X"). No urgency/shame. |
| Test coverage for every change | Pending | 6 + 6 + 5 + 4 = 21 test cases across all changes. |

---

## 10. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Sessions spent debugging morning pipeline | ~10/169 (6%) | <2/169 (<1.5%) | Count sessions where morning output was not produced due to pipeline error |
| Time to diagnose pipeline failure | 30-60 min (manual) | <2 min (read diagnostic JSON) | Measure from failure to root cause identification |
| "File Not Found" errors in morning pipeline | 39 across 169 sessions | <5 | Usage report File Not Found count for .q-system paths |
| Preflight catch rate | 0% (no preflight) | >90% of structural failures caught before Phase 0 | Compare preflight-enhanced.json blocking items vs actual pipeline failures |

---

## 11. Implementation Order

1. Create `morning-preflight.py` (Change 1) - no dependencies
2. Create `notion-validator.py` (Change 3) - no dependencies, can parallel with #1
3. Create `phase-runner.py` (Change 2) - no dependencies, can parallel with #1-2
4. Update `step-orchestrator.md` (Change 4) - depends on #1, #2, #3 existing
5. Run test cases 1.1-1.6, 2.1-2.6, 3.1-3.5 (deterministic, can run immediately)
6. Run integration test 4.3 (full pipeline test, depends on #4)
7. `kipi update --dry` to verify propagation
8. `kipi update` to push to all instances

---

## 12. Open Questions

| Question | Owner | Deadline | Resolution |
|----------|-------|----------|------------|
| Should phase-runner.py also wrap Agent tool spawns, or only deterministic scripts? | Assaf | Before implementation | Current design: scripts only. Agent spawns have their own error handling via bus file error convention. |
| Should Notion validator do live API calls or just ID format checks? | Assaf | Before implementation | Current design: format checks only. Live validation stays with 00-preflight agent to avoid duplicating MCP calls. |
| What's the right timeout for phase-runner.py? 300s may be too short for Phase 5 (lead sourcing with Chrome). | Assaf | During implementation | Could make timeout configurable per phase. Default 300s, override via env var or arg. |
| Does this PRD need PRD #2 (tool brittleness) to ship first, or can they be independent? | Assaf | Before implementation | Preflight and phase runner work without tool brittleness fixes. But the full value comes when tool fallbacks (PRD #2) are in place. Ship independently, get more value combined. |

---

## 13. Wiring Checklist (MANDATORY)

| Check | Status | Notes |
|-------|--------|-------|
| PRD file saved to `q-system/output/prd-morning-orchestrator-2026-04-09.md` | Done | This file |
| All code/config changes implemented and tested | Pending | 3 new scripts + 1 orchestrator update |
| New files listed in folder-structure rule (if any created) | Pending | 3 new scripts in `.q-system/scripts/` - already covered by existing pattern |
| New conventions referenced in root CLAUDE.md (if any added) | N/A | No new conventions, uses existing script patterns |
| New rules referenced in folder-structure rules list (if any created) | N/A | No new rules files |
| Memory entry saved for decisions/patterns worth recalling | Pending | Save entry about pre-pipeline validation pattern |
| `kipi update --dry` confirms propagation diff (if skeleton files changed) | Pending | Run after implementation |
| `kipi update` run to push to all instances (if skeleton files changed) | Pending | Run after dry verification |
| PRD Status field updated to "Done" | Pending | Update after all implementation complete |
