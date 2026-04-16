# PRD: File-Too-Large Error Reduction

**Date:** 2026-04-09
**Author:** Assaf Kipnis
**Status:** Draft
**Priority:** P2 (medium)

---

## 1. Problem

Claude reads large files without offset/limit parameters, triggering 27 file-too-large errors over 15 days (3,000 messages, 169 sessions). Each error wastes a tool call, burns tokens on the truncated/failed response, and forces a retry with offset/limit -- doubling the cost of reading that file.

- **Evidence:** Usage report: 27 file-too-large events across 15 days. Known offenders: `relationships.md`, `morning-log-*.json`, bus JSON files, `marketing-state.md`. Separately, 39 file-not-found errors suggest broader file-access friction.
- **Impact:** Claude (all sessions). ~54 wasted tool calls (error + retry). Estimated 2-3 wasted tool calls per incident. Compounds during morning routine where bus files and logs are read repeatedly.
- **Root cause:** No guidance in CLAUDE.md about which files are large. No PreToolUse guard that catches unbounded reads before they execute. Claude defaults to reading whole files when it doesn't know the file size.

## 2. Scope

### In Scope
- Add "Large File Handling" guidance section to root CLAUDE.md
- Create a PreToolUse hook script that warns when reading known large files without offset/limit
- Wire the hook into settings.json

### Out of Scope
- Fixing the 39 file-not-found errors (separate root cause, separate PRD)
- Auto-splitting large files or imposing line budgets on canonical files (md-hygiene rule already handles pruning)
- Changing the Read tool's default behavior (outside our control)

### Non-Goals
- Preventing all file-too-large errors (some will come from new/unexpected large files)
- Making Claude always use offset/limit (small files should be read whole for efficiency)

## 3. Changes

### Change 1: Large File Handling Section in CLAUDE.md

- **What:** Add a "Large File Handling" section to root CLAUDE.md documenting known large files and the offset/limit pattern
- **Where:** `/Users/assafkip/Desktop/kipi-system/CLAUDE.md` (after "Token Discipline" section)
- **Why:** 27 file-too-large errors because Claude has no guidance on which files exceed the Read tool's default limit. Documentation is the cheapest fix for a behavioral problem.
- **Exact change:**

