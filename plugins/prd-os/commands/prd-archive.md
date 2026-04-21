---
description: Archive the active PRD (blocked until every accepted finding has a receipt)
allowed-tools: Bash
---

Archive the active PRD. The runner's G4 coverage gate blocks archive when any
accepted finding in the PRD's findings JSONL lacks a matching entry in the
issue-receipts file with `prd_id` set to the active PRD. Deferred findings
require a non-empty `rationale`; rejected findings pass through.

Do not edit the receipts file by hand. If the gate blocks, close the named
issues via `/issue-closeout` (which writes the receipts) and retry.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prd_runner.py" archive
```

On success, the spec's frontmatter flips to `status: archived` and the active
PRD state is cleared. On block, surface stderr verbatim — the runner names
each uncovered accepted finding and the path of the receipts file.
