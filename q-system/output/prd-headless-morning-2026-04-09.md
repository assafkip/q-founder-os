# PRD: Headless Morning Pipeline

**Date:** 2026-04-09
**Author:** Assaf Kipnis
**Status:** Draft
**Priority:** P3 (low)
**Source:** Claude Code Insights report (3,000 messages, 169 sessions, 2026-03-26 to 2026-04-09)
**Depends on:** PRD #2 (tool brittleness - `prd-tool-brittleness-2026-04-09.md`), PRD #5 (autonomous orchestrator - `prd-morning-orchestrator-2026-04-09.md`)

---

## 1. Problem

The morning routine runs interactively in every session. The founder must open a Claude Code session, type `/q-morning`, and stay engaged through the multi-phase pipeline before getting the day's schedule. This costs interactive time on a routine that is mostly deterministic.

- **Evidence:** Usage report. 169 sessions over 15 days, with morning routine triggered in most working-day sessions. Founder reports the routine takes "significant interactive time" before any planning or execution work begins. Most morning phases (preflight, data ingest, scoring, synthesis) do not require founder input.
- **Impact:** Founder cannot get morning briefing without sitting at the terminal. Time-to-first-action delayed by pipeline runtime. Cannot review the schedule on phone or before opening a session. Interactive attention spent on a routine that should be ambient.
- **Root cause:** The morning pipeline is built as an interactive command (`/q-morning`) that requires a Claude Code session in foreground mode. There is no headless wrapper that runs the routine in the background and notifies on completion. Claude Code supports `claude -p` for non-interactive execution, but no script wires the morning routine into it.

---

## 2. Scope

### In Scope
- Shell wrapper that invokes `claude -p` with the morning prompt and a restricted tool allowlist
- Documentation of which tools the headless session needs
- Output capture (stdout/stderr) and structured log
- Notification on completion (macOS notification + log file)
- CLAUDE.md entry documenting the headless option

### Out of Scope
- Replacing the interactive `/q-morning` (both modes coexist)
- Cron scheduling (founder can wire to cron/launchd separately)
- Mobile notification delivery (local macOS notification only)
- Headless versions of other commands (`/q-debrief`, `/q-engage`, etc.)
- Multi-instance orchestration (one instance at a time)

### Non-Goals
- Make the morning routine fully autonomous (founder still needs to confirm action cards)
- Replace the orchestrator (Change scope is wrapping, not rewriting)
- Add UI or web dashboard

---

## 3. Changes

### Change 1: Headless Morning Wrapper Script

- **What:** Bash script that invokes `claude -p` with the morning routine prompt and restricted tool permissions, captures output, and notifies on completion.
- **Where:** `q-system/hooks/headless-morning.sh`
- **Why:** Addresses root cause directly - provides a way to run the morning pipeline without an interactive session. The founder can run this from terminal background, cron, or launchd.
- **Exact change:**

