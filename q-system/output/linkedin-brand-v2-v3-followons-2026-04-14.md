# linkedin-brand skill — v2/v3 follow-ons

**Date:** 2026-04-14
**Context:** v1 wired `linkedin-brand` SKILL.md to call `kipi_voice_lint` and `kipi_copy_edit_lint` deterministically in the Pre-Publish Checklist. These two linters cover em-dashes, banned words/phrases, filler openers, structural openers, sentence length, paragraph uniformity, complex-word replacements, filler words, and passive voice.

Everything below is NOT in v1. Each item stays as LLM self-check until built.

## v2a — Extend existing linters to close the self-check gap

Codex review on 2026-04-14 flagged that the initial skill rewrite overclaimed linter coverage. The skill now accurately distinguishes linter-enforced vs. self-check, but the self-check side has items that SHOULD be deterministic. Extend the linters rather than relying on memory.

Add to `draft_scanner.py`:
- `TIER1_WORDS` additions: ecosystem, landscape, holistic, scalable, disruptive
- Hyphenated addition: next-gen
- Adjective form: seamless (the adverb "seamlessly" is already caught)
- `BANNED_PHRASES` addition: `"in today's [^\s]+"` regex (catches any "in today's X" variant, not just world/fast-paced/era)

Add to `linter.py`:
- Rule-of-three detector: regex for `\b\w+,\s+\w+,\s+\w+\b` within a single sentence. False-positive risk on legitimate 3-item lists, so flag as warning not blocker initially.

**Cost:** ~15 lines. Single PR. Tests need one sample each.

## v2b — LinkedIn-specific gate (one new MCP tool)

Build `kipi_linkedin_gate(draft, day_of_week)` that wraps both linters plus:

1. **Hashtag counter.** Count `#` occurrences. Block if >1.
2. **External-link-in-body check.** Regex for `http(s)://` in body text (exclude first-comment context). Block if found.
3. **Day-of-week gate.** Block if day not in {Tue, Wed, Thu}. Accept override flag.

Return shape: `{pass, lint_voice, lint_copy, hashtag_count, body_links, day_ok, violations: []}`. Skill calls one tool instead of two plus manual checks.

**Cost:** ~80 lines Python in `linter.py`, one new `@mcp.tool()` registration in `server.py`, one skill edit.

## v3 — Cadence tracker

Build `kipi_linkedin_cadence_check()` that reads the publish log (`q-system/memory/marketing-state.md` or equivalent) and returns:

1. Posts this week: count.
2. Last post day: ISO date.
3. 70/30 engage ratio: comments-this-week / posts-this-week.
4. Blocks drafting a 4th post in a week. Warns if engage ratio <60%.

**Cost:** Requires a publish-logging mechanism first (write a row every time a LinkedIn draft is confirmed shipped). Needs founder decision: auto-log or manual log? Log to SQLite (`kipi.db`) or markdown?

## v4 — First-hour engagement tracker (stretch)

Track which 2nd-degree posts the founder commented on each morning. Pair with `kipi_linkedin_gate` to verify a first-hour plan was stated AND executed. Requires LinkedIn activity scrape (Apify actor exists) or manual log.

## Why these are separate

- v1 is a skill edit. Zero new code. 2 files touched.
- v2 adds ~80 lines of Python + one MCP tool registration. Testable.
- v3 requires persistent state (publish log). Design decision needed.
- v4 requires external data integration. Largest scope.

Batch v2 + v3 only if the founder is actively missing cadence or hashtag regressions. Otherwise v2 alone buys most of the remaining enforcement.

## Verification that v1 is working

End-to-end test on 2026-04-14:

- **Input:** founder's "Four companies. Same broken loop." LinkedIn post (137 words)
- **`kipi_voice_lint` result:** `pass: true`, 0 violations
- **`kipi_copy_edit_lint` result:** `pass: false`, 1 filler word found (`actually` in "could actually move on it")
- **After removing "actually":** `kipi_copy_edit_lint` `pass: true`, 0 issues

The old self-check missed this. The new enforcement caught it. v1 delivers the promised fix.
