# Test Obsidian Connection

## What This Tests
Verifies that Obsidian can see your Kipi files and that Dataview is ready for CRM views.

## Tests

### 1. Vault exists
Check if `q-system/.obsidian/` directory exists:
```bash
test -d "$CLAUDE_PROJECT_DIR/q-system/.obsidian"
```
- **Pass:** "Obsidian vault is set up."
- **Fail:** "Obsidian hasn't opened your q-system folder yet. Open Obsidian > 'Open folder as vault' > select the q-system folder."

### 2. Dataview plugin installed
Check if Dataview is in the community plugins list:
```bash
cat "$CLAUDE_PROJECT_DIR/q-system/.obsidian/community-plugins.json" 2>/dev/null | grep -q "dataview"
```
- **Pass:** "Dataview plugin is installed."
- **Fail:** "Dataview plugin isn't installed yet. In Obsidian: Settings > Community plugins > Browse > search 'Dataview' > Install > Enable."

### 3. CRM Dashboard readable
Check if the dashboard file exists:
```bash
test -f "$CLAUDE_PROJECT_DIR/q-system/CRM-Dashboard.md"
```
- **Pass:** "CRM Dashboard is ready. Open it in Obsidian to see your contact tables."
- **Fail:** "CRM Dashboard file is missing. This shouldn't happen - it's part of the skeleton."

### 4. Optional MCP server (skip if not configured)
If user configured the Obsidian MCP server, test it:
- Try `mcp__obsidian__list_files` or similar
- **Pass:** "Obsidian MCP server is connected. I can search and write to your vault."
- **Fail:** "MCP server isn't responding. Check that the Local REST API plugin is enabled in Obsidian and the API key matches."
- **Not configured:** Skip silently. The MCP server is optional.

## Success Message

> "Obsidian is connected. Your contacts, pipeline, and canonical files are browsable in the vault. Open CRM-Dashboard.md to see your data as tables."

## Failure Handling

If test 1 fails: The user hasn't opened the vault yet. Walk them through it.
If test 2 fails: Suggest installing Dataview. Not blocking - the system works without it.
If test 3 fails: Something is wrong with the skeleton. Check if this is a fresh install.
