# Q Entrepreneur OS

@q-system/CLAUDE.md

## Project Structure
- `plugins/` - Plugin groups: kipi-core (every instance), kipi-ops (GTM), kipi-design (UI)
- `.claude/agents/` - Custom agent definitions (preflight, data-ingest, synthesizer, etc.)
- `.claude/rules/` - Path-scoped instruction files
- `q-system/` - Core OS (canonical/, marketing/, methodology/, output/, my-project/, memory/)

## Conventions
- Never produce fluff - every sentence must carry information or enable action
- Mark unvalidated claims with `{{UNVALIDATED}}` or `{{NEEDS_PROOF}}`
- All written output goes through the founder voice skill
- All actionable output follows AUDHD executive function rules (if enabled)
- No filler phrases ("leverage," "innovative," "cutting-edge," "game-changing")
- When something fails because an LLM misinterpreted instructions, the fix must be a deterministic script or code change
- For any task involving more than a single file edit, state the planned approach and wait for OK
- When fixing identified issues, fix exactly what was flagged. No scope expansion.
- Never read or search files outside the current project directory without stating which directory and why
- All product/system changes use the PRD template at `q-system/marketing/templates/prd.md`

## Commands
- `/q-morning` - Full morning briefing (9-phase agent pipeline)
- `/q-debrief` - Post-conversation extraction (highest priority)
- `/q-calibrate` - Update canonical files
- `/q-create` - Generate specific output (talk tracks, emails, slides, decks)
- `/q-plan` - Review and prioritize actions
- `/q-engage` - Social engagement mode
- `/q-market-*` - Marketing system commands
- `/q-draft` - Ad-hoc output generation
- `/q-wrap` - Evening health check
- `/q-handoff` - Session continuity
- `/q-research` - Anti-hallucination research mode
- `/wiring-check` - End-of-task gate: verify every change is connected end-to-end (plugins, hooks, MCP tools, agents, bus, canonical, rules, skeleton propagation)

## Definition of Done: Fully Wired (ENFORCED)

No implementation task is "done" until every change is wired end-to-end. This
repo's value is that its parts compose; a new skill/command/hook/agent that
isn't connected to the rest is dead weight.

Before declaring done, confirm (evidence required, not assumed):
- Any new skill has a trigger (auto-invoke rule, command, or discoverable description)
- Any new slash command is registered (listed in CLAUDE.md commands and/or `plugin.json`)
- Any new hook script is referenced from `settings.json`, is executable, and uses the correct exit-code contract
- Any new MCP tool is registered in the server and appears in the plugin description
- Any new agent has a current (non-deprecated) model ID, explicit tool allowlist, and is invoked by the orchestrator
- Any new bus file has both a producer and a consumer, and a schema in `agent-pipeline/schemas/`
- Any new canonical file is in `ripple-graph.json` and the digest is regenerated
- Any new rule is auto-loaded or imported via `@` in CLAUDE.md
- Any new Python harness has a caller and resolves QROOT correctly
- Skeleton-vs-instance placement is correct; `kipi update --dry` confirms propagation if this is `kipi-system`

When finished, run `/wiring-check` and produce the WIRING REPORT. "I think it
works" is not done. "I ran X, got Y" is done.

## Build and Test
- Build daily schedule: `python3 q-system/marketing/templates/build-schedule.py <json> <html>`
- Audit morning routine: `python3 q-system/.q-system/audit-morning.py q-system/output/morning-log-YYYY-MM-DD.json`
- Audit instruction budget: `python3 q-system/.q-system/scripts/instruction-budget-audit.py`
- Develop with plugins: `kipi dev` (loads all 3 plugin groups)
