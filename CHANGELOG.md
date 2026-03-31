# Changelog

## v0.0.1 — Plugin Architecture Rewrite

Complete rewrite from standalone Claude Code project to proper Claude Code plugin.

### Plugin structure
- Added `.claude-plugin/plugin.json` manifest and `marketplace.json`
- Install via `/plugin marketplace add assafkip/kipi-system` + `/plugin install kipi-system@kipi`
- Removed `.claude/` directory entirely (rules, settings, skills all moved)

### Skills (2 → 34)
- Moved from `.claude/skills/` to top-level `skills/`
- 20 user-invokable commands (`/q-morning`, `/q-debrief`, `/q-plan`, `/q-research`, etc.)
- 14 agent skills — behavioral rules (voice, AUDHD, identity, modes) now delivered as auto-loading skills with `user-invocable: false` frontmatter, replacing `.claude/rules/`
- Removed generic coding skills (security, coding-standards, python-testing, typescript-testing) — these belong in user's global config, not a domain plugin
- Removed `/q-migrate` — replaced with standalone shell script

### MCP server (kipi-mcp/)
- New Python MCP server with 20 modules and 466 tests
- 55 tools: logging, loops, validation, linting, scoring, schema generation, backup/export/import
- 6 resources: `kipi://paths`, `kipi://status`, `kipi://instances`, `kipi://loops/open`, `kipi://loops/stats`, `kipi://backups`
- Removed `kipi_guide` tool and `guide_loader.py` — third-party marketing guides were vendored by mistake
- Removed `kipi_migrate` tool and `migrator.py` — migration handled outside the plugin
- Renamed `ktlyst_*` tools to `kipi_*` (8 tools)

### Instance data model
- Instance data (positioning, relationships, voice) lives outside the plugin at `~/.claude/plugins/data/`
- `active-instance` file in plugin data dir selects which instance to use
- Sync hook ensures instance data works across install methods (inline, marketplace, local)
- `/q-setup` creates instances interactively

### External MCP servers
- Removed gmail, google-calendar, apify, notion configs from `.mcp.json` — user installs these separately
- Plugin only bundles its own `kipi` MCP server
- README documents required servers with install commands

### Hooks
- Moved from `.claude/settings.json` to `hooks/hooks.json` (plugin format)
- SessionStart: git pull, uv sync, data sync across plugin variants, session context loading
- PreToolUse: token-guard (runaway detection)

### Documentation
- Consolidated ARCHITECTURE.md, CONTRIBUTE.md, INSTANCE-SETUP.md, SETUP.md, UPDATE.md into README.md
- Removed `guides/` directory (32 vendored third-party marketing methodology guides)

### Paths
- `KipiPaths` reads `KIPI_PLUGIN_DATA` (mapped from `CLAUDE_PLUGIN_DATA`) and `active-instance` file
- Removed `.kipi-instance` file and `KIPI_HOME` env var fallback
- All paths resolve through `kipi://paths` MCP resource
