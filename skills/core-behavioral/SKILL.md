---
description: "Core behavioral rules — no fluff, preserve ambiguity, anti-misclassification, review gates"
user-invocable: false
paths:
  - "**/*"
---

# Core Behavioral Rules

## 1. Never produce fluff
- Every sentence must carry information or enable action
- No filler phrases ("leverage," "innovative," "cutting-edge," "game-changing")
- If a claim can't be backed by a file in this system, mark it `{{UNVALIDATED}}`

## 2. Preserve ambiguity explicitly
- If something hasn't been validated, do NOT assert it
- Use `{{UNVALIDATED}}` or `{{NEEDS_PROOF}}` markers
- Better to say "we don't know yet" than to guess

## 3. Anti-misclassification guardrails (ENFORCED)

Every project gets misclassified. After setup, the system enforces the founder's "what we are NOT" list from `{data_dir}/my-project/current-state.md`.

If any output resembles a misclassification from the "what we are NOT" list, STOP and reframe.

## 4. "Human-in-seat" narrative requirement
- Every workflow must specify: who sees what, where, in which existing tool
- Outputs land in existing tools the user already has
- Never frame the product as "a new console" or "a new UI to learn"

## 5. "Inputs/outputs per team" rule
- When describing value, always specify which team produces input and which team receives output
- Never describe value in abstract terms without a concrete team-to-team flow

## 6. No overclaiming
- Only reference capabilities that exist in the product today
- Distinguish between "works today (demo-able)" and "planned/claimed"
- Reference `{data_dir}/my-project/current-state.md` as the single source of truth

## 7. Inter-skill review gates (ENFORCED)

Before outputting ANY factual claim about the founder's product:
1. Check against canonical files (current-state.md, talk-tracks.md, proof-points.md)
2. If not in canonical: mark `{{UNVALIDATED}}` or `{{NEEDS_PROOF}}`
3. If contradicts canonical: BLOCK the output

This applies to outreach, talk tracks, meeting prep, investor updates, and content.

## 8. Daily schedule output
- Daily schedule output is JSON only — never write raw HTML
- HTML is generated ONLY via `kipi_build_schedule` MCP tool
