# PRD: Usage Report Friction Fixes

**Date:** 2026-04-09
**Author:** Assaf Kipnis
**Status:** Draft
**Priority:** P1 (high)
**Source:** Claude Code Insights report (3,000 messages, 169 sessions, 2026-03-26 to 2026-04-09)

---

## 1. Problem

The Claude Code Insights report reveals systemic friction patterns that waste founder time across sessions.

**Evidence:** Usage report at `~/.claude/usage-data/report.html`

| Friction Type | Count | % of Total |
|---------------|-------|------------|
| Wrong approach | 29 | 41% |
| Misunderstood request | 16 | 23% |
| Buggy code | 15 | 21% |
| Excessive changes | 5 | 7% |
| Tool failure | 3 | 4% |
| External tool failure | 2 | 3% |

**Impact:**
- 70 friction events across 169 sessions = 41% of sessions hit avoidable friction
- 92 "User Rejected" tool errors = founder manually blocking bad actions
- 39 "File Not Found" errors = stale paths and wrong-directory searches
- Inferred satisfaction: 24 frustrated/dissatisfied sessions vs 16 satisfied/happy

**Root causes (3 layers):**
1. **No pre-execution alignment.** Claude starts multi-file tasks without confirming intent. 29 wrong-approach events.
2. **Short responses misread.** "No" gets interpreted as a prompt for elaboration. 16 misunderstood events.
3. **Wrong fix pattern.** Claude fixes LLM-instruction failures with more LLM instructions. Same failure mode repeats.
4. **Instance confusion.** Claude searches wrong project directory despite cluster map existing in rules.
5. **Scope creep.** Claude adds unrequested improvements after getting the approach right. 5 excessive-changes events.
6. **Tone drift.** Claude defaults to formal/consultant style when casual is needed. Repeated across outreach, agendas, Slack replies.
7. **Cross-directory leakage.** Claude reads files from sibling instances without stating it's doing so.

---

## 2. Scope

### In Scope
- CLAUDE.md rule additions (global + skeleton) to address friction patterns 1-6
- Session-start hook enhancement for instance identity (pattern 4)
- Directory boundary rule (pattern 7)
- Change interaction analysis
- Deterministic + behavioral test coverage

### Out of Scope
- **Adversarial review Custom Skill.** Report's #1 pattern suggestion. Separate PRD. Requires defining review checklist format, fix-and-commit flow, and replacing Codex dependency.
- **Headless morning pipeline.** Report's horizon suggestion. Requires architecture work on fallback logic and preflight automation. Separate PRD.
- **File-too-large error reduction (27 events).** Requires auditing which files Claude tries to read whole and adding offset/limit patterns. Separate, mechanical fix.
- **Codex/Exa external tool brittleness.** Report's #3 friction category. Requires per-tool fallback paths and auth caching. Too tool-specific for this PRD.

### Non-Goals
- Eliminating all friction. Some friction is healthy (founder catching genuine mistakes).
- Automating the approach gate. The gate is intentionally manual to force alignment.
- Changing the cluster map structure. The map is correct. The problem is Claude not referencing it.

---

## 3. Changes

### Change 1: Brief Dismissal Rule