```bash
#!/bin/bash
set -euo pipefail

# Headless morning pipeline runner
# Invokes claude -p with the morning prompt and restricted tools
# Captures output, writes structured log, sends notification on completion

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
QROOT="$PROJ_DIR/q-system"

DATE=$(date +%Y-%m-%d)
LOG_DIR="$QROOT/output"
LOG_FILE="$LOG_DIR/headless-morning-${DATE}.log"
RESULT_FILE="$LOG_DIR/headless-morning-${DATE}.json"

mkdir -p "$LOG_DIR"

# Tool allowlist - read from headless-tools.md (single source of truth)
TOOLS_FILE="$QROOT/.q-system/headless-tools.md"
if [ ! -f "$TOOLS_FILE" ]; then
  echo "ERROR: Tool manifest not found at $TOOLS_FILE" >&2
  exit 1
fi

# Extract allowed tool names from the manifest (lines starting with `- `)
ALLOWED_TOOLS=$(grep '^- ' "$TOOLS_FILE" | sed 's/^- //' | tr '\n' ',' | sed 's/,$//')

if [ -z "$ALLOWED_TOOLS" ]; then
  echo "ERROR: No tools listed in $TOOLS_FILE" >&2
  exit 1
fi

START_TIME=$(date +%s)
START_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=== Headless Morning Pipeline ===" | tee "$LOG_FILE"
echo "Date: $DATE" | tee -a "$LOG_FILE"
echo "Started: $START_ISO" | tee -a "$LOG_FILE"
echo "Project: $PROJ_DIR" | tee -a "$LOG_FILE"
echo "Allowed tools: $ALLOWED_TOOLS" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# The morning prompt
PROMPT="Run /q-morning. Execute all 9 phases of the morning pipeline using the agent orchestrator. Do not ask any clarifying questions. Use the existing canonical files for context. Write all bus files, run all scripts, build the daily schedule HTML, and run the audit harness. Report completion status as: phases completed, blocking failures, output files written. End response with the path to the daily schedule HTML."

# Run claude -p with restricted tools
# Capture exit code without exiting on failure (we want to log the result)
set +e
cd "$PROJ_DIR"
claude -p "$PROMPT" \
  --allowed-tools "$ALLOWED_TOOLS" \
  --output-format text \
  >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

END_TIME=$(date +%s)
END_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DURATION=$((END_TIME - START_TIME))

# Write structured result JSON
cat > "$RESULT_FILE" <<EOF
{
  "date": "$DATE",
  "started_at": "$START_ISO",
  "finished_at": "$END_ISO",
  "duration_seconds": $DURATION,
  "exit_code": $EXIT_CODE,
  "status": "$([ $EXIT_CODE -eq 0 ] && echo "success" || echo "failure")",
  "log_file": "$LOG_FILE",
  "schedule_html": "$QROOT/output/daily-schedule-${DATE}.html",
  "morning_log": "$QROOT/output/morning-log-${DATE}.json"
}
EOF

echo "" | tee -a "$LOG_FILE"
echo "=== Result ===" | tee -a "$LOG_FILE"
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "Duration: ${DURATION}s" | tee -a "$LOG_FILE"
echo "Result file: $RESULT_FILE" | tee -a "$LOG_FILE"

# macOS notification
if command -v osascript >/dev/null 2>&1; then
  if [ $EXIT_CODE -eq 0 ]; then
    osascript -e "display notification \"Morning routine complete (${DURATION}s)\" with title \"Kipi Morning\" sound name \"Glass\""
  else
    osascript -e "display notification \"Morning routine FAILED (exit $EXIT_CODE). Check $LOG_FILE\" with title \"Kipi Morning\" sound name \"Sosumi\""
  fi
fi

exit $EXIT_CODE
```

- **Scope:** All instances. Founder can invoke directly or wire into cron/launchd.

### Change 2: Headless Tools Manifest

- **What:** Markdown file documenting which tools the headless morning session needs.
- **Where:** `q-system/.q-system/headless-tools.md`
- **Why:** The wrapper script needs a tool allowlist to pass to `claude -p --allowed-tools`. A manifest file makes the list maintainable, version-controlled, and a single source of truth that the script reads (no hardcoding).
- **Exact change:**

```markdown
# Headless Morning Tool Manifest

This file lists every tool the headless morning pipeline needs access to. The `headless-morning.sh` wrapper reads this file and passes the tool list to `claude -p --allowed-tools`.

## Format

One tool per line, prefixed with `- `. Tool names match Claude Code's tool naming convention. Lines not starting with `- ` are ignored (comments OK).

## Required Tools

### Core file/process tools
- Bash
- Read
- Write
- Edit
- Glob
- Grep
- Agent
- ToolSearch

### MCP - Calendar/Email
- mcp__claude_ai_Google_Calendar__gcal_list_events
- mcp__claude_ai_Google_Calendar__gcal_get_event
- mcp__claude_ai_Gmail__gmail_search_messages
- mcp__claude_ai_Gmail__gmail_read_message
- mcp__claude_ai_Gmail__gmail_read_thread

### MCP - Notion (CRM)
- mcp__claude_ai_Notion__notion-search
- mcp__claude_ai_Notion__notion-fetch
- mcp__claude_ai_Notion__notion-create-pages
- mcp__claude_ai_Notion__notion-update-page

### MCP - Reddit (lead sourcing)
- mcp__reddit__reddit_search
- mcp__reddit__reddit_search_subreddit
- mcp__reddit__reddit_get_subreddit_posts

### MCP - Apify (X/Twitter only)
- mcp__apify__call-actor
- mcp__apify__fetch-actor-details

### MCP - Chrome (LinkedIn)
- mcp__claude-in-chrome__tabs_context_mcp
- mcp__claude-in-chrome__navigate
- mcp__claude-in-chrome__get_page_text
- mcp__claude-in-chrome__find
- mcp__claude-in-chrome__read_page

### Web fetching (RSS, Medium)
- WebFetch

## Excluded Tools (intentional)

These tools are NOT in the allowlist for headless mode:

- `mcp__claude-in-chrome__form_input` - DM sending requires founder confirmation
- `mcp__claude-in-chrome__shortcuts_execute` - Avoid risky browser shortcuts unattended
- `mcp__gamma__generate_gamma` - Gamma deck generation is interactive, run separately
- `WebSearch` - Not needed for morning routine
- All `mcp__plugin_posthog__*` tools - Not used in morning routine
- All `mcp__threat-intel__*` tools - Not used in morning routine

## Maintenance

When the morning pipeline adds a new tool dependency, add it here. The wrapper script reads this file at runtime - no script changes needed.
```

