---
description: "Weekly content scraping and scoring across LinkedIn, X, Reddit, and Medium"
---

# /q-content-intel — Content intelligence

Scrape your own content across all platforms. Analyze what works vs. what doesn't. Build a data-driven content scoring model.

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
1. `{config_dir}/enabled-integrations.md` — which scrapers are available
2. `{config_dir}/canonical/content-intelligence.md` — current scoring model
3. `{config_dir}/marketing/content-themes.md` — theme definitions (1-8)

## Process

### Full run (weekly or on demand)

1. **Scrape all platforms via Apify:**
   - LinkedIn: Posts Scraper actor on founder's profile (last 30 days). Extract: text, impressions, likes, comments, reposts, date/time.
   - X/Twitter: Scraper actor on founder's handle (last 30 days). Extract: text, impressions, likes, retweets, replies, quotes, date/time.
   - Medium: Web Scraper on founder's profile. Extract: title, reads, claps, read ratio, responses, publish date.
   - Reddit: Scraper on founder's posts (last 30 days). Extract: title, subreddit, upvotes, comments, upvote ratio.
   - Substack: Web Scraper on founder's profile. Extract: title, open rate, click rate, subscriber count.

2. **Normalize and rank:**
   - Engagement rate per post: (likes + comments + reposts) / impressions
   - Rank by engagement rate per platform
   - Tag each post with content theme (from content-themes.md)
   - Tag with format: signals, thought leadership, hot take, BTS, thread, article, comment

3. **Pattern extraction:**
   - Top 20%: shared language, format, topic, length, time-of-day patterns
   - Bottom 20%: patterns to avoid
   - Theme analysis: which themes perform best per platform
   - Format analysis: which format gets most engagement per platform
   - Timing analysis: best day/time combinations
   - Hook analysis: first lines of top performers
   - Language analysis: phrases in top performers absent from bottom performers

4. **Update `{config_dir}/canonical/content-intelligence.md`:**
   - Refresh Performance Baselines tables
   - Update "What Works" and "What Doesn't Work"
   - Update Theme Performance table
   - Update Content Scoring Model criteria
   - Add Weekly Intel Log entry

5. **Save report** to `{state_dir}/output/content-intel/content-intel-YYYY-MM-DD.md`

### Quick score (on demand)

Run `/q-content-intel score` with a draft post. Scores 1-5 on hook strength, pattern match, platform fit, timing, and novelty using current content-intelligence.md data. Returns pass/revise/rethink.

## Output rules

- Apply `founder-voice` rule to recommendations
- Present patterns as actionable changes, not abstract observations
- Apify cost estimate: ~$2-4 per full run
