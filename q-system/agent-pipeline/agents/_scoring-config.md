# Scoring Config

Single source of truth for lead scoring, temperature signals, and strategic targeting.
Read by agents that score prospects or generate outreach.

## Regulatory/Compliance Bonus
Regulated sectors: energy, transport, banking, health, digital infra, cloud, ICT.
Lead scoring bonus: +3. Temperature bonus: +1.
Angle: "regulators now agree with the problem you're describing."

## Lead Scoring (6 dimensions, 0-5 each, max 30 + bonus)

- **Pain Signal** (0-5): Real operational problem? (5 = "we have no way to track X", 0 = generic opinion)
- **First-Person Proof** (0-5): Their own experience? (5 = "I spent 3 days manually...", 0 = retweeted article)
- **Role Fit** (0-5): Buyer persona? (5 = matches ICP exactly, 0 = student/vendor/irrelevant)
- **Budget Signal** (0-5): Can they pay? Read budget-qualifiers.md for keep/skip signals. (5 = quantified pain + senior title + team, 0 = student/side hustle/no revenue signal). **Score 0 = auto-discard regardless of other scores.**
- **Engagement Opportunity** (0-5): Can you add real value? (5 = specific pain you can address, 0 = 50 generic replies)
- **Multi-Team Pain** (0-5): Touches multiple teams? (5 = 3+ teams/departments, 0 = single person complaint)

## Lead Tiers
- Tier A (22-30): Send outreach today
- Tier B (16-21): Engage today (comment, then DM)
- Tier C (10-15): Add to warm list
- Below 10: Discard

## Temperature Signal Weights

| Signal | Weight |
|--------|--------|
| DM reply received | +3 |
| Email reply received | +3 |
| Demo request / scheduling link clicked | +4 |
| Connection accepted (within 7 days) | +2 |
| Comment on your post | +2 |
| Like on your post | +1 |
| Link click (tracked UTM) | +2 |
| Profile view (notification) | +2 |
| Post share/repost (notification) | +3 |
| Regulated sector prospect | +1 |
| No contact 14+ days | -1 |
| No contact 30+ days | -2 |

## Temperature Buckets
- Hot: 8+
- Warm: 4-7
- Cool: 1-3
- Cold: 0 or below