```markdown
## Large File Handling

These files regularly exceed the Read tool's default line limit. Always use `offset` and `limit` parameters when reading them.

| File Pattern | Typical Size | How to Read |
|---|---|---|
| `q-system/my-project/relationships.md` | 500-2000 lines | Read first 100 lines for index, then target specific sections |
| `q-system/output/morning-log-*.json` | 500-3000 lines | Read last 200 lines for most recent entries |
| `q-system/.q-system/agent-pipeline/bus/*/*.json` | 200-1000 lines | Read first 50 lines for metadata, then targeted sections |
| `q-system/memory/marketing-state.md` | 300-800 lines | Read first 100 lines for current state summary |
| `q-system/canonical/engagement-playbook.md` | 300-600 lines | Read specific sections by offset |

**Pattern:** When unsure about file size, start with `offset: 0, limit: 100` to scan structure, then read targeted ranges.
```

- **Scope:** Skeleton (propagates to all instances via `kipi update`)

### Change 2: PreToolUse Large File Guard Hook

- **What:** A shell script that checks if a Read tool call targets a known large file without offset/limit and warns Claude before the read executes
- **Where:** `/Users/assafkip/Desktop/kipi-system/q-system/hooks/large-file-guard.sh`
- **Why:** Documentation alone (Change 1) is behavioral -- Claude may ignore it. A PreToolUse hook provides deterministic enforcement. This follows the project convention: "Never fix LLM-instruction failures with better instructions alone."
- **Exact change:**

```bash
#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook: warns when reading known large files without offset/limit.
# Reads tool_input from stdin (JSON with tool_name and tool_input fields).
# Exit 0 = allow (with optional warning via stdout JSON).
# Exit 2 = block (stderr message goes to Claude as feedback).

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")

# Only check Read tool calls
if [ "$TOOL_NAME" != "Read" ]; then
  exit 0
fi

FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")
HAS_LIMIT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if 'limit' in d.get('tool_input',{}) else 'no')" 2>/dev/null || echo "no")

# Skip if limit is already provided
if [ "$HAS_LIMIT" = "yes" ]; then
  exit 0
fi

# Known large file patterns
LARGE_PATTERNS=(
  "relationships.md"
  "morning-log-"
  "marketing-state.md"
  "engagement-playbook.md"
  "/bus/"
)

MATCHED=""
for pattern in "${LARGE_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    MATCHED="$pattern"
    break
  fi
done

if [ -n "$MATCHED" ]; then
  # Warn but don't block -- let Claude proceed but inject guidance
  cat <<EOF
{"warning": "Large file detected (matched: $MATCHED). Consider using offset/limit parameters to avoid file-too-large errors. See CLAUDE.md 'Large File Handling' section."}
EOF
fi

exit 0
```

- **Scope:** Skeleton (propagates to all instances via `kipi update`)

### Change 3: Wire Hook into settings.json

- **What:** Add the large-file-guard hook to the PreToolUse section in settings.json, scoped to Read tool calls only
- **Where:** `/Users/assafkip/Desktop/kipi-system/.claude/settings.json`
- **Why:** Without wiring, the hook script exists but never runs
- **Exact change:**

Add a new entry to the `PreToolUse` array in settings.json:

```json
{
  "matcher": "Read",
  "hooks": [
    {
      "type": "command",
      "command": "bash \"$CLAUDE_PROJECT_DIR/q-system/hooks/large-file-guard.sh\"",
      "timeout": 3
    }
  ]
}
```

This goes before the existing `"matcher": ".*"` token-guard entry so it runs first on Read calls.

- **Scope:** Skeleton (propagates to all instances via `kipi update`)

## 4. Change Interaction Matrix

| Change A | Change B | Interaction | Resolution |
|----------|----------|-------------|------------|
| Change 1 (CLAUDE.md guidance) | Change 2 (hook script) | Both address the same problem. Claude may see the CLAUDE.md guidance and use offset/limit before the hook fires. | Complementary. CLAUDE.md is proactive (Claude plans ahead). Hook is reactive (catches misses). No conflict. |
| Change 2 (hook script) | Change 3 (settings wiring) | Hook does nothing without wiring. | Sequential dependency. Change 2 must exist before Change 3 activates it. |
| Change 2 (hook script) | Existing token-guard (PreToolUse) | Both run on PreToolUse. Token-guard runs on all tools (`.*` matcher). Large-file-guard runs only on Read. | No conflict. Both exit 0 independently. Large-file-guard is ordered first in the array so its warning appears before token-guard's accounting. |

## 5. Files Modified

| File | Change Type | Lines Added | Lines Removed |
|------|------------|-------------|---------------|
| `CLAUDE.md` | Edit | +15 | -0 |
| `q-system/hooks/large-file-guard.sh` | Add | +55 | -0 |
| `.claude/settings.json` | Edit | +9 | -0 |

## 6. Test Cases

### Change 1 Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 1.1 | BEH | Claude reads relationships.md in new session | Ask Claude to summarize relationships | Claude uses offset/limit on first read attempt | Observed over 5 sessions within 1 week |
| 1.2 | BEH | Claude reads a small canonical file | Ask Claude to read objections.md (~50 lines) | Claude reads whole file without offset/limit | No unnecessary offset/limit on small files |

### Change 2 Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 2.1 | DET | Read relationships.md without limit | `{"tool_name":"Read","tool_input":{"file_path":"q-system/my-project/relationships.md"}}` | Stdout contains warning JSON with "Large file detected" | Exit 0, stdout contains warning |
| 2.2 | DET | Read relationships.md with limit | `{"tool_name":"Read","tool_input":{"file_path":"q-system/my-project/relationships.md","limit":100}}` | No warning output | Exit 0, empty stdout |
| 2.3 | DET | Read a non-large file without limit | `{"tool_name":"Read","tool_input":{"file_path":"CLAUDE.md"}}` | No warning output | Exit 0, empty stdout |
| 2.4 | DET | Non-Read tool call | `{"tool_name":"Edit","tool_input":{"file_path":"q-system/my-project/relationships.md"}}` | No warning output | Exit 0, empty stdout |
| 2.5 | DET | Malformed input | `{"bad":"json"}` | Script doesn't crash | Exit 0 |

### Change 3 Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 3.1 | DET | settings.json is valid JSON after edit | `python3 -c "import json; json.load(open('.claude/settings.json'))"` | No error | Exit 0 |
| 3.2 | INT | Hook fires on Read in live session | Read relationships.md in Claude Code session | Warning appears in hook output before Read executes | Visible in session |

## 7. Regression Tests

| # | What to Verify | How to Verify | Pass Criteria |
|---|----------------|---------------|---------------|
| R-1 | Token guard still runs on all tool calls | Run any tool call, check /tmp/claude-guard-*.json updates | Counter increments |
| R-2 | Existing hooks still fire (SessionStart, PostCompact, Stop) | Start new session, observe hook output | All hooks produce expected output |
| R-3 | Read tool still works for small files | Read CLAUDE.md without offset/limit | Full file returned, no errors |

## 8. Rollback Plan

| Change | Rollback Steps | Risk |
|--------|---------------|------|
| Change 1 (CLAUDE.md) | Remove "Large File Handling" section from CLAUDE.md | None. Behavioral guidance only. |
| Change 2 (hook script) | Delete `q-system/hooks/large-file-guard.sh` | None. File is standalone. |
| Change 3 (settings wiring) | Remove the Read matcher entry from PreToolUse array in settings.json | None. Other hooks unaffected. |

## 9. Change Review Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Changes are additive (no breaking removals) | PASS | All three changes are additions |
| No conflicts with existing enforced rules | PASS | Hook exits 0 (warn only), no blocking behavior |
| No hardcoded secrets | PASS | No secrets in any change |
| Propagation path verified (kipi update, global, etc.) | PENDING | CLAUDE.md, settings.json, and hooks/ all propagate via skeleton |
| Exit codes preserved (hooks exit 0) | PASS | Hook always exits 0 |
| AUDHD-friendly (no pressure/shame language added) | PASS | Warning is informational, no shame language |
| Test coverage for every change | PASS | DET tests for hook, BEH tests for CLAUDE.md guidance |

## 10. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| File-too-large errors per 15-day window | 27 | <5 | Count "file-too-large" in usage report |
| Wasted tool calls from large file retries | ~54 | <10 | Count Read retries with offset after error |
| Hook warning rate (fires but Claude still errors) | N/A | <20% of warnings lead to errors | Compare hook fire count vs error count in same window |

## 11. Implementation Order

1. **Create hook script** (`q-system/hooks/large-file-guard.sh`) -- no dependencies
2. **Add CLAUDE.md section** -- no dependencies, can parallel with step 1
3. **Wire hook into settings.json** -- depends on step 1 (script must exist)
4. **Run `kipi update --dry`** to verify propagation diff
5. **Run DET tests** (2.1-2.5) against hook script directly
6. **Run `kipi update`** to push to all instances

## 12. Open Questions

| Question | Owner | Deadline | Resolution |
|----------|-------|----------|------------|
| Should the hook block (exit 2) instead of warn (exit 0) for repeat offenses? | Assaf | 2026-04-16 | Start with warn-only. If errors don't drop below target, add blocking after 2nd warning per file per session. |
| Are there other large files not yet identified? | Assaf | 2026-04-16 | Review next usage report for new file-too-large paths. Add to pattern list. |

## 13. Wiring Checklist (MANDATORY)

| Check | Status | Notes |
|-------|--------|-------|
| PRD file saved to `q-system/output/prd-file-too-large-2026-04-09.md` | DONE | This file |
| All code/config changes implemented and tested | PENDING | |
| New files listed in folder-structure rule (if any created) | PENDING | `q-system/hooks/large-file-guard.sh` needs adding to folder-structure |
| New conventions referenced in root CLAUDE.md (if any added) | PENDING | "Large File Handling" section is the convention itself |
| New rules referenced in folder-structure rules list (if any created) | N/A | No new rules files created |
| Memory entry saved for decisions/patterns worth recalling | PENDING | Save: "PreToolUse warn-only pattern for file hygiene" |
| `kipi update --dry` confirms propagation diff (if skeleton files changed) | PENDING | |
| `kipi update` run to push to all instances (if skeleton files changed) | PENDING | |
| PRD Status field updated to "Done" | PENDING | |