- **Scope:** All instances using headless mode. The file is read at runtime, so changes take effect on next invocation.

### Change 3: CLAUDE.md Entry

- **What:** Add a section to root `CLAUDE.md` documenting the headless option and how to invoke it.
- **Where:** `/Users/assafkip/Desktop/kipi-system/CLAUDE.md`
- **Why:** Makes the headless option discoverable. Without documentation, the founder will not know to use it, defeating the purpose.
- **Exact change:**

Add a new section after the existing "## Build and Test" section:

```markdown
## Headless Morning Routine

The morning pipeline can run without an interactive Claude Code session via the headless wrapper.

**Manual invocation:**
```bash
bash q-system/hooks/headless-morning.sh
```

**Schedule via launchd (run at 7am daily):**
Create `~/Library/LaunchAgents/com.kipi.headless-morning.plist` with a StartCalendarInterval entry pointing to `headless-morning.sh`. The wrapper handles logging and notification.

**Output:**
- `q-system/output/headless-morning-YYYY-MM-DD.log` - full session log
- `q-system/output/headless-morning-YYYY-MM-DD.json` - structured result
- `q-system/output/daily-schedule-YYYY-MM-DD.html` - the briefing (open in browser)

**Tool allowlist:** Read from `q-system/.q-system/headless-tools.md`. Do not edit the wrapper script to add tools - edit the manifest.

**When to use headless vs interactive:**
- Headless: morning data collection, scoring, schedule build (no founder input needed)
- Interactive: action card confirmation, debriefs, ad-hoc research (requires founder)

The headless pipeline produces the same artifacts as `/q-morning` but skips any phase that requires founder confirmation. Action cards stay in `delivered, unconfirmed` state until the founder opens an interactive session and reviews them.
```

- **Scope:** Skeleton root. Propagates to all instances via `kipi update`.

### Change 4: Output Capture and Notification (covered in Change 1)

- **What:** N/A. This was originally listed as a separate change but is implemented inline in the wrapper script (Change 1). Listed here for completeness.
- **Where:** `q-system/hooks/headless-morning.sh` (same file as Change 1)
- **Why:** Output capture, structured JSON result, and macOS notification are all part of the wrapper. Splitting them adds no value and creates artificial coupling.
- **Exact change:** N/A - implemented in Change 1's script. The notification logic uses `osascript -e "display notification ..."` and the structured result writes to `headless-morning-YYYY-MM-DD.json`.
- **Scope:** N/A.

---

## 4. Change Interaction Matrix

| Change A | Change B | Interaction | Resolution |
|----------|----------|-------------|------------|
| 1 (wrapper script) | 2 (tools manifest) | Wrapper reads manifest at runtime | Wrapper uses `grep` + `sed` to extract tool names from manifest. If manifest missing, wrapper exits 1 with clear error. |
| 1 (wrapper script) | 3 (CLAUDE.md docs) | Docs reference the script path | Docs use literal path `q-system/hooks/headless-morning.sh`. If script renamed, docs must update too. |
| 2 (tools manifest) | 3 (CLAUDE.md docs) | Docs reference the manifest path | Docs say "edit the manifest, not the script." Reinforces SSoT. |
| 1 (wrapper) | PRD #5 orchestrator | Wrapper invokes `/q-morning` which uses orchestrator | If PRD #5 ships first, wrapper benefits from preflight + phase runner automatically. If wrapper ships first, PRD #5's improvements still apply when added. No code coupling. |

---

## 5. Files Modified

| File | Change Type | Lines Added | Lines Removed |
|------|-------------|-------------|---------------|
| `q-system/hooks/headless-morning.sh` | New file | ~95 | 0 |
| `q-system/.q-system/headless-tools.md` | New file | ~70 | 0 |
| `CLAUDE.md` (root) | Modified | ~25 | 0 |

