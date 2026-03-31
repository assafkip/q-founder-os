---
description: "Anti-hallucination research mode — citation-verified, source-grounded analysis"
---

# /q-research — Research mode

Activates three anti-hallucination constraints. Stay in this mode until the founder says to exit or switches to another mode.

Source: [Anthropic - Reduce Hallucinations](https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)

## Arguments

`/q-research [topic]` — optional topic to research. If provided, begin researching immediately.

## Constraints (ALL active simultaneously)

### 1. Say "I don't know"
If you don't have a credible source for a claim, say so. Don't guess. Don't infer. "I don't have data on this" is always a valid answer.

### 2. Verify with citations
Every recommendation, claim, or piece of advice must cite a specific source:
- A debrief (person + date) from seed-materials/
- A canonical file (talk-tracks.md, objections.md, etc.)
- The relationships file
- An email thread
- An external source found via web search (with URL)
- A named expert or researcher

If you generate a claim and cannot find a supporting source, retract it. Do not present it.

### 3. Direct quotes for factual grounding
When working from documents (debriefs, canonical files, emails, web pages), extract the actual text first before analyzing. Ground your response in word-for-word quotes, not paraphrased summaries. Reference the quote when making your point.

## What this mode is NOT
- It is NOT the default. Creative thinking, brainstorming, and novel ideas don't require this mode.
- It does NOT mean "be slow." Research efficiently. Use tools in parallel.
- It does NOT mean "only use existing ideas." You can synthesize across sources to reach new conclusions, but the inputs must be grounded.

## How to exit
Say "exit research mode" or switch to any other mode (CALIBRATE, CREATE, PLAN, etc.)
