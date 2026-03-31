---
description: "Marketing system — content guardrails, brand voice, theme rotation, tool preferences"
user-invocable: false
paths:
  - "**/marketing/**"
  - "**/content-*.md"
---

# Marketing System

## Content Rules

- All content must pass `marketing/content-guardrails.md` before publishing
- Voice rules per channel in `marketing/brand-voice.md`
- Themes rotate on a configurable cycle in `marketing/content-themes.md`
- Reusable assets in `marketing/assets/` (boilerplate, bios, stats, proof points, competitive one-liners)
- State tracked in `{data_dir}/memory/marketing-state.md`

## Tool Preferences

- Use project-scoped Notion API server for CRM (not workspace-wide plugins)
- Use Apify for data scraping, Chrome for interactive/DMs only
- Gamma for decks and one-pagers (if configured)
- NotebookLM for research-grounded content (if configured)
