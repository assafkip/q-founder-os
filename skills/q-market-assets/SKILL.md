---
description: "Refresh marketing assets (bios, stats, proof points, decks)"
---

# /q-market-assets — Asset refresh

Refresh all reusable marketing assets from canonical files. Flag stale items. Flag Gamma decks needing re-generation.

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
1. `{data_dir}/memory/marketing-state.md` — Asset Freshness table
2. `{config_dir}/marketing/assets/` — all asset files (boilerplate, bios, stats, proof points, competitive one-liners)

## Process

1. Read marketing-state.md Asset Freshness table
2. For each asset, check source file modification dates:
   - Read source file content and compare against asset content
   - If source has material changes since last refresh → mark stale
3. For stale assets: regenerate from current canonical sources
4. Check Gamma Deck Tracker: compare canonical file dates against deck generation dates
   - If positioning changes since deck generation → flag deck for re-generation
   - Optionally: generate new Gamma deck via Gamma MCP
5. Update marketing-state.md with new refresh dates
6. Update Asset Library DB in Notion

## Output rules

- Report: refreshed assets, current assets, Gamma deck status
- Apply `founder-voice` rule to any regenerated asset content
