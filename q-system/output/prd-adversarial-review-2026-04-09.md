# PRD: Parallel Adversarial Review Skill

**Date:** 2026-04-09
**Author:** Assaf Kipnis
**Status:** Draft
**Priority:** P1

---

## 1. Problem
Adversarial code review is the most repeated workflow (8+ sessions, 29 wrong-approach friction events across 3,000 messages / 169 sessions / 15 days). Currently depends on Codex API which hits daily rate limits and auth failures, blocking entire review sessions. Claude over-engineers, picks wrong tools, or misscopes reviews because there's no codified checklist defining what "adversarial review" means.

- **Evidence:** Usage report shows 29 wrong-approach friction events. Codex rate limits blocked multiple sessions. 8+ sessions spent on adversarial review workflows. Report's #1 pattern suggestion: "Codify your adversarial code review into a Custom Skill."
- **Impact:** Founder loses 1-2 hours per blocked session. Review quality varies because scope isn't defined. External API dependency creates unpredictable failures.
- **Root cause:** No local skill definition for adversarial review. Relies on Codex (external API) for code analysis. No structured checklists, so each review session reinvents scope. No parallel execution, so reviews run sequentially and burn context.

## 2. Scope
### In Scope
- New `adversarial-review` skill in `plugins/kipi-core/skills/`
- Three review dimension checklists (security, architecture, performance)
- Coordinator SKILL.md that spawns 3 parallel Agent tool calls
- Finding collection, dedup, prioritization, and auto-fix workflow

### Out of Scope
- Removing Codex entirely (it still has value for non-review tasks)
- CI/CD integration or git hook automation
- Review of non-code files (docs, config-only changes)

