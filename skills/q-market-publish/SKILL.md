---
description: "Mark content as published and update tracking state"
---

# /q-market-publish — Mark content published

Mark content as published. Updates Content Pipeline DB, Editorial Calendar, and marketing state.

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

1. Read the content file specified by the user
2. Verify guardrails have passed (check Content Pipeline DB or re-run `/q-market-review` if needed)
3. Update Content Pipeline DB: Status → Published, Published Date → today
4. Update Editorial Calendar DB if applicable: Status → Published
5. Update `{data_dir}/memory/marketing-state.md`:
   - Add to Publish Log
   - Update Content Cadence for current week
   - Increment Pipeline Summary counts

## Output rules

- Confirmation with publish details
- No lengthy summaries — just state what was updated
