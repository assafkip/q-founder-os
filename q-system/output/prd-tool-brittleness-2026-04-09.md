# PRD: Codex/Exa External Tool Brittleness

**Date:** 2026-04-09
**Author:** Assaf Kipnis
**Status:** Draft
**Priority:** P1

---

## 1. Problem
External tools (Codex, Exa MCP, browser automation) fail frequently due to auth issues, rate limits, and misconfiguration. Claude doesn't handle these failures gracefully -- it retries blindly, debugs auth mid-session, or halts without a fallback path. This wastes founder time and blocks downstream workflows.

- **Evidence:** 5 tool failures + repeated auth debugging across sessions. 92 "User Rejected" tool errors across 3,000 messages / 169 sessions / 15 days. Report's #3 friction category. Report quote: "You rely heavily on external tools like Codex, Exa MCP, and browser automation that frequently fail due to auth issues, rate limits, or misconfiguration -- and Claude doesn't handle these failures gracefully."
- **Impact:** Auth debugging burns 10-20 min per incident. Downstream PRDs (#5 adversarial review, #6 content pipeline) depend on tools being reliable or having fallbacks. 92 rejected tool calls = wasted tokens and broken flow.
- **Root cause:** No preflight health check for external tools at session start. No defined fallback paths when a tool fails. Claude retries the same broken tool instead of switching to an alternative. Working configs aren't captured, so auth issues recur session to session.

## 2. Scope
### In Scope
- Shell script that tests external tool availability at session start
- Rule file defining fallback paths for each external tool
- Integration with existing session-context.sh hook
- Update to preflight.md documenting the tool health check

### Out of Scope
- Fixing the external tools themselves (Codex rate limits, Exa auth)
- Auto-configuring MCP servers
- Modifying the token-guard or PreToolUse hook

### Non-Goals
- Zero tool failures (external services will always have outages)
- Automatic failover without founder awareness (founder should know when a fallback is active)

## 3. Changes

### Change 1: Tool Health Check Script
- **What:** Shell script that tests each external tool's availability and outputs a status summary
- **Where:** `q-system/hooks/tool-preflight.sh`
- **Why:** 5 tool failures went undetected until mid-workflow. Early detection at session start prevents wasted time.
- **Exact change:**
```bash
#!/bin/bash
set -euo pipefail

# Tool preflight health check - called by session-context.sh at SessionStart
# Tests external tool availability and reports status
# Exit 0 always (informational, never blocks session)

PROJ_DIR="${CLAUDE_PROJECT_DIR:-.}"
if [ -d "$PROJ_DIR/q-system/q-system/canonical" ]; then
  QROOT="$PROJ_DIR/q-system/q-system"
else
  QROOT="$PROJ_DIR/q-system"
fi

STATUS_FILE="$QROOT/memory/working/tool-status.json"
mkdir -p "$(dirname "$STATUS_FILE")"

echo "{"
echo "  \"timestamp\": \"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\","
echo "  \"tools\": {"

# Codex CLI
CODEX_OK="false"
if command -v codex >/dev/null 2>&1; then
  if codex --version >/dev/null 2>&1; then
    CODEX_OK="true"
  fi
fi
echo "    \"codex\": {\"available\": $CODEX_OK, \"fallback\": \"adversarial-review skill (local)\"},"

# Exa MCP - check if the MCP server process is reachable
EXA_OK="false"
if [ -f "$PROJ_DIR/.mcp.json" ]; then
  if grep -q "exa" "$PROJ_DIR/.mcp.json" 2>/dev/null; then
    EXA_OK="maybe"
  fi
fi
echo "    \"exa\": {\"available\": \"$EXA_OK\", \"fallback\": \"WebSearch tool\"},"

# Browser automation (Chrome MCP)
CHROME_OK="false"
if [ -f "$PROJ_DIR/.mcp.json" ]; then
  if grep -q "claude-in-chrome" "$PROJ_DIR/.mcp.json" 2>/dev/null; then
    CHROME_OK="maybe"
  fi
fi
echo "    \"chrome\": {\"available\": \"$CHROME_OK\", \"fallback\": \"WebFetch for public URLs\"},"

# Apify
APIFY_OK="false"
if [ -f "$PROJ_DIR/.mcp.json" ]; then
  if grep -q "apify" "$PROJ_DIR/.mcp.json" 2>/dev/null; then
    APIFY_OK="maybe"
  fi
fi
echo "    \"apify\": {\"available\": \"$APIFY_OK\", \"fallback\": \"Chrome for X/Twitter\"}"

echo "  }"
echo "}"

# Write status file for session reference
cat > "$STATUS_FILE" << JSONEOF
{
  "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "codex": $CODEX_OK,
  "exa": "$EXA_OK",
  "chrome": "$CHROME_OK",
  "apify": "$APIFY_OK"
}
JSONEOF

echo ""
echo "--- Tool Preflight ---"
echo "Codex CLI: $([ "$CODEX_OK" = "true" ] && echo "OK" || echo "NOT FOUND - fallback: local adversarial-review skill")"
echo "Exa MCP: $([ "$EXA_OK" = "maybe" ] && echo "CONFIGURED (verify with ToolSearch)" || echo "NOT CONFIGURED - fallback: WebSearch")"
echo "Chrome MCP: $([ "$CHROME_OK" = "maybe" ] && echo "CONFIGURED (verify with tabs_context)" || echo "NOT CONFIGURED - fallback: WebFetch")"
echo "Apify MCP: $([ "$APIFY_OK" = "maybe" ] && echo "CONFIGURED (verify with ToolSearch)" || echo "NOT CONFIGURED - fallback: Chrome for X")"
echo ""

exit 0
```
- **Scope:** All kipi instances via `kipi update`

### Change 2: Fallback Routing Rule
- **What:** Rule file defining fallback paths for each external tool, loaded when Claude encounters a tool failure
- **Where:** `.claude/rules/tool-fallbacks.md`
- **Why:** Claude retries broken tools instead of switching. A rule file makes fallback behavior deterministic, not LLM-dependent.
- **Exact change:**
```markdown
---
description: External tool fallback routing when tools fail or are unavailable
globs:
  - q-system/hooks/**
  - q-system/.q-system/preflight.md
  - q-system/memory/working/tool-status.json
---

# Tool Fallback Routing (ENFORCED)

When an external tool fails (error, timeout, auth failure, rate limit), do NOT retry
the same tool. Switch to the fallback immediately and tell the founder.

## Fallback Table

| Tool | Failure Modes | Fallback | What You Lose |
|------|--------------|----------|---------------|
| **Codex CLI** | Rate limit, auth failure, API error | `adversarial-review` skill (local, parallel agents) | Codex-specific models. Gain: no rate limits, parallel execution. |
| **Exa MCP** | Not recognized, auth failure, timeout | `WebSearch` tool (built-in) | Structured search results. WebSearch returns snippets. |
| **Chrome MCP** | Timeout, dialog block, tab crash | `WebFetch` for public URLs. Skip for auth-required pages. | JavaScript rendering, login-gated content. |
| **Apify MCP** | Tools don't load, actor errors | Chrome for X/Twitter scraping. RSS feeds for Medium/Substack. | Batch processing. Chrome is slower but more reliable. |
| **Reddit MCP** | Server not running | Skip Reddit scraping entirely. Do NOT use Chrome for Reddit. | Reddit data for that session. |
| **Notion MCP** | Auth failure, API error | Log actions to local markdown in `memory/working/notion-queue.md`. Push on next successful session. | Real-time CRM updates. Data preserved locally. |

## Rules

1. **One retry max.** If a tool fails, try ONE more time. If it fails again, switch to fallback.
2. **Tell the founder.** When switching to a fallback, print: "Switched from [tool] to [fallback] because [reason]."
3. **Don't debug auth mid-session.** If auth is broken, note it for end-of-session and use the fallback now.
4. **Read tool-status.json.** At session start, `tool-preflight.sh` writes tool availability to `q-system/memory/working/tool-status.json`. Check it before attempting any external tool call.
5. **Log failures.** Any tool failure gets logged to the morning log (if in morning routine) or noted in the session handoff.
```
- **Scope:** All kipi instances via `kipi update`

### Change 3: Update preflight.md with Tool Health Check
- **What:** Add a reference to tool-preflight.sh in the preflight manifest's tool testing section
- **Where:** `q-system/.q-system/preflight.md`
- **Why:** Preflight.md is the single source of truth for what tools are available. It needs to reference the automated health check.
- **Exact change:**
Add after the "Reading Order for `/q-morning`" section's item 3:

```markdown
### Automated Tool Health Check

Before running individual tool tests, the `tool-preflight.sh` hook runs automatically
at SessionStart (called by `session-context.sh`). It writes tool availability to
`memory/working/tool-status.json`.

If a tool shows as unavailable in the preflight output:
- Check the fallback table in `.claude/rules/tool-fallbacks.md`
- Use the fallback for that session
- Do NOT spend time debugging auth during the morning routine

The preflight script tests:
- Codex CLI: `codex --version` (binary check)
- Exa MCP: `.mcp.json` config presence (runtime verify via ToolSearch)
- Chrome MCP: `.mcp.json` config presence (runtime verify via tabs_context)
- Apify MCP: `.mcp.json` config presence (runtime verify via ToolSearch)
```
- **Scope:** All kipi instances via `kipi update`

### Change 4: Update session-context.sh to Call tool-preflight.sh
- **What:** Add a call to `tool-preflight.sh` at the end of session-context.sh, before exit 0
- **Where:** `q-system/hooks/session-context.sh`
- **Why:** Tool health check must run automatically at every session start. session-context.sh is the existing SessionStart hook.
- **Exact change:**
Insert before the final `exit 0`:
```bash
# Tool preflight health check
TOOL_PREFLIGHT="$SCRIPT_DIR/tool-preflight.sh"
if [ -f "$TOOL_PREFLIGHT" ] && [ -x "$TOOL_PREFLIGHT" ]; then
  "$TOOL_PREFLIGHT" || true
fi
```
- **Scope:** All kipi instances via `kipi update`

## 4. Change Interaction Matrix
| Change A | Change B | Interaction | Resolution |
|----------|----------|-------------|------------|
| Change 1 (tool-preflight.sh) | Change 4 (session-context.sh update) | session-context.sh calls tool-preflight.sh | Script must exist and be executable before hook runs. Deploy Change 1 first. |
| Change 1 (tool-preflight.sh) | Change 2 (fallback rule) | Preflight writes status JSON; rule references it | Both must ship together for the workflow to be complete. |
| Change 2 (fallback rule) | Change 3 (preflight.md update) | Both reference fallback behavior | No conflict. preflight.md points to the rule file. |
| Change 1 (tool-preflight.sh) | Change 3 (preflight.md update) | preflight.md documents what the script does | Documentation must match script behavior. |

## 5. Files Modified
| File | Change Type | Lines Added | Lines Removed |
|------|-------------|-------------|---------------|
| `q-system/hooks/tool-preflight.sh` | New file | ~65 | 0 |
| `.claude/rules/tool-fallbacks.md` | New file | ~45 | 0 |
| `q-system/.q-system/preflight.md` | Modified | ~18 | 0 |
| `q-system/hooks/session-context.sh` | Modified | ~5 | 0 |

## 6. Test Cases
Tag each: DET (deterministic), BEH (behavioral), INT (integration)

### [Change 1] tool-preflight.sh Tests
| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 1 | DET | Script is executable | `test -x q-system/hooks/tool-preflight.sh` | True | File has execute permission |
| 2 | DET | Script exits 0 even when tools missing | Run on machine without Codex | Exit code 0, status shows codex: false | Never blocks session start |
| 3 | DET | Status JSON written | Run script, check `memory/working/tool-status.json` | Valid JSON with timestamp and tool keys | File exists and parses as valid JSON |
| 4 | DET | Negative: missing .mcp.json | Remove .mcp.json temporarily | All MCP tools show "false" | Script doesn't crash on missing config |

### [Change 2] Fallback Rule Tests
| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 5 | DET | Rule file has valid frontmatter | Parse YAML frontmatter | `description` and `globs` present | Frontmatter valid |
| 6 | BEH | Codex failure triggers fallback | Codex returns rate limit error | Claude switches to adversarial-review skill | No second Codex attempt, fallback used |
| 7 | BEH | Exa failure triggers fallback | Exa MCP not recognized | Claude uses WebSearch instead | Search results returned via WebSearch |
| 8 | BEH | Negative: tool succeeds, no fallback | Codex returns valid result | Normal flow, no fallback message | No "Switched from" message printed |

### [Change 3] preflight.md Tests
| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 9 | DET | New section exists | Grep for "Automated Tool Health Check" in preflight.md | Match found | Section present |

### [Change 4] session-context.sh Tests
| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 10 | INT | Session start runs tool preflight | Start new Claude session | tool-preflight.sh output appears in session context | Tool status printed |
| 11 | DET | Negative: missing tool-preflight.sh | Delete the script temporarily | session-context.sh still exits 0 | Guarded by `-f` check, no crash |

## 7. Regression Tests
| # | What to Verify | How to Verify | Pass Criteria |
|---|----------------|---------------|---------------|
| 1 | session-context.sh still exits 0 | Run `bash q-system/hooks/session-context.sh; echo $?` | Exit code 0 |
| 2 | Morning routine unaffected | Run `/q-morning` after changes | All phases complete, no new errors |
| 3 | Existing preflight tool tests still work | Run morning routine Step 0f | Connection checks pass as before |
| 4 | `kipi check` passes | Run `kipi check` | Validation harness reports no errors |

## 8. Rollback Plan
| Change | Rollback Steps | Risk |
|--------|----------------|------|
| Change 1 (tool-preflight.sh) | Delete `q-system/hooks/tool-preflight.sh`. session-context.sh's guard clause (`-f` check) means it won't crash. | Zero risk. Guard clause handles missing file. |
| Change 2 (fallback rule) | Delete `.claude/rules/tool-fallbacks.md`. Claude reverts to default retry behavior. | Low risk. Behavior returns to pre-PRD state. |
| Change 3 (preflight.md update) | Remove the "Automated Tool Health Check" section from preflight.md. | Zero risk. Documentation only. |
| Change 4 (session-context.sh) | Remove the 4-line tool-preflight call block. | Zero risk. Restores original session-context.sh. |

## 9. Change Review Checklist
| Check | Status | Notes |
|-------|--------|-------|
| Changes are additive (no breaking removals) | PASS | New file + appends to existing files |
| No conflicts with existing enforced rules | PASS | Complements token-discipline (retry rules) and morning-pipeline (preflight) |
| No hardcoded secrets | PASS | Script checks tool presence, doesn't store credentials |
| Propagation path verified (kipi update, global, etc.) | PENDING | `kipi update --dry` needed post-implementation |
| Exit codes preserved (hooks exit 0) | PASS | Both scripts exit 0 unconditionally |
| AUDHD-friendly (no pressure/shame language added) | PASS | Status output is factual, no urgency language |
| Test coverage for every change | PASS | 11 test cases across all 4 changes |

## 10. Success Metrics
| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Tool failure debugging time per session | 10-20 min when failures hit | 0 min (fallback activates automatically) | Session timestamps around tool failures |
| Auth debugging sessions | Multiple per 15-day period | 0 during workflows (deferred to end of session) | Count auth-related tool errors in usage reports |
| "User Rejected" tool errors | 92 per 15 days | <20 (fallbacks prevent repeated broken calls) | Usage report tool error count |
| Tool status awareness at session start | None (discovered mid-workflow) | 100% (every session shows tool status) | Presence of tool-preflight output in session logs |

## 11. Implementation Order
1. Create `q-system/hooks/tool-preflight.sh` (Change 1) -- no dependencies
2. `chmod +x q-system/hooks/tool-preflight.sh`
3. Create `.claude/rules/tool-fallbacks.md` (Change 2) -- no dependencies
4. Update `q-system/.q-system/preflight.md` (Change 3) -- references Changes 1 and 2
5. Update `q-system/hooks/session-context.sh` (Change 4) -- depends on Change 1 existing
6. Test: run `bash q-system/hooks/session-context.sh` and verify tool status output
7. Test: run `kipi check` to validate structure
8. Run `kipi update --dry` to verify propagation
9. Run `kipi update` to push to all instances

## 12. Open Questions
| Question | Owner | Deadline | Resolution |
|----------|-------|----------|------------|
| Should tool-preflight.sh do live MCP tool calls (via ToolSearch) or only file-based checks? | Assaf | 2026-04-16 | Start with file-based (fast, no token cost). Live verification happens during morning routine Step 0f. |
| Should fallback activations be logged to a persistent file for trend analysis? | Assaf | 2026-04-16 | Yes, add to morning-log.json if in routine, or session handoff otherwise. Defer implementation to v2. |
| Should Notion queue (from fallback rule) auto-flush on next successful Notion connection? | Assaf | 2026-04-23 | Defer. Manual flush for now. |

## 13. Wiring Checklist (MANDATORY)
| Check | Status | Notes |
|-------|--------|-------|
| PRD file saved to `q-system/output/prd-tool-brittleness-2026-04-09.md` | DONE | This file |
| All code/config changes implemented and tested | PENDING | Implementation not started |
| New files listed in folder-structure rule (if any created) | PENDING | `tool-preflight.sh` in hooks/, `tool-fallbacks.md` in rules/ |
| New conventions referenced in root CLAUDE.md (if any added) | N/A | No new conventions |
| New rules referenced in folder-structure rules list (if any created) | PENDING | Add `tool-fallbacks.md` to the rules list in folder-structure.md |
| Memory entry saved for decisions/patterns worth recalling | PENDING | Save after implementation |
| `kipi update --dry` confirms propagation diff (if skeleton files changed) | PENDING | Run after implementation |
| `kipi update` run to push to all instances (if skeleton files changed) | PENDING | Run after dry run confirms |
| PRD Status field updated to "Done" | PENDING | Update after all checks pass |