### Non-Goals
- Replacing human judgment on whether to merge
- Catching business logic errors (those require domain context the skill won't have)

## 3. Changes

### Change 1: Security Review Checklist
- **What:** Markdown checklist of security review items an agent evaluates against a git diff
- **Where:** `plugins/kipi-core/skills/adversarial-review/references/security-checklist.md`
- **Why:** 29 wrong-approach friction events include misscoped security reviews. A fixed checklist eliminates scope drift.
- **Exact change:**
```markdown
# Security Review Checklist

Evaluate the git diff against each item. Report PASS, FAIL (with line ref), or N/A.

## Input Validation
- [ ] All user-controlled input is validated before use
- [ ] No raw string interpolation into SQL, shell commands, or file paths
- [ ] File path inputs are canonicalized and checked against allowed directories

## Authentication & Authorization
- [ ] No hardcoded secrets, tokens, or API keys
- [ ] Auth checks exist on every new endpoint/route
- [ ] Token validation uses constant-time comparison

## Data Exposure
- [ ] No secrets logged to stdout/stderr/files
- [ ] Error messages don't leak internal paths or stack traces to users
- [ ] Sensitive fields excluded from serialization/API responses

## Dependencies
- [ ] No new dependencies with known CVEs
- [ ] No pinning to vulnerable versions
- [ ] Import paths match expected packages (no typosquatting)

## Crypto & Storage
- [ ] No custom crypto implementations
- [ ] Passwords hashed with bcrypt/scrypt/argon2, not MD5/SHA
- [ ] Temp files cleaned up, no sensitive data in /tmp without restricted perms
```
- **Scope:** All kipi instances via `kipi update`

### Change 2: Architecture Review Checklist
- **What:** Markdown checklist of architecture review items
- **Where:** `plugins/kipi-core/skills/adversarial-review/references/architecture-checklist.md`
- **Why:** Claude over-engineers or picks wrong patterns without a reference. Fixed checklist prevents scope creep.
- **Exact change:**
```markdown
# Architecture Review Checklist

Evaluate the git diff against each item. Report PASS, FAIL (with line ref), or N/A.

## Separation of Concerns
- [ ] New code doesn't mix I/O with business logic
- [ ] No God functions (>50 lines or >3 responsibilities)
- [ ] Side effects are isolated and explicit (no hidden state mutation)

## API & Interface Design
- [ ] Public interfaces are minimal (no internal details exposed)
- [ ] Breaking changes to existing interfaces are flagged
- [ ] Return types are consistent (no mixed error handling patterns)

## Error Handling
- [ ] Errors propagate, not swallowed silently
- [ ] Error types are specific (no bare `except:` or `catch(e)`)
- [ ] Retry logic has backoff and max attempts

## State Management
- [ ] No global mutable state introduced
- [ ] Shared state has clear ownership and lifecycle
- [ ] Config reads happen at startup, not scattered through code

## Maintainability
- [ ] No copy-pasted blocks (>10 lines identical = extract)
- [ ] File placement follows project conventions (folder-structure rule)
- [ ] Naming is self-documenting (no single-letter vars outside loops)
```
- **Scope:** All kipi instances via `kipi update`

### Change 3: Performance Review Checklist
- **What:** Markdown checklist of performance review items
- **Where:** `plugins/kipi-core/skills/adversarial-review/references/performance-checklist.md`
- **Why:** Performance issues are caught inconsistently. Fixed checklist ensures systematic coverage.
- **Exact change:**
```markdown
# Performance Review Checklist

Evaluate the git diff against each item. Report PASS, FAIL (with line ref), or N/A.

## Algorithmic Complexity
- [ ] No O(n^2) or worse in hot paths (nested loops over collections)
- [ ] Large collection operations use appropriate data structures (set/map vs list)
- [ ] Pagination or streaming for unbounded result sets

## I/O & Network
- [ ] No synchronous blocking calls in async contexts
- [ ] Database queries use indexes (no full table scans on large tables)
- [ ] HTTP calls have timeouts set
- [ ] No N+1 query patterns (loop of individual fetches vs batch)

## Memory
- [ ] Large objects not held in memory longer than needed
- [ ] No unbounded caches or growing lists without limits
- [ ] File reads use streaming for files that could be large

## Concurrency
- [ ] Shared resources have proper locking or are lock-free
- [ ] No race conditions in read-modify-write sequences
- [ ] Thread/worker pool sizes are bounded

## Build & Bundle
- [ ] No large dependencies added for small features
- [ ] Static assets are appropriately sized (images, fonts)
- [ ] No debug/dev-only code left in production paths
```
- **Scope:** All kipi instances via `kipi update`

### Change 4: Coordinator SKILL.md
- **What:** Skill definition that orchestrates 3 parallel review agents, collects findings, prioritizes, applies fixes, runs tests, and commits
- **Where:** `plugins/kipi-core/skills/adversarial-review/SKILL.md`
- **Why:** Replaces the ad-hoc Codex-dependent review workflow with a local, deterministic, parallel skill. Addresses the #1 pattern suggestion from the usage report.
- **Exact change:**
```markdown
---
name: adversarial-review
description: Parallel adversarial code review. Spawns 3 agents (security, architecture, performance) against a git diff, collects findings, prioritizes, fixes HIGH/MEDIUM, runs tests, commits.
---

# Adversarial Review Skill

Run a structured adversarial review of code changes. No external API dependency.

## Trigger

Invoke when the founder says "review", "adversarial review", "code review",
or "check this code." Also invoke via `/q-review`.

## Input

By default, review staged + unstaged changes (`git diff HEAD`).
If the founder specifies a branch or commit range, use that instead.

## Execution

### Phase 1: Collect the diff

Run `git diff HEAD` (or the specified range). If the diff is empty, tell the
founder and stop. Save the diff to a temp variable -- do not hold full file
contents, only the diff.

### Phase 2: Parallel review (3 agents)

Spawn 3 Agent tool calls in parallel. Each agent gets:
- The git diff text
- Its review checklist (from `references/`)
- Instructions to output structured JSON findings

**Agent 1 -- Security:**
- Read `references/security-checklist.md`
- Prompt: "Review this diff against the security checklist. For each checklist
  item, report PASS, FAIL, or N/A. For FAIL, include the file, line range,
  severity (HIGH/MEDIUM/LOW), and a one-sentence explanation. Output as JSON
  array of findings."

**Agent 2 -- Architecture:**
- Read `references/architecture-checklist.md`
- Prompt: Same structure as Agent 1, using architecture checklist.

**Agent 3 -- Performance:**
- Read `references/performance-checklist.md`
- Prompt: Same structure as Agent 1, using performance checklist.

### Phase 3: Collect and deduplicate

Merge all findings into one list. Deduplicate by file+line range (if two
agents flag the same line, keep the higher severity). Sort by severity
(HIGH first, then MEDIUM, then LOW).

### Phase 4: Report

Present findings to the founder as a table:

| # | Dimension | Severity | File | Lines | Issue | Fix? |
|---|-----------|----------|------|-------|-------|------|

Ask: "Fix HIGH and MEDIUM issues? (y/n/select)"

### Phase 5: Fix (if approved)

For each HIGH and MEDIUM finding:
1. Read the target file
2. Apply the fix
3. Run tests (`npm test`, `pytest`, `cargo test` -- detect from project)
4. If tests pass, stage the file

After all fixes: commit with message summarizing what was fixed.

### Phase 6: Re-review (optional)

If the founder asks, re-run Phase 2-4 on the new diff to verify fixes
didn't introduce new issues.

## Model Allocation

- Phase 2 agents: Sonnet (analysis, not creative work)
- Phase 3-5 coordinator: Opus (judgment calls on dedup and fix quality)

## Token Budget

- Phase 2: ~30K per agent (90K total for parallel phase)
- Phase 3-5: ~20K for coordination and fixes
- Total budget: ~110K tokens

## Fallback

If any agent fails or times out:
- Log which dimension failed
- Continue with the other two
- Note the gap in the report table
```
- **Scope:** All kipi instances via `kipi update`

## 4. Change Interaction Matrix
| Change A | Change B | Interaction | Resolution |
|----------|----------|-------------|------------|
| Change 1 (security checklist) | Change 4 (SKILL.md) | SKILL.md references `references/security-checklist.md` | File must exist before skill runs. Both ship together. |
| Change 2 (architecture checklist) | Change 4 (SKILL.md) | SKILL.md references `references/architecture-checklist.md` | Same as above. |
| Change 3 (performance checklist) | Change 4 (SKILL.md) | SKILL.md references `references/performance-checklist.md` | Same as above. |
| Change 1 | Change 2 | No interaction | Independent files, no conflict. |
| Change 1 | Change 3 | No interaction | Independent files, no conflict. |
| Change 2 | Change 3 | No interaction | Independent files, no conflict. |

## 5. Files Modified
| File | Change Type | Lines Added | Lines Removed |
|------|-------------|-------------|---------------|
| `plugins/kipi-core/skills/adversarial-review/SKILL.md` | New file | ~90 | 0 |
| `plugins/kipi-core/skills/adversarial-review/references/security-checklist.md` | New file | ~30 | 0 |
| `plugins/kipi-core/skills/adversarial-review/references/architecture-checklist.md` | New file | ~30 | 0 |
| `plugins/kipi-core/skills/adversarial-review/references/performance-checklist.md` | New file | ~30 | 0 |

## 6. Test Cases
Tag each: DET (deterministic), BEH (behavioral), INT (integration)

### [Change 1-3] Checklist Tests
| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 1 | DET | Checklist files exist | `ls plugins/kipi-core/skills/adversarial-review/references/` | 3 .md files | All three checklist files present |
| 2 | DET | Checklists have checklist items | `grep -c '\- \[ \]' <file>` for each | >= 5 items per file | Each checklist has at least 5 review items |
| 3 | DET | No hardcoded secrets in checklists | `grep -i 'password\|token\|secret' <file>` | Matches are only in "check for" context | No actual secrets embedded |

### [Change 4] SKILL.md Tests
| # | Type | Scenario | Input | Expected | Pass Criteria |
|---|------|----------|-------|----------|---------------|
| 4 | DET | SKILL.md has valid frontmatter | Parse YAML frontmatter | `name: adversarial-review`, `description` present | Both fields non-empty |
| 5 | BEH | Skill triggers on "review this code" | Founder says "review this code" | Skill activates, runs git diff | Diff collected and 3 agents spawned |
| 6 | BEH | Empty diff handled | No staged/unstaged changes | Skill reports "no changes to review" and stops | No agents spawned, clean exit |
| 7 | BEH | Agent failure fallback | One agent times out | Other two complete, report notes gap | Report shows 2/3 dimensions with gap note |
| 8 | INT | Full review cycle | Diff with a known SQL injection + N+1 query | Security agent flags SQL injection (HIGH), perf agent flags N+1 (MEDIUM) | Both findings appear in report, correct severity |
| 9 | BEH | Negative: no false positives on clean code | Diff adding a simple utility function | All items PASS or N/A | Zero FAIL findings |

## 7. Regression Tests
| # | What to Verify | How to Verify | Pass Criteria |
|---|----------------|---------------|---------------|
| 1 | Existing skills unaffected | Run `kipi check` after adding new skill directory | Validation passes, no errors about existing skills |
| 2 | `kipi update` propagates new skill | Run `kipi update --dry` | New skill directory appears in diff for all instances |
| 3 | Codex skill still works | Run a Codex task after adversarial-review is installed | Codex operates normally, no conflicts |

## 8. Rollback Plan
| Change | Rollback Steps | Risk |
|--------|----------------|------|
| All (Changes 1-4) | Delete `plugins/kipi-core/skills/adversarial-review/` directory. Run `kipi update` to remove from instances. | Zero risk. New directory, no existing files modified. No other skill depends on this. |

## 9. Change Review Checklist
| Check | Status | Notes |
|-------|--------|-------|
| Changes are additive (no breaking removals) | PASS | All new files, nothing modified |
| No conflicts with existing enforced rules | PASS | Skill follows folder-structure conventions |
| No hardcoded secrets | PASS | Checklists contain review items, not secrets |
| Propagation path verified (kipi update, global, etc.) | PENDING | `kipi update --dry` needed post-implementation |
| Exit codes preserved (hooks exit 0) | N/A | No hooks modified |
| AUDHD-friendly (no pressure/shame language added) | PASS | Report is a table with choices, not commands |
| Test coverage for every change | PASS | 9 test cases across all 4 changes |

## 10. Success Metrics
| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Adversarial review sessions using Codex | 8+ per 15 days | 0 | Count Codex calls for review tasks in usage reports |
| Wrong-approach friction events (review-related) | 29 per 15 days | <5 | Usage report friction analysis |
| Time to complete a full code review | ~30 min (manual scoping + Codex waits) | <10 min (parallel agents) | Session timestamps |
| Review dimension coverage | Inconsistent (varies per session) | 100% (all 3 checklists every time) | Audit finding reports |

## 11. Implementation Order
1. Create directory structure: `plugins/kipi-core/skills/adversarial-review/references/`
2. Write security-checklist.md (Change 1) -- no dependencies
3. Write architecture-checklist.md (Change 2) -- no dependencies
4. Write performance-checklist.md (Change 3) -- no dependencies
5. Write SKILL.md coordinator (Change 4) -- depends on 1-3 existing
6. Test: run `kipi check` to validate structure
7. Test: run the skill against a known-bad diff
8. Run `kipi update --dry` to verify propagation
9. Run `kipi update` to push to all instances

## 12. Open Questions
| Question | Owner | Deadline | Resolution |
|----------|-------|----------|------------|
| Should the skill auto-trigger on `git commit` or only on explicit invocation? | Assaf | 2026-04-16 | Start with explicit only. Add hook later if wanted. |
| Should LOW severity findings be shown or hidden by default? | Assaf | 2026-04-16 | Show all, let founder filter. |
| Add project-specific checklist extensions (e.g., KTLYST-specific security items)? | Assaf | 2026-04-23 | Defer to v2. Keep checklists generic for now. |

## 13. Wiring Checklist (MANDATORY)
| Check | Status | Notes |
|-------|--------|-------|
| PRD file saved to `q-system/output/prd-adversarial-review-2026-04-09.md` | DONE | This file |
| All code/config changes implemented and tested | PENDING | Implementation not started |
| New files listed in folder-structure rule (if any created) | PENDING | Need to add `adversarial-review/` to folder-structure.md skill listing |
| New conventions referenced in root CLAUDE.md (if any added) | N/A | No new conventions |
| New rules referenced in folder-structure rules list (if any created) | N/A | No new rules files |
| Memory entry saved for decisions/patterns worth recalling | PENDING | Save after implementation |
| `kipi update --dry` confirms propagation diff (if skeleton files changed) | PENDING | Run after implementation |
| `kipi update` run to push to all instances (if skeleton files changed) | PENDING | Run after dry run confirms |
| PRD Status field updated to "Done" | PENDING | Update after all checks pass |
