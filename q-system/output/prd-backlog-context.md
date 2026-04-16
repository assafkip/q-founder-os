# PRD Backlog Context (saved before context clear)

**Date:** 2026-04-09
**Purpose:** Context for building PRDs for deferred items from usage report analysis

## Source Data
- Claude Code Insights report: `~/.claude/usage-data/report.html`
- Implemented PRD: `q-system/output/prd-usage-report-fixes-2026-04-09.md`
- PRD template: `q-system/marketing/templates/prd.md`

## Deferred Items (ranked by impact)

### 1. Parallel Adversarial Review Skill (RECOMMENDED NEXT)
- **Source:** Report's #1 pattern suggestion + horizon section
- **Problem:** 29 wrong-approach friction events. Daily Codex rate limits and auth failures block the adversarial review workflow (8+ sessions). Claude over-engineers, picks wrong tools, or misscopes reviews.
- **Report quote:** "Adversarial review is your most repeated workflow. Codify your adversarial code review into a Custom Skill to eliminate Codex rate limit issues and scope failures."
- **Report quote (horizon):** "Instead of depending on an external API, Claude Code can spawn parallel sub-agents -- one to audit security, one for architecture, one for performance -- then a coordinator agent triages findings, applies fixes, runs tests, and commits."
- **Implementation path:** Define 3 review checklists as .md files (security, architecture, performance). Write coordinator skill that spawns 3 parallel agents against git diff, collects findings, prioritizes, fixes HIGH/MEDIUM, runs tests, commits. Replaces Codex dependency entirely.
- **Effort:** Medium
- **Dependencies:** None. Can start immediately.

### 2. Codex/Exa External Tool Brittleness
- **Source:** Report's #3 friction category
- **Problem:** 5 tool failures + repeated auth debugging across sessions. Codex auth caching issues, Exa MCP not recognized, browser automation timeouts.
- **Report quote:** "You rely heavily on external tools like Codex, Exa MCP, and browser automation that frequently fail due to auth issues, rate limits, or misconfiguration -- and Claude doesn't handle these failures gracefully."
- **Implementation path:** Per-tool preflight check in session-context.sh or new preflight hook. Fallback paths (if Exa fails, try WebSearch; if Codex fails, use local review skill). Capture working tool configs.
- **Effort:** Medium
- **Dependencies:** Partially addressed by instance echo (Change 4 of implemented PRD).

### 3. File-Too-Large Error Reduction
- **Source:** Report tool errors (27 file-too-large events)
- **Problem:** Claude tries to read large files without offset/limit, gets truncated or errors out. 27 events in 15 days.
- **Implementation path:** Audit which files Claude reads whole (grep for Read tool calls in logs). Add CLAUDE.md guidance for known large files. Add offset/limit patterns.
- **Effort:** Low (mechanical)
- **Dependencies:** None.

### 4. Self-Healing Pipeline with Test Gates
- **Source:** Report horizon section
- **Problem:** Value-drop and KTLYST pipelines require extensive manual iteration when extraction, imports, or dedup logic breaks.
- **Report quote:** "Claude Code can autonomously run a pipeline, catch failures, diagnose root causes, and re-run against test assertions in a loop."
- **Implementation path:** Build test assertion infrastructure per-pipeline. Use Agent tool to spawn sub-agent that runs pipeline, captures stderr, applies fixes, re-runs until assertions pass.
- **Effort:** High
- **Dependencies:** Requires test suites that don't exist yet.

### 5. Autonomous Morning Orchestrator
- **Source:** Report horizon section
- **Problem:** Morning pipeline breaks when MCP tools are missing, Notion DB IDs go stale, or file paths reference yesterday's bus directory. ~10 sessions spent debugging.
- **Report quote:** "An autonomous orchestrator agent can preflight all dependencies, run each stage with fallback logic, and surface a single dashboard summary."
- **Implementation path:** CLAUDE.md-driven morning routine with Bash preflight checks, Agent tool per-phase, halt-on-failure rules, Notion verification.
- **Effort:** High
- **Dependencies:** Depends on #2 (tool brittleness).

### 6. Headless Morning Pipeline
- **Source:** Report features section + horizon
- **Problem:** Same as #5 but lighter scope. Morning pipeline kicked off manually each session.
- **Implementation path:** `claude -p` wrapper script with `--allowedTools` for morning routine.
- **Effort:** Medium
- **Dependencies:** Depends on #2.

## Key Report Stats (for PRD Problem sections)
- 3,000 messages, 169 sessions, 15 days (2026-03-26 to 2026-04-09)
- 29 wrong-approach friction events (highest category)
- 16 misunderstood-request events
- 15 buggy-code events
- 5 excessive-changes events
- 92 "User Rejected" tool errors
- 39 "File Not Found" errors
- 27 "File Too Large" errors
- 87% achievement rate
- Adversarial review: 8+ sessions, daily workflow
- Morning pipeline: ~10 sessions
- Codex rate limits/auth: blocked across multiple sessions

## Existing System Context
- PRD template: `q-system/marketing/templates/prd.md` (13 sections, mandatory wiring checklist)
- Folder structure rule: PRDs go to `q-system/output/prd-<slug>-YYYY-MM-DD.md`
- Skeleton CLAUDE.md: already has deterministic-first, approach gate, scope creep, directory boundary rules
- Global CLAUDE.md: already has brief dismissal, casual tone rules
- Instance echo: session-context.sh now prints instance name at session start
- Validator: validate-separation.py skips archived instances and handles website correctly
