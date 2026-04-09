# Connect Obsidian

## What This Does
Makes your Kipi files browsable, searchable, and visually organized in Obsidian. Your existing markdown files become a navigable vault with CRM views, pipeline dashboards, and task lists.

## What the User Needs
- Obsidian installed (free from obsidian.md)
- That's it. No accounts, no tokens, no API keys.

## Setup Steps

Say:

> "Let's connect Obsidian. This is the easiest setup in the system:
>
> 1. Open **Obsidian**
> 2. Click **'Open folder as vault'**
> 3. Navigate to your project folder and select the **q-system** folder inside it
> 4. Obsidian will open your files. You're connected.
>
> That's it. All your contacts, pipeline, and canonical files are now browsable."

## Part 2: Install Dataview Plugin

Say:

> "One more thing to make it really useful. Let's add a plugin that turns your files into CRM views:
>
> 1. In Obsidian, go to **Settings** (gear icon, bottom left)
> 2. Click **Community plugins** on the left
> 3. Click **Turn on community plugins** if prompted
> 4. Click **Browse**
> 5. Search for **Dataview**
> 6. Click **Install**, then **Enable**
>
> Now open the file called **CRM-Dashboard** in your vault. You should see tables of your contacts and pipeline."

If they don't see tables: "Dataview needs to be enabled. Go back to Settings > Community plugins and make sure the toggle next to Dataview is on."

## Part 3: Optional Plugins

After Dataview is working, mention once:

> "Two more plugins you might like later. No rush:
> - **Calendar** - shows your files on a timeline
> - **Templater** - lets you create contact entries from a template
>
> You can add these anytime from the same Community plugins screen."

## Advanced: MCP Server (Optional)

For users who want Claude Code to search and write through Obsidian's API:

> "There's an advanced option that lets me interact with Obsidian directly. You only need this if you want me to search your vault from the command line.
>
> 1. In Obsidian, install the **Local REST API** plugin (same Community plugins screen)
> 2. In that plugin's settings, copy the **API key**
> 3. Paste it here"

When they paste:
1. Validate it's not empty
2. Add to `.mcp.json`:
```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uvx",
      "args": ["mcp-obsidian"],
      "env": {
        "OBSIDIAN_API_KEY": "[their key]"
      }
    }
  }
}
```

Tell the user:
> "Saved. You might need to restart Claude Code for this to take effect."

## How It Works

Claude Code writes markdown files (contacts, actions, follow-ups). Obsidian reads those same files and renders them as tables, graphs, and dashboards. No sync. No API. Same files, two views.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "I don't see any files" | "Make sure you opened the **q-system** folder specifically, not the parent project folder." |
| "Dataview tables are empty" | "Check that you have entries in `my-project/relationships.md`. The dashboard reads from that file." |
| "CRM Dashboard shows code instead of tables" | "Dataview plugin isn't enabled. Go to Settings > Community plugins and toggle it on." |
| "I want to switch from Notion" | "No migration needed. Your data is already in markdown files. Obsidian just makes it visible." |
