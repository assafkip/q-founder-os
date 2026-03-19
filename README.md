# The Kipi System

**Your AI operating system for relationship-driven work.**

You know who you need to follow up with. You just don't remember when. You know what that person said last month that mattered. You just can't find it. You know exactly what email to write. You just haven't written it.

The Kipi System is the part of your brain that remembers everything, connects everything, and turns everything into the next action. It runs on Claude Code. It learns from every conversation you have. It produces your entire day as a single file: every action pre-written, every follow-up drafted, every open thread tracked.

You copy, paste, check the box, move on.

---

## What happens when you run `/q-morning`

The system pulls from your calendar, email, CRM, and social platforms. It reads every open loop. It checks what went cold. Then 25 agents run across 9 phases and produce a single HTML file:

- **Copy-paste actions sorted by friction.** 2-minute replies first, deep work later. Momentum builds before the hard stuff.
- **Every follow-up pre-written in your voice.** Not AI voice. YOUR voice. Fed from your writing samples, your word choices, your pet peeves.
- **Open loops with escalation.** Sent a DM 7 days ago with no reply? The system drafted the follow-up already. 14 days? It forces you to decide: send, park, or kill.
- **Meeting prep with context.** Who you're meeting, what you discussed last time, what they care about, suggested talking points.

You open the HTML. Start at the top. Work down. Done.

---

## Paste a conversation. Get your next 10 actions.

Had a call? Paste the transcript. The system extracts:
- What resonated (their exact words)
- What got pushback
- What you owe them
- New objections to prepare for

Then it routes each insight to the right file automatically. Your talk tracks update. Your relationship file updates. Your follow-up email is drafted and waiting in tomorrow's HTML.

After 50 conversations, the system knows your market better than you do. Because it remembers everything. You don't have to.

---

## Nothing gets forgotten

Every outbound action opens a loop. Every loop has a timer.

| Days open | What happens |
|-----------|-------------|
| 0-2 | Quiet. Listed in your dashboard. |
| 3-6 | Follow-up drafted. Shows in your action plan. |
| 7-13 | Flagged. Shows at the top. "This is going cold." |
| 14+ | Forced decision. Act now, park for later, or kill it. No more open loops draining mental energy. |

Loops auto-close when the system detects a response. Gmail reply? Closed. LinkedIn DM reply? Closed. Connection accepted? Closed. You don't track anything. The system tracks everything.

---

## How the agent pipeline works

