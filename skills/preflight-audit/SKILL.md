---
description: "Preflight and audit harness — mandatory before /q-morning, fail-fast protocol, flight recorder"
user-invocable: false
paths:
  - "**/agent-pipeline/**"
  - "**/output/**"
  - "**/bus/**"
---

# Preflight, Fail-Fast, and Audit Harness (ENFORCED)

Before every `/q-morning` run, read `q-system/agent-pipeline/preflight.md` FIRST. It contains:
1. Tool manifest with exact tests, known limitations, and fallback chains
2. Known issues registry (things that broke before — never re-discover)
3. Session budget with hard split points and handoff format
4. Step completion log format (flight recorder)

Every step must write its completion status to `{state_dir}/output/morning-log-YYYY-MM-DD.json`. This is a file on disk, not context. Even if context rots, the log is accurate. If a step isn't logged, it didn't happen.

After the routine ends, run the audit harness via `kipi_audit_morning` MCP tool. Show the audit output to the founder. This is not optional.

If any MCP server is unavailable or any step fails during `/q-morning`, STOP the entire routine immediately and report what broke. Do NOT continue with partial data.
