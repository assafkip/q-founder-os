---
description: "First-time interactive setup wizard — profile, voice, integrations, network. Supports partial reconfiguration."
---

# /q-setup — Setup wizard for Q Founder OS

Run on first use for full setup, or anytime to reconfigure specific sections.

## Path resolution

All user data lives under `${CLAUDE_PLUGIN_DATA}` (provided by Claude Code plugin system). Read the `kipi://paths` MCP resource to get resolved directories.

In plugin mode, `{config_dir}`, `{data_dir}`, and `{state_dir}` all resolve to the same instance directory under `${CLAUDE_PLUGIN_DATA}/instances/{name}/`.

## Detection

**FIRST:** Read the `kipi://status` MCP resource.

**Then:** Read `{config_dir}/founder-profile.md`. If it contains `{{SETUP_NEEDED}}`, this is a fresh install → run full setup (all steps).

If `{{SETUP_NEEDED}}` is NOT present, show the reconfigure menu:

```
You're already set up. What do you want to update?

1. Profile (name, role, company, stage)
2. Target buyer & positioning
3. Voice & writing style
4. Integrations (MCP servers, API keys)
5. Google Analytics (GA4 setup)
6. CRM / Notion databases
7. Network (contacts, investors)
8. Behavioral rules (AUDHD, voice enforcement, etc.)
9. Run full setup from scratch

Pick a number, or describe what you want to change.
```

Jump directly to that step. No need to re-run everything.

## Steps

### Step 1: Who are you?

Ask:
- What's your name?
- What's your role? (founder, operator, executive, etc.)
- What's your company/project name?
- What do you sell / what are you building? (one sentence)
- What stage are you at? (idea, pre-seed, seed, Series A, growth)
- Do you have a co-founder? If so, name and role.

**After getting the company name**, generate an instance name:
1. Call `kipi_suggest_instance_name(company=<company_name>)` for a suggestion
2. Show it, let them override or accept
3. Call `kipi_set_instance_name(name=<chosen_name>)` to register

**Save to:** `{config_dir}/founder-profile.md`

### Step 2: Who do you sell to?

Ask:
- Who is your target buyer? (title, department, company size)
- What industry/vertical?
- What's the pain you solve? (in the buyer's words)
- What do they use today instead? (competitors or manual process)
- What's your price point or deal size? (if known)

**Save to:** `{data_dir}/my-project/current-state.md` and `{config_dir}/canonical/discovery.md`

### Step 3: What's your positioning?

Ask:
- Do you have a one-liner? ("We help [who] do [what] by [how]")
- Any metaphors or analogies that have landed?
- What are you NOT? (common misclassifications)
- What are the top 3 objections you hear?

**Save to:** `{config_dir}/canonical/talk-tracks.md`, `{config_dir}/canonical/objections.md`

### Step 4: Your voice

Ask:
- How would you describe your writing style?
- Any words or phrases you naturally use?
- Any words or phrases you hate?
- Share 2-3 examples of messages or posts you've written

**Save to:** `{config_dir}/voice/voice-dna.md` and `{config_dir}/voice/writing-samples.md`

### Step 5: Your tools (SMART DETECTION)

Check `.mcp.json` for configured MCP servers and test each:

**Google Calendar & Gmail:**
- Test `gcal_list_events` and `gmail_search_messages`
- If not configured, show install commands:
  ```
  claude mcp add google-calendar -- npx -y @anthropic/google-calendar-mcp
  claude mcp add gmail -- npx -y @anthropic/gmail-mcp
  ```

**Notion:**
- Test Notion MCP connection
- If works: "Notion connected. We'll use it for CRM."
- If fails: "Skipping — system works with local files."

**Apify:**
- Test if Apify MCP or APIFY_TOKEN env var exists
- If not: show install command:
  ```
  claude mcp add apify -e APIFY_TOKEN=your_token -- npx -y @apify/actors-mcp-server
  ```

**Chrome MCP:**
- Check if Chrome MCP tools are available
- If not: "Chrome MCP needed for LinkedIn data. Configure in Claude.ai settings."

**Reddit:**
- Test if Reddit MCP is available
- If not: show install command:
  ```
  claude mcp add reddit -- uvx --from git+https://github.com/adhikasp/mcp-reddit.git mcp-reddit
  ```