---

## 6. Test Cases

### [Change 1] Wrapper Script Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 1.1 | DET | Script is executable | `ls -la headless-morning.sh` | Has execute permission | Mode includes `x` |
| 1.2 | DET | Manifest missing | Delete headless-tools.md, run wrapper | Exit 1, clear error message | stderr contains "Tool manifest not found" |
| 1.3 | DET | Manifest empty | Empty headless-tools.md, run wrapper | Exit 1, error about empty list | stderr contains "No tools listed" |
| 1.4 | INT | Successful run | Normal morning | claude -p completes, exit 0, logs written | headless-morning-DATE.log + .json exist, schedule HTML built |
| 1.5 | INT | Failed run | Force claude -p failure (e.g., invalid prompt) | Exit non-zero, failure JSON, notification sent | result file has status="failure", notification fired |
| 1.6 | DET | Result JSON format | Run wrapper | result file is valid JSON with required fields | jq parses without error, has date/exit_code/status fields |
| 1.7 | DET | Notification on macOS | Run wrapper on macOS | osascript notification fires | Visible notification (manual check) |
| 1.8 | DET (negative) | Run from wrong directory | `cd /tmp && bash /path/to/headless-morning.sh` | Resolves project paths correctly | Logs written to correct project output dir, not /tmp |

### [Change 2] Tools Manifest Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 2.1 | DET | Manifest parses correctly | Run wrapper extraction logic | Returns comma-separated list | List has all `- ` prefixed entries, no comments |
| 2.2 | DET | All listed tools are valid Claude Code tool names | Compare manifest entries against ToolSearch | Every tool exists in current Claude Code | No "tool not found" errors at runtime |
| 2.3 | DET | Excluded tools are NOT in list | Grep manifest for form_input | No match | grep returns nothing |
| 2.4 | DET (negative) | Manifest with malformed line | Add a line missing the `- ` prefix | Wrapper ignores it | Tool count matches valid lines only |

### [Change 3] CLAUDE.md Docs Tests

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 3.1 | DET | Section added in correct location | Read CLAUDE.md | "Headless Morning Routine" section after "Build and Test" | Section exists at expected location |
| 3.2 | DET | Script path is correct | Compare doc path to actual script | Match | Path in docs matches `q-system/hooks/headless-morning.sh` |
| 3.3 | DET (negative) | No emdashes in added content | Grep for `—` in new section | No match | grep returns nothing |
| 3.4 | DET | Manifest path referenced | Read added section | Mentions `q-system/.q-system/headless-tools.md` | Path appears in docs |

---

## 7. Regression Tests

