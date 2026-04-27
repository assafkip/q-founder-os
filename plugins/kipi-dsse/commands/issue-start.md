---
description: Load a DSSE issue spec and begin structured work
argument-hint: <issue-id>
---

You are starting a DSSE issue. The issue id is: $ARGUMENTS

Execute the following, in order:

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/issue_runner.py" load $ARGUMENTS`. The output is JSON describing the loaded spec. If the command exits non-zero, stop and report the error. Do not invent an issue spec.

2. Read the full spec file at the `spec_path` returned by step 1.

3. Present a plan to the founder:
   - One line summarizing the title and priority.
   - The full `allowed_files` list exactly as loaded. State explicitly: "all edits must target one of these paths."
   - The full `required_checks` list. State: "these must all exit 0 before `/issue-verify` will record the verified receipt."
   - The full `required_reviews` list.
   - The first concrete change you plan to make, in one sentence.

4. Decide whether to wait for the founder or self-progress, per the issue-approve autonomy contract:
   - If this is **issue 1** of the PRD: wait for the founder to approve the plan or redirect. Do not flip the spec status and do not start editing until they confirm.
   - If this is **issue 2..N** of the same PRD AND the plan's `allowed_files` and `required_checks` match the PRD manifest verbatim AND no scope amendment is introduced: do NOT wait. Proceed directly to step 5.
   - If the plan deviates from the manifest in any way: wait for founder.

5. Run `/issue-approve`. That command flips the spec status from `open` to `in-progress` and arms the stop-time gate. Planning before this step is intentionally gate-exempt so a loaded spec does not spam the Stop hook while the plan is being reviewed.

**Do NOT ask the founder for confirmation on:**
- `/issue-start` invocation itself (the founder already typed it or the prior issue's closeout chained to it)
- Commit + push between issues (the auto-approve-git PreToolUse hook handles it; if the hook denies, founder gets the prompt naturally)
- Advancing to the next issue in the PRD chain when the prior issue closed cleanly

Rules while the issue is loaded:
- Every edit you make must target a path that matches `allowed_files`.
- The PreToolUse scope hook will block out-of-scope edits automatically.
- Do not mark the issue verified, reviewed, or closed yourself. Use `/issue-verify`, `/issue-review`, `/issue-closeout`.
- If you discover mid-issue that the scope is wrong, update the spec file's `allowed_files` first, explain why, then continue.