Write final state to `{config_dir}/enabled-integrations.md`.

### Step 5b: Google Analytics (GA4)

Ask: "Do you use Google Analytics? Want weekly site metrics and UTM tracking in your morning schedule?"

If yes:
1. Walk through service account setup:
   - "Go to Google Cloud Console → APIs & Services → Enable 'Google Analytics Data API'"
   - "Create a service account → download the JSON key file"
   - "In GA4 Admin → Property Access Management → add the service account email as Viewer"
2. Ask for their GA4 Property ID (numeric, found in GA4 Admin → Property Settings)
3. Ask for the path to their service account JSON file
4. Save env vars guidance: "Set these in your shell profile or .env file:"
   ```
   export GA4_PROPERTY_ID=123456789
   export GA4_CREDENTIALS_PATH=/path/to/service-account.json
   ```
5. Set `ga4: true` in `enabled-integrations.md`

If no: set `ga4: false`. GA4 sources will be silently skipped during harvest.

### Step 5c: Harvest source configuration

Ask about optional env vars for data sources:
- "What's your X/Twitter handle?" → `TWITTER_HANDLE`
- "What's your Medium username?" (if applicable) → `MEDIUM_USERNAME`
- "What's your Substack publication name?" (if applicable) → `SUBSTACK_PUB`
- "Which subreddits should I monitor for your industry?" → `REDDIT_SUB_1`, `REDDIT_SUB_2`, `REDDIT_SUB_3`
- "Which subreddits for lead sourcing?" → `REDDIT_LEAD_SUB_1`, `REDDIT_LEAD_SUB_2`
- "What X/Twitter search terms for finding leads?" → `X_LEAD_SEARCH_TERMS`

Show the user all env vars they need to set. Save a reference to `{config_dir}/harvest-env-vars.md`.

### Step 6: Your CRM

**If Notion is enabled:**
- Walk through creating or connecting databases: Contacts, Actions, Pipeline, LinkedIn Tracker, Content Pipeline
- For each DB, get the database ID and save to `{data_dir}/my-project/notion-ids.md`
- **Test write access:** Create a test action in Actions DB, then delete it. If write fails, show error.

**If Notion is NOT enabled:**
- "No problem — the system works with local files. relationships.md is your CRM."

### Step 7: Your network

Ask:
- Who are your top 10 contacts right now?
- Any investors you're talking to?
- Any design partners or early customers?
- Any advisors or connectors?

**Save to:** `{data_dir}/my-project/relationships.md`

### Step 8: Behavioral rules

Show the available behavioral rules and let the founder toggle:

```
These rules shape how the system behaves. All default OFF — enable what you want.

Core rules:
  [x] founder-voice — enforce your writing style in all generated copy
  [ ] audhd-executive-function — AUDHD accommodations (friction-ordering, no shame language, copy-paste-only)
  [x] core-rules — positioning guardrails, anti-misclassification
  [ ] auto-detection — auto-detect pasted transcripts and run /q-debrief

Workflow rules:
  [x] token-discipline — prevent token waste during long sessions
  [x] preflight-audit — execution harness for /q-morning
  [ ] operating-modes — CALIBRATE/CREATE/DEBRIEF/PLAN mode definitions
  [ ] decision-tagging — tag decisions as user-directed vs claude-recommended
  [ ] file-authority — route new info to correct canonical files
  [ ] memory-architecture — time-stratified memory lifecycle
  [ ] marketing-system — content guardrails, brand voice, theme rotation
```

For each: explain in one sentence what it does, let them toggle on/off.

If they mentioned ADHD/ASD earlier (Step 4), pre-check `audhd-executive-function`.

**Save to:** `{config_dir}/enabled-integrations.md`

### Step 9: Confirmation

1. Show summary of everything configured
2. Ask if anything needs adjusting
3. Remove `{{SETUP_NEEDED}}` markers
4. Show data location (from `kipi://paths`)
5. Tell the user: "You're set. Run `/q-morning full` for your first morning briefing, or `/q-health` to verify everything is connected."

## Output rules
- Conversational tone, one step at a time
- Never dump all questions at once
- Confirm each step before moving on
- If the user seems overwhelmed, skip optional steps
- When reconfiguring: jump directly to the requested step, don't repeat completed steps
