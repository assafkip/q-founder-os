---
description: "Marketing pipeline snapshot — content state across channels"
---

# /q-market-status — Marketing snapshot

Quick snapshot of marketing pipeline, content cadence, asset health, and recent publishes.

## Setup guard

**FIRST:** Read `{config_dir}/founder-profile.md`. If it contains `{{SETUP_NEEDED}}`, STOP and tell the user:

> This system hasn't been configured yet. Run `/q-setup` first.

Do not proceed.

## Path resolution

Read the `kipi://paths` MCP resource to get resolved directories. Key directories:
- **Config** (`{config_dir}`): founder-profile, enabled-integrations, canonical/, voice/, marketing/
- **Data** (`{data_dir}`): my-project/, memory/
- **State** (`{state_dir}`): output/, bus/
- **Repo**: system code (agents, templates, steps) stays in the git repo

## Process

1. Read `{data_dir}/memory/marketing-state.md`
2. Pull Content Pipeline DB counts from Notion (if available)
3. Output snapshot:
   - Pipeline: Ideas / Drafted / Reviewed / Published / Killed counts
   - This week's cadence: Signals progress, TL posts progress, Medium status
   - Asset health: current vs stale count, list stale if any
   - Gamma decks: name, status, URL
   - Recent publishes: last 5 from publish log
   - Stale drafts: list or "None"

## Output rules

- Keep it short — this is a status check, not a report
- Apply `audhd-executive-function` rule if enabled