> **Visual guides:** [Agent Pipeline Architecture](docs/diagrams/agent-pipeline-architecture.pdf) | [Daily Workflow](docs/diagrams/daily-workflow.pdf) | [Data Flow Architecture](docs/diagrams/data-flow-architecture.pdf)
>
> Interactive versions: [Pipeline](https://gamma.app/docs/ovum1angmf5mh1d) | [Workflow](https://gamma.app/docs/zn2h7mtj1kc0l9y) | [Data Flow](https://gamma.app/docs/923zj6f7zv4nzdq)

The morning routine is not a single prompt. It's 25 specialized agents organized into 9 phases. Each agent has one job. They communicate through JSON files in a shared bus/ directory, not through context. This keeps the main conversation light while the agents do heavy lifting in parallel.

**Phase 0: Preflight.** One agent checks that all tools are responding (calendar, email, CRM, browser). If anything is down, the pipeline halts before wasting tokens.

**Phase 1: Data Ingest.** Four agents run in parallel, each pulling from a different source: calendar events, email threads, CRM contacts and pipeline, and any external APIs you've configured. They write structured JSON to the bus.

**Phase 2: Analysis.** Two agents read the bus data and produce meeting prep and warm introduction matching. They run in parallel because neither depends on the other.

**Phase 3: Social.** Three agents run sequentially (browser automation needs one tab at a time). They scan LinkedIn posts, read DMs and connection accepts, and count your prospect pipeline by status.

**Phase 4: Content.** A signals agent finds today's relevant news and drafts posts. Then a value-routing agent matches signals to prospects, and a visual generation agent creates social cards and carousels. On brand post days, a personal brand agent drafts a separate post.

**Phase 5: Pipeline.** Four agents score prospect temperature, source new leads, draft overdue follow-ups, and review stale loops, all in parallel. Then an engagement hitlist agent (the most important one) reads everything and produces the copy-paste-ready action list.

**Phase 6: Compliance.** Two agents check all generated content against your positioning rules and audit your talk tracks for freshness.

**Phase 7: Synthesis.** One agent reads every bus file and produces the daily schedule JSON, following strict actionability rules: every item must be copy-paste ready, have a next physical action, an energy tag, and a time estimate.

**Phase 8: Build and Verify.** A build script converts the JSON to HTML. A visual verify agent opens it in the browser. An audit harness checks for skipped steps.

**Phase 9: Write-back.** Two agents push today's actions to your CRM and update your daily checklist pages.

The agents don't share context. They share files. This means you can run the same pipeline tomorrow with zero context carryover and get a fresh, accurate daily plan.

---

## Built for focus. Works for everyone.

The system was designed with ADHD in mind. Every design decision reduces cognitive load.

**No decisions.** The system picks who to contact, what to say, in what order, through which channel. You copy-paste and check boxes.

**No shame.** Never "overdue." Always "carried forward." Never "you forgot." Always "not yet done." Language matters when your brain punishes you for every dropped ball.

**Friction-ordered.** Quick wins first. Dopamine before discipline. The hardest task is never at the top.

**Effort-tracked.** "You sent 4 messages today" matters more than "nobody responded yet." Progress is actions taken, not outcomes received.

This isn't a feature toggle. It's how the whole system thinks. Even without ADHD, you get a system that eliminates decision fatigue and orders your day by what's easiest to start.

---

## A brain that compounds

Your biological brain forgets 90% of every conversation within a week. This one doesn't.

**Canonical memory.** Your positioning, your objections and the responses that worked, your competitive landscape, every relationship and what each person cares about. Every workflow reads from this memory. Every conversation updates it.

**Time-layered recall.** Working memory expires in 48 hours (you don't need yesterday's scratch notes). Weekly patterns roll up. Monthly insights persist. Session logs capture what happened and when, separate from current state. Like a real brain, it forgets what doesn't matter and strengthens what does.

**Connections across conversations.** A knowledge graph links people, companies, what they said, and how they relate. The insight from a conversation three weeks ago changes what the system suggests today. You didn't have to remember it. The brain did.

---

## Three commands to start

```bash
npm install -g @anthropic-ai/claude-code
git clone https://github.com/assafkip/kipi-system.git
cd kipi-system && claude
```

The system walks you through setup: who you are, what you're building, how you talk, who you know. Takes about 20 minutes. Then run `/q-morning` and see your first daily action plan.

---

## Architecture

```
kipi-system/
├── .q-system/
│   ├── agent-pipeline/
│   │   ├── agents/              # 25 agent prompt files (one per task)
│   │   │   ├── 00-preflight.md          # Verify all tools respond
│   │   │   ├── 01-calendar-pull.md      # Fetch calendar events
│   │   │   ├── 01-gmail-pull.md         # Fetch flagged emails
│   │   │   ├── 01-notion-pull.md        # Fetch CRM data
│   │   │   ├── 01-vc-pipeline-pull.md   # Fetch external pipeline (optional)
│   │   │   ├── 02-meeting-prep.md       # Prep today's meetings
│   │   │   ├── 02-warm-intro-match.md   # Cross-ref warm intro paths
│   │   │   ├── 03-linkedin-posts.md     # Scan LinkedIn feed
│   │   │   ├── 03-linkedin-dms.md       # Scan DMs + connection accepts
│   │   │   ├── 03-prospect-pipeline.md  # Count prospects by status
│   │   │   ├── 04-signals-content.md    # Find signals, draft posts
│   │   │   ├── 04-value-routing.md      # Match signals to prospects
│   │   │   ├── 04-post-visuals.md       # Generate visual assets
│   │   │   ├── 04-founder-brand-post.md # Weekly personal brand post
│   │   │   ├── 05-temperature-scoring.md # Score prospect engagement
│   │   │   ├── 05-lead-sourcing.md      # Run lead scraping
│   │   │   ├── 05-lead-sourcing-chrome.md # Browser fallback for leads
│   │   │   ├── 05-pipeline-followup.md  # Draft overdue follow-ups
│   │   │   ├── 05-loop-review.md        # Flag stale loops
│   │   │   ├── 05-engagement-hitlist.md # Copy-paste engagement actions
│   │   │   ├── 06-compliance-check.md   # Check content vs rules
│   │   │   ├── 06-positioning-check.md  # Audit talk tracks + objections
│   │   │   ├── 07-synthesize.md         # Produce daily schedule JSON
│   │   │   ├── 08-visual-verify.md      # Open HTML, check layout
│   │   │   ├── 09-notion-push.md        # Push actions to CRM
│   │   │   ├── 10-daily-checklists.md   # Update checklist pages
│   │   │   ├── _auto-fail-checklist.md  # Voice/content rules
│   │   │   └── _cadence-config.md       # Posting/outreach timing
│   │   └── bus/                 # Inter-agent JSON (per-date directories)
│   │
│   ├── steps/               # Monolithic step files (fallback)
│   ├── commands.md           # Full workflow definitions
│   ├── audit-morning.py      # Catches skipped steps
│   ├── bus-to-log.py         # Bridges bus/ files to morning log
│   ├── log-step.sh           # Flight recorder for every step
│   ├── loop-tracker.sh       # Opens, escalates, closes loops
│   ├── step-loader.sh        # Re-injects step requirements (EOP)
│   ├── tool-counter.sh       # Session tool call counter with thresholds
│   ├── diagnose-tools.sh     # Pre-command tool availability check
│   ├── verify-schedule.py    # Blocks HTML if sections missing
│   ├── token-guard.py        # Stops runaway token consumption
│   └── preflight.md          # Tool manifest and known issues
│
├── canonical/               # Source of truth (updates from every conversation)
│   ├── talk-tracks.md       # What to say, tested and tagged by audience
│   ├── objections.md        # Every pushback, with the response that worked
│   ├── market-intelligence.md  # Buyer language and competitive signals
│   ├── engagement-playbook.md  # Comment, DM, and connection request strategies
│   └── decisions.md         # Every decision with origin and rationale
│
├── my-project/              # Your specific context
│   ├── relationships.md     # Every person and what you owe them
│   ├── current-state.md     # What's true today (not vision)
│   └── progress.md          # Decision log and change history
│
├── memory/
│   ├── working/             # 48-hour scratch (auto-cleaned)
│   ├── weekly/              # 7-day patterns
│   ├── monthly/             # Persistent insights
│   ├── sessions/            # Per-session logs (what happened when)
│   └── graph.jsonl          # Who knows whom, who cares about what
│
├── marketing/               # Content templates, guardrails, voice matching
│   └── templates/
│       ├── build-schedule.sh          # JSON -> HTML build script
│       ├── daily-schedule-template.html # Actionability-optimized HTML template
│       └── schedule-data-schema.md    # JSON schema (with post visuals)
│
├── methodology/             # Debrief template, operating modes
│
├── tools/
│   └── osint-infra-mcp/     # WHOIS, DNS, Wayback Machine lookups
│
└── output/
    ├── daily-schedule-*.html # Your daily action plan
    └── morning-log-*.json   # Audit trail
```

---

## Commands

| What you want to do | Command |
|---------------------|---------|
| Generate your entire day | `/q-morning` |
| Process a conversation | `/q-debrief` (or just paste a transcript) |
| Draft a quick email or DM | `/q-draft` |
| Challenge your assumptions | `/q-challenge` |
| Identify research gaps | `/q-ask-first` |
| Get engagement actions for prospects' posts | `/q-engage` |
| Plan your week's content | `/q-market-plan` |
| Update your positioning from new info | `/q-calibrate` |
| Stress-test your positioning | `/q-reality-check` |
| Capture report screenshots | `/q-screenshots` |
| End-of-day health check | `/q-wrap` |
| Save context for next session | `/q-handoff` |

---

## Connects to

Works standalone with local files. Each integration adds capability:

| Tool | What it adds |
|------|-------------|
| Notion | CRM, pipeline, relationship tracking |
| Google Calendar | Meeting detection, auto-prep |
| Gmail | Email monitoring, loop auto-close on reply |
| Apify | LinkedIn/X/Reddit scraping for lead sourcing |
| Chrome | LinkedIn DMs, analytics, interactive browsing |
| Gamma | Social cards, carousels, presentation visuals |
| Slack | Notifications, approval workflows |
| Threat Intel MCP | VirusTotal, AbuseIPDB, OTX feeds for signal enrichment |
| OSINT Infra MCP | WHOIS, DNS, cert transparency, Wayback Machine lookups |

---

## The AI needs scaffolding too

The AI running this system has the same executive function problems you do.

Research calls it "Lost in the Middle" (Stanford, 2023). In long conversations, LLMs forget instructions from earlier in the context. They rush to produce output and skip boring middle steps. They self-report completion without verifying. They pattern-match from old sessions instead of reading current requirements.

So the system has guardrails for the AI, not just for you:

**Verification gate.** Before the HTML builds, a script checks the JSON output. Are pipeline follow-ups there? Does day-specific content exist? Are sections in the right order? If verification fails, the build is blocked. The AI can't bypass it.

**Echo of Prompt.** Before each step executes, a script re-injects that step's requirements fresh into context. Combats the attention drift that makes the AI "forget" what a step actually requires by the time it runs it.

**Token discipline.** A tool counter tracks every call and warns at 10, 30, and 50 thresholds. A token guard blocks runaway consumption. A diagnose script checks tool availability before expensive operations. The AI is forced to pause and ask: "Am I closer to the goal than 10 calls ago?"

**No self-authorized skipping.** The AI cannot decide on its own to skip a step. It must ask you first. The default is always run.

**Structured deliverables, not text summaries.** The system logs what was actually produced (number of follow-ups, number of copy blocks) not just "done."

---

## Who this is for

The pattern works anywhere humans manage concurrent relationships and compound knowledge:

**Sales teams** - accounts as relationships, proposals as loops, call notes as debriefs.

**Consultants** - clients as relationships, deliverables as loops, stakeholder meetings as debriefs.

**Lawyers** - case files as canonical state, filing deadlines as loops, client conversations as debriefs.

**Recruiters** - candidates as relationships, interview stages as loops, hiring manager conversations as debriefs.

**Account managers** - customers as relationships, renewals as loops, QBRs as debriefs.

Fork it and replace the canonical files with your domain.

---

## Compatibility

The Kipi System is built for **Claude Code** (CLI or Desktop Code tab). It uses sub-agents, bash execution, hooks, MCP servers, CLAUDE.md, and skills, all of which are Claude Code features.

**Claude Cowork** can run the core pipeline (sub-agents, local files, MCP, skills all work) but loses the bash scripts (HTML build, audit harness), hooks (automated guardrails), and CLAUDE.md auto-loading. About 80% of the system's value transfers. The daily HTML deliverable would need reworking.

**Claude.ai Projects** (web) cannot run the pipeline. No local file access, no sub-agents, no bash. You can upload the canonical files as project knowledge and use the debrief template manually, but the automation doesn't transfer.

---

## Security

- `.env`, credentials, and key files blocked from read/write
- PreToolUse hooks intercept dangerous operations at runtime
- No secrets in committed files
- `rm -rf`, `sudo`, `git push --force` denied by default
- Token guard prevents runaway consumption

---

## Origin

Built by [Assaf Kipnis](https://www.linkedin.com/in/assafkipnis/) to run [KTLYST Labs](https://ktlystlabs.com) operations. The production instance manages investor pipeline, prospect outreach, content publishing, and meeting prep for a pre-seed security startup. This repo is the general-purpose version.