| # | What to Verify | How to Verify | Pass Criteria |
|---|----------------|---------------|---------------|
| 7.1 | Interactive `/q-morning` still works | Run `/q-morning` in interactive session | Same output as before |
| 7.2 | Headless and interactive produce same artifacts | Run headless one day, interactive another, compare bus files and schedule HTML structure | Same file types, same schema |
| 7.3 | Existing hooks not affected | Run a normal session, verify session-context.sh and stop-logger.sh fire | Hooks fire as before |
| 7.4 | `kipi update` propagates new files | Run `kipi update --dry` after creating files | Diff shows new wrapper, manifest, CLAUDE.md changes |
| 7.5 | No conflicts with token-guard | Run headless mode | Token-guard hook does not block (it shouldn't fire on headless `claude -p`) |

---

## 8. Rollback Plan

| Change | Rollback Steps | Risk |
|--------|---------------|------|
| 1 (wrapper script) | Delete `headless-morning.sh`. Founder reverts to interactive `/q-morning`. | Low - script is purely additive. |
| 2 (tools manifest) | Delete `headless-tools.md`. Wrapper would fail without it, but if Change 1 also rolled back, no impact. | Low - file is read-only by wrapper. |
| 3 (CLAUDE.md docs) | `git revert` the CLAUDE.md edit. | Low - text only. |

All three changes can be rolled back independently. Removing them reverts to current interactive-only behavior with zero impact on existing functionality.

---

## 9. Change Review Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Changes are additive (no breaking removals) | Pending | All 3 changes are new files or additive doc edits. |
| No conflicts with existing enforced rules | Pending | Wrapper does not bypass token-guard, gates, or audit. It invokes `/q-morning` which respects all rules. |
| No hardcoded secrets | Pending | No secrets in script or manifest. `claude -p` uses founder's existing auth. |
| Propagation path verified (kipi update, global, etc.) | Pending | New files in `q-system/hooks/` and `q-system/.q-system/` propagate via kipi update. Root CLAUDE.md propagates too. |
| Exit codes preserved (hooks exit 0) | Pending | This is NOT a Claude Code hook (not in .claude/settings.json). It is a standalone script. Exit codes reflect run success/failure - intentional. |
| AUDHD-friendly (no pressure/shame language added) | Pending | Notification text is factual ("complete", "FAILED"). No urgency or shame. |
| Test coverage for every change | Pending | 8 + 4 + 4 = 16 test cases. |

---

## 10. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Interactive time spent on morning routine | Full pipeline duration (~10-30 min interactive) | <2 min interactive (review only) | Time from session start to first non-morning action |
| Days morning routine ran without founder at terminal | 0 | 5+ per week | Count `headless-morning-*.json` files with status=success |
| Time-to-schedule on demand | Open session, type /q-morning, wait for pipeline | Open `daily-schedule-DATE.html` directly | Founder opens HTML before any session |
| Headless failure rate | N/A (does not exist) | <10% of runs | Failed result files / total result files |

---

## 11. Implementation Order

1. Create `headless-tools.md` (Change 2) - no dependencies, can be reviewed standalone
2. Create `headless-morning.sh` (Change 1) - depends on Change 2 (reads the manifest)
3. `chmod +x headless-morning.sh` - script must be executable
4. Run test cases 1.1-1.3, 2.1-2.4 (deterministic, fast)
5. Run integration test 1.4 (full headless run on a real morning)
6. Update `CLAUDE.md` (Change 3) - depends on script existing
7. Run test cases 3.1-3.4
8. `kipi update --dry` to verify propagation
9. `kipi update` to push to all instances

PRD #5 (orchestrator) is a soft dependency. If PRD #5 ships first, the headless wrapper inherits its preflight and phase runner improvements automatically. If headless ships first, the wrapper still works - PRD #5 improvements apply on next invocation after they ship. No coupling.

---

## 12. Open Questions

| Question | Owner | Deadline | Resolution |
|----------|-------|----------|------------|
| Should the wrapper run `/q-morning` or call the orchestrator directly? | Assaf | Before implementation | Current design: invoke `/q-morning` via prompt. Keeps the wrapper agnostic of pipeline internals. |
| What happens if the founder runs headless and interactive on the same day? | Assaf | Before implementation | Bus files overwrite each run. Interactive run after headless will reprocess everything. Should the wrapper check for an existing morning-log and skip? Default: do not skip - founder wants fresh data. |
| Should the wrapper send notifications to phone (push) instead of macOS local? | Assaf | Future enhancement | Out of scope for v1. macOS local is sufficient for desk-based founder. |
| Does `claude -p` in non-interactive mode handle the 9-phase pipeline within reasonable runtime? | Assaf | During testing | Test 1.4 will measure. Expected: 5-15 min total. If it exceeds 30 min, may need to split into stages. |
| Should headless mode skip phases that need founder input (action card confirmation)? | Assaf | Before implementation | Current design: run all phases. Action cards stay unconfirmed until founder opens interactive session. The next interactive `/q-morning` reads yesterday's unconfirmed cards (existing behavior). |

---

## 13. Wiring Checklist (MANDATORY)

| Check | Status | Notes |
|-------|--------|-------|
| PRD file saved to `q-system/output/prd-headless-morning-2026-04-09.md` | Done | This file |
| All code/config changes implemented and tested | Pending | Wrapper, manifest, CLAUDE.md edit |
| New files listed in folder-structure rule (if any created) | Pending | `headless-morning.sh` in `q-system/hooks/` (existing dir, no rule update needed). `headless-tools.md` in `q-system/.q-system/` (existing dir, no rule update needed). |
| New conventions referenced in root CLAUDE.md (if any added) | Done as part of Change 3 | Headless Morning Routine section |
| New rules referenced in folder-structure rules list (if any created) | N/A | No new rules files created |
| Memory entry saved for decisions/patterns worth recalling | Pending | Save entry: "Headless mode pattern - claude -p with manifest-driven tool allowlist" |
| `kipi update --dry` confirms propagation diff (if skeleton files changed) | Pending | Run after implementation |
| `kipi update` run to push to all instances (if skeleton files changed) | Pending | Run after dry verification |
| PRD Status field updated to "Done" | Pending | Update after all implementation complete |
