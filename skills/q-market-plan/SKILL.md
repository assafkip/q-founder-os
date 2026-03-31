---
description: "Weekly content planning from theme rotation and calendar"
---

# /q-market-plan — Weekly content planning

Weekly content planning. Reads theme rotation + editorial calendar. Generates this week's plan. Creates Notion entries.

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

## Preconditions

Read these files:
1. `{config_dir}/marketing/content-themes.md` — theme definitions and rotation
2. `{data_dir}/memory/marketing-state.md` — last week's publish log
3. `{data_dir}/my-project/progress.md` — recent debriefs for fresh insights
4. `{config_dir}/canonical/market-intelligence.md` — recent market signals and buyer language

## Integration checks

| Integration | Used for | If unavailable |
|------------|---------|----------------|
| Notion | Content Pipeline DB, Editorial Calendar DB | Output plan as markdown only |
| Google Calendar | Upcoming meetings for deck/one-pager queuing | Skip meeting prep items |

## Process

1. Read editorial calendar for this week's theme assignments
2. Read content-themes.md for theme details and canonical sources
3. Check marketing-state.md for last week's results (what landed, what was skipped)
4. Check recent debriefs for fresh insights that map to themes
5. Read market-intelligence.md — prioritize topics aligned with market signals from last 2 weeks. Use buyer language from Problem Language section.
6. Assign specific topics to each content slot:
   - Tue LinkedIn TL: [theme] + [angle from signals/debriefs/calendar]
   - Thu LinkedIn TL: [theme] + [angle]
   - Fri Medium: [theme] + [deep dive topic]
   - Sun Substack: [theme] + [newsletter angle]
7. Check calendar for upcoming meetings — auto-queue one-pagers and decks
8. Update editorial calendar with assigned topics
9. Create Notion Editorial Calendar DB entries
10. Create Notion Content Pipeline DB entries (Status: Idea)

## Output rules

- Apply `founder-voice` rule to topic descriptions
- Apply `audhd-executive-function` rule if enabled
- Run Monday or start of week