- **What:** When the founder says "no", gives a one-word answer, or briefly dismisses a topic, Claude treats it as closed. No elaboration, no reframing, no follow-up.
- **Where:** `~/.claude/CLAUDE.md` under `## Communication Style`
- **Why:** 16 misunderstood-request events. Multiple sessions show Claude interpreting "no" as a prompt to provide more info, argue tool availability, or offer alternatives. (Section 1, root cause #2)
- **Exact change:**
```markdown
## Communication Style
# ... existing bullets ...
- When I say "no" or give a brief dismissal, that topic is closed. Do not elaborate, reframe, or interpret it as a question. Move on.
```
- **Scope:** Global (all instances inherit from `~/.claude/CLAUDE.md`)

---

### Change 2: Deterministic-First Rule

- **What:** When something fails because an LLM misinterpreted instructions, the fix must be a shell script, Python script, or code change. Not better instructions, not a longer prompt, not a retry with different wording.
- **Where:** `/Users/assafkip/Desktop/kipi-system/CLAUDE.md` under `## Conventions`
- **Why:** Repeated failure mode in morning pipeline and hook wiring. Claude defaults to "let me rewrite the instruction" when the root cause is non-deterministic LLM behavior. (Section 1, root cause #3)
- **Exact change:**
```markdown
## Conventions
# ... existing bullets ...
- When something fails because an LLM misinterpreted instructions, the fix must be a deterministic script or code change. Never fix LLM-instruction failures with better instructions.
```
- **Scope:** All kipi-system instances (skeleton CLAUDE.md, propagated via `kipi update`)

---

### Change 3: Approach-Before-Execute Gate

- **What:** For any task involving more than a single file edit, Claude states the planned approach in 1-2 bullet points and waits for the founder's OK before executing. No assumptions.
- **Where:** `/Users/assafkip/Desktop/kipi-system/CLAUDE.md` under `## Conventions`
- **Why:** 29 wrong-approach events. Highest friction category. Includes over-engineering, wrong tools, wrong instances, scope creep. A one-line checkpoint catches most of these before wasted effort. (Section 1, root cause #1)
- **Exact change:**
```markdown
## Conventions
# ... existing bullets ...
- For any task involving more than a single file edit, state the planned approach in 1-2 bullet points and wait for the founder's OK before executing. Do not proceed on assumption.
```
- **Scope:** All kipi-system instances

---

### Change 4: Instance Identity Echo

- **What:** The `session-context.sh` hook prints which project instance is active at session start, resolved from `instance-registry.json`.
- **Where:** `q-system/hooks/session-context.sh`
- **Why:** Multiple sessions had Claude operating in the wrong instance. The cluster map exists but Claude doesn't read it proactively. Echoing the instance name forces awareness. (Section 1, root cause #4)
- **Exact change:** Add after the `echo "Date: ..."` line:
```bash
# Instance identity
INSTANCE_NAME=""
REGISTRY="/Users/assafkip/Desktop/kipi-system/instance-registry.json"
if [ -f "$REGISTRY" ] && command -v python3 >/dev/null 2>&1; then
  INSTANCE_NAME=$(python3 -c "
import json, os
try:
    with open('$REGISTRY') as f:
        data = json.load(f)
    proj = os.path.realpath('$PROJ_DIR')
    for inst in data.get('instances', []):
        if os.path.realpath(inst['path']) == proj:
            print(inst['name'])
            break
    else:
        if proj == os.path.realpath(data.get('skeleton', {}).get('path', '')):
            print('kipi-system (skeleton)')
except Exception:
    pass
" 2>/dev/null || true)
fi
if [ -z "$INSTANCE_NAME" ]; then
  INSTANCE_NAME=$(basename "$PROJ_DIR")
fi
echo "Instance: $INSTANCE_NAME"
echo "Directory: $PROJ_DIR"
```
- **Scope:** All instances (propagated via `kipi update`)

---

### Change 5: Scope-Creep Prevention Rule

- **What:** When fixing identified issues, fix exactly what was flagged. No architectural changes, refactors, or improvements beyond the request.
- **Where:** `/Users/assafkip/Desktop/kipi-system/CLAUDE.md` under `## Conventions`
- **Why:** 5 excessive-changes events. Claude adds unrequested improvements after getting the approach right. Investor update cadences over-complicated, token guard workarounds expanded, extra config added. (Section 1, root cause #5)
- **Exact change:**
```markdown
## Conventions
# ... existing bullets ...
- When fixing identified issues, fix exactly what was flagged. No architectural changes, refactors, or scope expansion beyond the request.
```
- **Scope:** All kipi-system instances

---

### Change 6: Casual Tone Default

- **What:** Default to casual, direct tone in all drafted messages and docs. Never write formal/consultant/pitch style unless explicitly asked.
- **Where:** `~/.claude/CLAUDE.md` under `## Communication Style`
- **Why:** Repeated friction across sessions where Claude over-formalized agendas into pitch decks, outreach messages into corporate letters, and Slack replies into press releases. Required multiple rounds of tone correction each time. (Section 1, root cause #6)
- **Exact change:**
```markdown
## Communication Style
# ... existing bullets ...
- Default to casual, direct tone in all drafted messages and docs. Never write formal/consultant/pitch style unless I explicitly ask for it.
```
- **Scope:** Global (all instances)

---

### Change 7: Directory Boundary Rule

- **What:** Never read or search files outside `$PROJ_DIR` without stating which directory and getting a reason on the record.
- **Where:** `/Users/assafkip/Desktop/kipi-system/CLAUDE.md` under `## Conventions`
- **Why:** Claude silently searches sibling instances (strategy files when in lawyer, product ICP data when in morning routine) and pulls wrong context without the founder knowing. Change 4 (instance echo) tells Claude where it IS. This rule prevents Claude from wandering outside. (Section 1, root cause #7)
- **Exact change:**
```markdown
## Conventions
# ... existing bullets ...
- Never read or search files outside the current project directory without stating which directory you're reaching into and why. If unsure which instance owns the data, ask.
```
- **Scope:** All kipi-system instances

---

## 4. Change Interaction Matrix

| Change A | Change B | Interaction | Resolution |
|----------|----------|-------------|------------|
| 1 (Brief Dismissal) | 3 (Approach Gate) | Founder says "no" to a proposed approach. | Dismissal rule fires: Claude drops the approach. Then asks "What approach do you want?" (one question, not an elaboration). The gate still requires an approach before executing. |
| 3 (Approach Gate) | Plan Adherence (existing) | Founder created a plan, then triggers a multi-file task. | Plan Adherence takes precedence. If a plan exists and the founder said "go," Claude follows the plan. No redundant approach checkpoint. |
| 5 (Scope Creep) | 3 (Approach Gate) | Founder approves approach. Claude finds adjacent improvement during execution. | Scope Creep rule fires: Claude does not add the improvement. If it matters, mention it after the task is done as a separate suggestion. |
| 7 (Directory Boundary) | Cluster Map (existing rule) | Claude needs data from a sibling instance. | Directory Boundary fires first: Claude states "I need to read X from the strategy instance because Y." Cluster map governs which instance owns which data. Both rules compose cleanly. |
| 1 (Brief Dismissal) | AUDHD Rules (existing) | Founder dismisses with "no." | Both align. AUDHD says "present choices not commands." Dismissal says "move on." Claude moves on without pressure or guilt. No conflict. |
| 2 (Deterministic-First) | Token Discipline (existing) | Claude's deterministic fix attempt fails. | Token Discipline fires: "do NOT retry the same call." Claude tries a different deterministic approach, not an instruction rewrite. Both rules push toward the same behavior. |
| 6 (Casual Tone) | Voice Enforcement (existing rule) | Claude drafts a LinkedIn post. | Voice Enforcement loads the full voice DNA (scar pattern, contrast pattern, anti-AI checks). Casual Tone sets the baseline register. Voice rules are more specific and take precedence on published content. Casual Tone governs everything else (internal docs, Slack, DMs). |

---

## 5. Files Modified

| File | Change Type | Lines Added | Lines Removed |
|------|------------|-------------|---------------|
| `~/.claude/CLAUDE.md` | Add 2 bullets (Changes 1, 6) | +2 | 0 |
| `kipi-system/CLAUDE.md` | Add 4 bullets (Changes 2, 3, 5, 7) | +4 | 0 |
| `q-system/hooks/session-context.sh` | Add instance identity block (Change 4) | +18 | 0 |

Total: 3 files, ~24 lines added, 0 lines removed.

---

## 6. Test Cases

### Change 1: Brief Dismissal

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 1.1 | BEH | Founder says "no" to suggestion | "Should I update marketing copy?" -> "no" | Claude moves to next topic | Response does not mention marketing copy |
| 1.2 | BEH | One-word dismissal | "Check Notion too?" -> "nah" | Claude proceeds without Notion | No follow-up question about Notion |
| 1.3 | BEH | "No" to tool claim | "Exa might not be loaded" -> "it is, move on" | Claude uses Exa directly | Next action calls Exa MCP |
| 1.4 | BEH | Ambiguous compound "no" (negative) | "no" to "Should I do A or B?" | Claude asks ONE clarifying question | Single question, not an elaboration |
| 1.5 | BEH | "No" to one step in multi-step | Proposes A, B, C -> founder rejects B | Claude executes A and C only | Step B absent from execution |

**Observation window:** Verified over next 15 days via next insights report. Target: misunderstood-request events < 5.

### Change 2: Deterministic-First

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 2.1 | BEH | LLM-instruction failure | Agent prompt misread causes pipeline failure | Claude proposes .py/.sh fix | Fix is executable code, not .md edit |
| 2.2 | BEH | Stale path from "use today" instruction | Bus dir has yesterday's date | Claude adds `date +%Y-%m-%d` in script | Deterministic date resolution |
| 2.3 | BEH | Dedup skipped due to ambiguous instruction | Agent didn't dedup because wording was unclear | Claude writes Python dedup function | Executable code with testable output |
| 2.4 | BEH | Code typo (negative) | Python variable misspelled | Claude fixes typo directly | Normal code fix, rule does not apply |
| 2.5 | BEH | Template variable mismatch | Jinja output wrong due to renamed variable | Claude fixes template code | Template file edited, not agent prompt |

**Observation window:** Verified over next 15 days. Target: "fix-with-instructions" pattern drops to 0.

### Change 3: Approach-Before-Execute Gate

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 3.1 | BEH | Multi-file task | "Update pipeline to use Exa" | Claude states 1-2 bullet approach, waits | Response ends with bullets + wait |
| 3.2 | BEH | Single-file task (negative) | "Fix typo on line 42 of session-context.sh" | Claude fixes immediately | No checkpoint |
| 3.3 | BEH | Ambiguous scope | "Clean up canonical files" | Claude clarifies "clean up" in bullets | Approach defines scope before edits |
| 3.4 | BEH | Plan exists (negative) | /plan created, founder says "go" | Claude follows plan directly | No redundant approach statement |
| 3.5 | BEH | Founder rejects approach | Claude proposes -> founder says "no, do X" | Claude adopts founder's approach | Execution matches founder's stated approach |
| 3.6 | BEH | Trivial multi-file | "Add comment to files A and B" | Minimal approach statement | 1 line max |
| 3.7 | BEH | Founder approves, Claude finds adjacent fix | During execution, spots unrelated issue | Claude finishes original scope, mentions issue separately after | No unrequested changes mid-task |

**Observation window:** Verified over next 15 days. Target: wrong-approach events < 10.

### Change 4: Instance Identity Echo

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 4.1 | DET | Known instance (strategy) | `PROJ_DIR=~/Desktop/ktlyst-hub/strategy bash session-context.sh` | stdout: "Instance: KTLYST_strategy" | grep passes |
| 4.2 | DET | Known instance (lawyer) | `PROJ_DIR=~/Desktop/ktlyst-hub/lawyer bash session-context.sh` | stdout: "Instance: ktlyst_lawyer" | grep passes |
| 4.3 | DET | Skeleton repo | `PROJ_DIR=~/Desktop/kipi-system bash session-context.sh` | stdout: "Instance: kipi-system (skeleton)" | grep passes |
| 4.4 | DET | Unknown directory (fallback) | `PROJ_DIR=/tmp/random bash session-context.sh` | stdout: "Instance: random" | basename used |
| 4.5 | DET | Registry missing | Delete registry, run hook | Fallback to basename, exit 0 | No traceback, exit 0 |
| 4.6 | DET | python3 unavailable | `PATH=/usr/bin bash session-context.sh` (hypothetical) | Fallback to basename, exit 0 | exit 0 |

**Verification:** Run each command, check stdout and exit code. Fully automated.

### Change 5: Scope-Creep Prevention

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 5.1 | BEH | Fix flagged issue, adjacent code is messy | "Fix the SQL injection on line 30" | Claude fixes line 30 only | No other lines changed |
| 5.2 | BEH | Fix flagged issue, spots improvement | During fix, notices duplicate code | Claude finishes fix, suggests improvement as separate item | Improvement is a suggestion, not an edit |
| 5.3 | BEH | Broad task (negative) | "Refactor the auth module" | Claude may make multiple changes | Rule does not apply to open-ended tasks |

**Observation window:** Verified over next 15 days. Target: excessive-changes events < 2.

### Change 6: Casual Tone Default

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 6.1 | BEH | Draft meeting agenda | "Draft agenda for Friday call with investor" | Casual bullet points, not formal presentation | No "Dear," no section headers like "Objective" |
| 6.2 | BEH | Draft Slack reply | "Reply to Dave's message about the demo" | Conversational, short, direct | Reads like a text message, not a memo |
| 6.3 | BEH | Draft LinkedIn post (negative, voice rules override) | "Write a LinkedIn post about X" | Voice enforcement skill fires, scar pattern used | Voice rules take precedence over casual default |
| 6.4 | BEH | Founder asks for formal (negative) | "Write a formal email to our lawyer" | Claude writes formally | Explicit override respected |

**Observation window:** Verified over next 15 days. Target: over-formalization corrections drop to 0.

### Change 7: Directory Boundary

| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 7.1 | BEH | Task requires sibling instance data | "What's the latest talk track for KTLYST?" (from lawyer instance) | Claude states "I need to read from strategy instance because talk tracks live there" | Directory stated before reading |
| 7.2 | BEH | Task is local (negative) | "Update the objections file" (from strategy, which owns it) | Claude edits directly | No boundary check needed for local files |
| 7.3 | BEH | Ambiguous data source | "Check the ICP data" (could be product or strategy) | Claude asks which instance | Question asked before reading |

**Observation window:** Verified over next 15 days. Target: wrong-instance data pulls = 0.

---

## 7. Regression Tests

| # | What to Verify | How to Verify | Pass Criteria |
|---|----------------|---------------|---------------|
| R-1 | Plan Adherence still works | Create a plan via /plan, execute | No skipped steps, no substituted approaches |
| R-2 | Session-start.py hook still runs | Start session, check for "SESSION START CONTEXT" | Both hooks produce output without conflict |
| R-3 | Post-compact hook unchanged | Trigger compaction, check output | All 5 sections present (mode, loops, pipeline, canonical, reminders) |
| R-4 | Token discipline enforced | Hit 10+ tool calls in one task | Self-check message appears |
| R-5 | AUDHD rules unaffected | Request actionable output | Copy-paste-ready, energy-tagged |
| R-6 | Voice enforcement unaffected | Draft LinkedIn post | Scar pattern, contrast pattern, no banned words |
| R-7 | Single-file edits unblocked | Fix typo in one file | No approach checkpoint |
| R-8 | session-context.sh exit 0 | `bash q-system/hooks/session-context.sh; echo $?` | Returns 0 |
| R-9 | kipi update propagation | `kipi update --dry` on an instance | Diff shows new CLAUDE.md bullets |
| R-10 | All hooks present in settings | Read `.claude/settings.json`, check 5 hook events | SessionStart, UserPromptSubmit, PreToolUse, PostCompact, Stop all present |
| R-11 | Council auto-trigger unaffected | Make >5 line canonical change | Council check fires per auto-detection rules |
| R-12 | Social reaction gate unaffected | Share someone's post and ask to comment | Claim extraction step happens before draft |

---

## 8. Rollback Plan

All changes are additive. Rollback = delete the added lines.

| Change | Rollback Steps | Risk |
|--------|---------------|------|
| 1 (Brief Dismissal) | Remove bullet from `~/.claude/CLAUDE.md` Communication Style | None. File is personal, not committed. |
| 2 (Deterministic-First) | Remove bullet from `kipi-system/CLAUDE.md` Conventions | Run `kipi update` to propagate removal to instances. |
| 3 (Approach Gate) | Remove bullet from `kipi-system/CLAUDE.md` Conventions | Same propagation. Verify Plan Adherence still works alone. |
| 4 (Instance Echo) | Remove 18-line block from `session-context.sh` | Run `kipi update`. Verify hook still exits 0. |
| 5 (Scope Creep) | Remove bullet from `kipi-system/CLAUDE.md` Conventions | Same propagation. |
| 6 (Casual Tone) | Remove bullet from `~/.claude/CLAUDE.md` Communication Style | None. Personal file. |
| 7 (Directory Boundary) | Remove bullet from `kipi-system/CLAUDE.md` Conventions | Same propagation. |

No database migrations, no config format changes, no breaking API changes.

---

## 9. Change Review Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Changes are additive (no breaking removals) | PASS | 24 lines added, 0 removed |
| No conflicts with Plan Adherence rule | PASS | Approach gate defers to existing plans (see interaction matrix) |
| No conflicts with Token Discipline | PASS | Approach gate adds 1 exchange, not retries |
| No conflicts with AUDHD interaction rules | PASS | All new rules use non-pressure language |
| No conflicts with Voice Enforcement | PASS | Casual tone defers to voice rules on published content |
| No conflicts with Social Reaction Gate | PASS | No changes to reaction flow |
| No conflicts with Council auto-trigger | PASS | No changes to canonical write flow |
| session-context.sh still exits 0 on all paths | PASS | All new code wrapped in `|| true` |
| No hardcoded secrets | PASS | Registry path is a public config file |
| Propagation path verified | PASS | CLAUDE.md + hooks/ are skeleton files, `kipi update` propagates |
| Global CLAUDE.md is user-scoped | PASS | `~/.claude/CLAUDE.md` is personal, not committed |
| Test coverage for every change | PASS | 30 test cases + 12 regression tests |
| AUDHD-friendly language | PASS | No shame, urgency, or pressure in any added rule |

---

## 10. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Wrong-approach friction events | 29 / 15 days | < 10 / 15 days | Next Claude Code Insights report (run after 15 days) |
| Misunderstood-request friction events | 16 / 15 days | < 5 / 15 days | Next Insights report |
| Excessive-changes friction events | 5 / 15 days | < 2 / 15 days | Next Insights report |
| "User Rejected" tool errors | 92 / 15 days | < 50 / 15 days | Next Insights report |
| Instance confusion incidents | ~5 sessions | 0 sessions | Next Insights report, grep for cross-directory reads |
| Over-formalization corrections | ~6 sessions | 0 sessions | Next Insights report, search for tone-correction messages |
| Inferred satisfaction: frustrated + dissatisfied | 24 / 15 days | < 10 / 15 days | Next Insights report |

**Measurement cadence:** Run Insights report on 2026-04-24 (15 days post-implementation). Compare.

---

## 11. Implementation Order

1. **Change 1** (global CLAUDE.md, brief dismissal) - standalone, no dependencies
2. **Change 6** (global CLAUDE.md, casual tone) - same file, add after Change 1
3. **Change 2** (skeleton CLAUDE.md, deterministic-first) - standalone
4. **Change 3** (skeleton CLAUDE.md, approach gate) - same file
5. **Change 5** (skeleton CLAUDE.md, scope creep) - same file
6. **Change 7** (skeleton CLAUDE.md, directory boundary) - same file
7. **Change 4** (session-context.sh, instance echo) - test with `bash q-system/hooks/session-context.sh` before committing
8. Run TC-4.1 through TC-4.6 (deterministic tests on the hook)
9. `kipi update --dry` to verify propagation diff
10. `kipi update` to push to all instances
11. R-8 through R-10 regression checks post-propagation

Steps 1-2 are one edit. Steps 3-6 are one edit. Step 7 is one edit. Three edits total.

---

## 12. Open Questions

| Question | Owner | Deadline | Resolution |
|----------|-------|----------|------------|
| Should the approach gate fire for 2-file tasks or only 3+? | Assaf | 2026-04-11 | Current spec: >1 file. May be too aggressive for trivial 2-file edits. Observe for 1 week. |
| Should directory boundary rule apply to bridge files (`~/.ktlyst/bridge/`)? | Assaf | 2026-04-11 | Bridge files are designed for cross-instance reads. Candidate for explicit exemption. |
| Should casual tone rule live in global CLAUDE.md or skeleton? | Assaf | 2026-04-10 | Currently global. If non-KTLYST instances need formal defaults, move to skeleton. |
| When to schedule the adversarial review Custom Skill PRD? | Assaf | 2026-04-16 | Report's #1 pattern suggestion. Deferred from this PRD. |

---

## 13. Wiring Checklist (MANDATORY)

| Check | Status | Notes |
|-------|--------|-------|
| PRD file saved to `q-system/output/prd-usage-report-fixes-2026-04-09.md` | DONE | |
| All code/config changes implemented and tested | DONE | Global CLAUDE.md (prior session), skeleton CLAUDE.md (this session), session-context.sh (this session) |
| New files listed in folder-structure rule | DONE | `prd-*.md` added to output/ tree, PRD placement rule added |
| New conventions referenced in root CLAUDE.md | DONE | PRD template convention added to Conventions section |
| New rules referenced in folder-structure rules list | N/A | No new rule files created |
| Memory entry saved for decisions/patterns worth recalling | DONE | PRD template memory saved |
| `kipi update --dry` confirms propagation diff | PENDING | Run after all edits complete |
| `kipi update` run to push to all instances | PENDING | Run after dry-run confirmed |
| PRD Status field updated to "Done" | PENDING | After propagation complete |
