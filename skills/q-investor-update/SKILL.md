---
description: "Draft milestone-triggered investor update emails"
---

# /q-investor-update — Investor update email

Milestone-triggered investor update email. Drafts a concise, high-signal update for the full VC list. Not a newsletter — a founder update that makes VCs feel like insiders.

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
1. `{data_dir}/my-project/relationships.md` — VC contacts tagged "quarterly update list"
2. `{data_dir}/my-project/progress.md` — recent milestones since last update
3. `{data_dir}/memory/morning-state.md` — Investor Update Tracker (last update date)

## Integration checks

| Integration | Used for | If unavailable |
|------------|---------|----------------|
| Notion | Investor Pipeline DB | Work from local relationships.md |

## Process

1. **Pull current state:**
   - Read Investor Pipeline DB for all VCs with status != Passed
   - Read relationships.md for "quarterly update list" contacts
   - Read progress.md for recent milestones
   - Read morning-state.md Investor Update Tracker for last update date

2. **Identify what's new since last update:**
   - New design partners or LOIs
   - Product milestones (features shipped, demo improvements)
   - New thesis endorsers or CISO validations
   - Notable conversations (only if person would be comfortable being named)
   - Content/community traction (if meaningful)
   - Team updates, upcoming events

3. **Draft the update email:**
   - Plain text. No HTML. Founder-to-investor voice.
   - Under 300 words. VCs scan, they don't read.
   - Structure: Subject → Highlight (1 sentence) → Product (2-3 bullets) → Traction → What's Next → Ask (optional, specific, low-effort)
   - Lead with strongest proof point, not vision
   - Numbers over adjectives: "3 design partners" not "growing traction"

4. **Generate variants:**
   - Active pipeline VCs: include tailored ASK per portfolio
   - Thesis nod VCs: standard update, no ASK
   - Warm connectors: specific intro ASK if relevant
   - BCC list: standard update, generic sign-off

5. **Save and track:**
   - Save to `{state_dir}/output/investor-updates/investor-update-YYYY-MM-DD.md`
   - Update morning-state.md Investor Update Tracker
   - Create Notion Action: "Review and send investor update"

## Output rules

- Apply `founder-voice` rule — mandatory
- Apply `audhd-executive-function` rule if enabled
- No "excited to announce" or "thrilled to share" — just state facts
- Personalize ASK per VC based on portfolio/network (3-4 variants max)
