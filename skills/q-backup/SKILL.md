---
description: "Backup and restore system data — create, list, restore, or export archives"
---

# /q-backup — Backup & Restore

Manage system backups. Archives include all databases (metrics, harvest, loops), canonical files, memory, config, and voice data.

## Commands

Ask the user what they want to do:

### "backup" or "create" (default)
1. Call `kipi_backup` MCP tool.
2. Show: "Backup created: {path} ({size_bytes} bytes, {files_count} files)"
3. Call `kipi://backups` resource to show total backup count.
4. Note: Auto-backups run every morning during /q-morning. Manual backups are in addition to those.

### "list"
1. Call `kipi://backups` MCP resource.
2. Show table: name, size, date for each backup.
3. Note: System keeps 5 most recent auto-backups (rotated daily).

### "restore"
1. Call `kipi://backups` resource to list available archives.
2. Ask: "Which backup do you want to restore from?" (show numbered list)
3. Call `kipi_import` with the chosen archive path and `dry_run=true` first.
4. Show what would be restored: "{N} files would be written to {paths}"
5. Ask: "This will overwrite your current data. Proceed? (yes/no)"
6. If yes: call `kipi_import` with `dry_run=false`.
7. Show: "Restored {N} files from {archive}. Restart the MCP server for changes to take effect."

### "export" (for moving to another machine)
1. Ask: "Where should I save the export?" (suggest Desktop or Downloads)
2. Call `kipi_export` with the chosen output path.
3. Show: "Export saved to {path}. To import on another machine: run /q-backup restore and point to this file."

## Backup Location

Auto-backups are saved to: `{instance_dir}/output/kipi-backup-{timestamp}.tar.gz`

To find your instance directory: call `kipi://paths` MCP resource and look for `config_dir`.

## What's Included

- **metrics.db** — content performance, outreach logs, behavioral signals, daily metrics, A/B tests
- **harvest.db** — harvest runs, source cursors, Apify budget, agent metrics, Notion queue
- **system.db** — open loops, session handoffs
- **canonical/** — talk tracks, objections, positioning, market intelligence, decisions, discovery
- **memory/** — working notes, weekly insights, monthly patterns, graph.jsonl
- **my-project/** — founder profile, relationships, lead sources, budget qualifiers, Notion IDs
- **voice/** — voice DNA, writing samples (shared across instances)
- **marketing/** — content themes, templates, brand voice

## What's NOT Included

- Backup archives themselves (avoids recursive backups)
- Harvest records older than 7 days (already cleaned up)

## Recovery Scenarios

| Problem | Solution |
|---------|----------|
| Database corrupted | `/q-backup restore` from latest backup |
| Accidentally deleted canonical file | `/q-backup restore` then copy the file |
| Moving to new laptop | `/q-backup export` then `/q-backup restore` on new machine |
| Want to undo today's changes | `/q-backup restore` from yesterday's auto-backup |

## MCP Tools Used

`kipi_backup`, `kipi_export`, `kipi_import`, `kipi://backups`
