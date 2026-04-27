---
description: Approve the planned DSSE issue and transition it from open to in-progress
---

**Autonomy contract (issues 2..N within an approved PRD).** Founder approval at `/prd-split` commit already authorized the manifest, including each issue's `allowed_files` and `required_checks`. So:

- **Issue 1** of a PRD: founder-gated. Founder sees the plan, types `approve`, then `/issue-approve` runs. This sets the working pattern for the PRD.
- **Issues 2..N** of the same PRD: agent self-approves IF the loaded plan's `allowed_files` and `required_checks` match the PRD manifest verbatim AND the plan does not introduce a scope amendment. Run `/issue-approve` directly without waiting for `approve` / `ok` / `start`.
- **Any deviation** from the manifest (new path, removed check, scope amendment): founder-gated, same as issue 1. Surface the diff, wait.

Founder-gated steps remain: `/prd-approve`, `/prd-split` commit, mid-issue scope amendments, and issue 1 plan-approval per PRD. Everything else self-progresses.

Approve the active DSSE issue after the founder has signed off on the plan. Execute in order:

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/issue_runner.py" approve`. This reads the active issue spec, confirms its status is currently `open`, and flips it to `in-progress`. The command writes the spec directly — do not use the `Edit` tool for this.

2. If approve exits non-zero:
   - No active issue: tell the founder to run `/issue-start <issue-id>` first.
   - Status already in-progress: safe to proceed, the runner is idempotent on re-approval.
   - Any other error: report it verbatim. Do not edit the spec manually to work around it.

3. Confirm in one line: "Issue $ISSUE_ID is now in-progress. Stop-time gate is armed."

After approval, proceed with the first concrete change from the plan. All edits must target `allowed_files`. Normal DSSE flow resumes: `/issue-verify`, `/issue-review`, `/issue-closeout`.
