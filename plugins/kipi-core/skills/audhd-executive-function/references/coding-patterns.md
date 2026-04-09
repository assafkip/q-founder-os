# AUDHD Coding Patterns - Full Reference

> CBT-informed coding accommodations. This file is the rationale behind the terse rules in `.claude/rules/coding-audhd.md` and the deterministic checks in `wiring-check.py`.
> Sources: JAN (Job Accommodation Network), Barkley scaffolding, Mahan Wall of Awful, Dodson interest-based nervous system, CBT for adult ADHD (Safren, Ramsay & Rostain).

## Why Code Structure Maps to Executive Function

Working memory limits don't just affect reading schedules. They affect reading code. A 3-level nested if-else chain requires holding 3 simultaneous conditions in working memory. For AUDHD, that's the buffer limit. The code should accommodate the reader, not test them.

| EF Deficit | Code Anti-Pattern | Accommodation |
|---|---|---|
| Working memory | Deep nesting, long functions | Max 2 levels, max 30 lines per function |
| Task object permanence | Variables defined far from use | Define close to use, names carry full meaning |
| Decision fatigue | Multiple code approaches presented | One approach. User overrides if they want. |
| Time blindness | "Real quick" scope additions | Explicit scope boundaries before starting |
| All-or-nothing | Partial failures crash everything | Partial success is valid, report what worked |
| RSD | "Easy fix" / "obviously" language | Factual. No difficulty qualifiers. |

## The Wiring Problem (Clinical View)

Forgetting to wire code is not carelessness. It's a working memory failure. The ADHD brain held the function implementation in active memory, wrote it, got the dopamine hit of completion, and moved on. The wiring step (connecting it to the caller) was in prospective memory, which is precisely what ADHD impairs.

This is the same mechanism as "I wrote the email but forgot to hit send." The compose step consumed all available working memory. The send step evaporated.

The accommodation: externalize the wiring check. Don't rely on the developer (human or LLM) to remember. Run a deterministic check every time code changes.

## The Emotional Weight of Debugging

CBT model: A failing test activates a negative automatic thought ("I'm bad at this"). The thought triggers an emotion (shame, frustration). The emotion triggers a behavior (avoidance, rage-quitting, or hyperfocus tunnel). The behavior prevents adaptive problem-solving.

AUDHD compounds this:
- ASD pattern-matching recalls every previous debugging failure
- ADHD emotional dysregulation amplifies the frustration
- RSD interprets the failure as personal ("a real developer would know this")
- The Wall of Awful grows. Each brick is a past failure. The wall blocks the next attempt.

Counter-accommodation is not reassurance ("you've got this!"). Reassurance feels performative and triggers RSD suspicion. The counter is:
1. Factual progress framing: what we tried, what we ruled out, what we know
2. Scope reduction: make the next step smaller, not bigger
3. Clean exit ramps: "good stopping point" without shame

## Interest-Based Task Pairing in Code Sessions

The ADHD nervous system activates on interest, not importance. A boring config refactor will stall even if it's critical. An interesting UI feature will get hyperfocused on even if it's low priority.

Accommodation for code sessions:
- Start with a quick, satisfying fix (passing test, visible change)
- Place boring-but-essential work in the middle (peak focus, momentum from quick win)
- End with something satisfying (demo, passing suite, clean commit)
- Never end on a broken state. The last thing in memory should be completion.

## Cognitive Distortion Counter-Patterns in Code

| Distortion | Trigger | System Response |
|---|---|---|
| All-or-nothing | Build fails | "Test on line 42 expected X, got Y." Specific, not total. |
| Catastrophizing | Bug found in production | "One function affected. Fix is [specific]." Scope it. |
| Mind-reading | No code review response yet | No mention. Surface when actionable. |
| Should statements | Needed to look something up | No commentary. Everyone looks things up. |
| Emotional reasoning | "This feels impossible" | Offer micro-action: smallest next step. |
| Discounting | Quick fix worked | "That works. Next." Full credit, no qualifier. |

## The Post-Session Crack Detection Checklist

Deterministic checks the wiring-check.py script runs on every Edit/Write:
1. Debug statements (print, console.log, breakpoint, debugger)
2. TODO/FIXME/HACK comments added this session
3. Unused imports
4. Functions defined but never called in the same file
5. Bare except clauses (Python)
6. Deep nesting beyond threshold
7. Functions exceeding length threshold
8. Hardcoded values that should be config

What it does NOT check (requires cross-file analysis, future enhancement):
- Route registration across files
- Component rendering in parent trees
- Event emitter/listener pairing
- Schema field usage in queries
- Environment variable documentation
