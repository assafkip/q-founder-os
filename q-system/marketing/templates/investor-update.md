# Template: Investor Update Email

> Used by `/q-investor-update`
> Milestone-triggered, not calendar-triggered. Send when there's something worth sharing.

---

## Pre-Generation Steps

1. **Pull metrics** from progress.md and current-state.md
2. **Check decisions.md** for major decisions since last update
3. **Check relationships.md** for investor context (what they care about, last touchpoint)
4. **Pull pipeline state** from CRM or relationships.md
5. **Check memory/morning-state.md** -> "Investor Update Tracker" for last update date

## Structure

```
Subject: {{YOUR_PRODUCT}} Update - [Month] [Year] - [1 headline]

Hi [first name],

Quick update on {{YOUR_PRODUCT}} since we last talked.

HIGHLIGHT (1 sentence - the single biggest thing)
[The one thing that moves the needle most]

PRODUCT
- [2-3 bullets, concrete, no fluff]

TRACTION
- [Design partners, conversations, pipeline numbers]

WHAT'S NEXT
- [2-3 bullets on immediate priorities]

ASK (optional - only if there's a specific, low-effort ask)
- [Intro to a specific person, feedback on a specific thing]

Thanks for following along.
{{YOUR_NAME}}
```

## Variants

- **Active pipeline VCs** (status: Follow-up, First Meeting): Include ASK tailored to their portfolio
- **Thesis nod VCs** (status: First Meeting done, no next step): Standard update, no ASK. Let traction speak.
- **Warm connectors** (people who offered intros): Include specific intro ASK if relevant
- **BCC list** (everyone else): Standard update, generic sign-off

## Rules

- Under 300 words. VCs scan, they don't read.
- Plain text email. No HTML, no fancy formatting.
- Lead with the strongest proof point, not vision.
- No "we're excited to announce" or "thrilled to share" - just state the fact.
- Numbers over adjectives. "3 design partners" not "growing traction."
- The ASK must be specific and low-effort. "Would you intro me to [Name] at [Company]?" not "Let me know if you know anyone."
- Personalize the ASK per VC based on their portfolio/network (batch of 3-4 variants max).
- Send from personal email, not a newsletter tool.

## Output Format

Save to: `output/investor-updates/investor-update-YYYY-MM-DD.md`

## Post-Generation

1. Run voice skill on the draft
2. Include recipient list with variant assignments
3. Update `memory/morning-state.md` -> "Investor Update Tracker" with date and summary
4. Create Action: "Review and send investor update" (Energy: Deep Focus, Time: 15 min)
