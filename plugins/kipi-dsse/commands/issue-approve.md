---
description: Approve the planned DSSE issue and transition it from open to in-progress
---

**Autonomy contract (advisor-approved, founder gated only at charter level).** In the v2 rewrite topology, plan approvals route to the **advisor** (main session), not to the founder. Founder approval at `/prd-split` commit already authorized the manifest, including each issue's `allowed_files` and `required_checks`. Plan approvals refine that authorization at the issue level and are advisor-owned.

- **Issue 1** of a PRD: advisor-gated. The advisor (main session) sees the plan via the channel, replies `approve` (or surfaces a redirect). Founder is NOT routed unless the plan introduces a scope amendment relative to the manifest.
- **Issues 2..N** of the same PRD: agent self-approves IF the loaded plan's `allowed_files` and `required_checks` match the PRD manifest verbatim AND the plan does not introduce a scope amendment. Run `/issue-approve` directly without waiting for advisor or founder.
- **Any deviation** from the manifest (new path, removed check, mid-issue scope amendment): **founder-gated**. Surface the diff with `[FOUNDER-INPUT-NEEDED]` and wait. Scope amendments are charter-level changes the founder owns.

Founder-gated steps remain (charter-level only):
- `/prd-approve` (founder owns the PRD contract)
- `/prd-split` commit (founder owns the issues manifest)
- Mid-issue scope amendments (founder owns scope)

Everything else self-progresses or routes to the advisor. Codex finding triage and disposition during `/issue-closeout` are agent-handled per the closeout autonomy contract.

Approve the active DSSE issue after the advisor (or, for scope amendments, the founder) has signed off on the plan. Execute in order:

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/issue_runner.py" approve`. This reads the active issue spec, confirms its status is currently `open`, and flips it to `in-progress`. The command writes the spec directly — do not use the `Edit` tool for this.

2. If approve exits non-zero:
   - No active issue: tell the founder to run `/issue-start <issue-id>` first.
   - Status already in-progress: safe to proceed, the runner is idempotent on re-approval.
   - Any other error: report it verbatim. Do not edit the spec manually to work around it.

3. Confirm in one line: "Issue $ISSUE_ID is now in-progress. Stop-time gate is armed."

After approval, proceed with the first concrete change from the plan. All edits must target `allowed_files`. Normal DSSE flow resumes: `/issue-verify`, `/issue-review`, `/issue-closeout`.
