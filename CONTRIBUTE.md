# Contributing to the Skeleton

## Change Process

1. **Branch** - Create a feature branch from `main`
2. **Change** - Make your changes
3. **Validate** - Run `python3 validate-separation.py 1 --verbose` (pre-commit runs this automatically)
4. **Commit** - Pre-commit hook blocks if Phase 1 fails
5. **Push** - Pre-push hook runs full phases 0-5 and blocks if any fail
6. **PR** - GitHub Actions runs Phase 1 validation + flags protected file changes
7. **Merge** - Merge to main after review
8. **Propagate** - Run `kipi update` to push changes to all instances

## Protected Files

These files affect all instances. Changes require extra review:

| File | Why it matters |
|------|---------------|
| `q-system/CLAUDE.md` | Behavioral rules loaded by every instance |
| `q-system/.q-system/token-guard.py` | Circuit breaker, blocks tool calls |
| `q-system/.q-system/agent-pipeline/agents/step-orchestrator.md` | Morning pipeline execution plan |
| `q-system/.q-system/agent-pipeline/BUS-PROTOCOL.md` | Inter-agent contract definitions |
| `validate-separation.py` | Validation harness, gates all commits/pushes |
| `.claude/settings.json` | Permissions, hooks, output style |
| `settings-template.json` | Template for new instances |
| `kipi` | CLI entry point |

The pre-commit hook warns when these are modified. Review the diff before pushing.

## Validation Layers

| Layer | When | What runs | Blocks on failure |
|-------|------|-----------|-------------------|
| Pre-commit hook | `git commit` | Phases 0-1 (skeleton integrity) | Yes |
| Pre-push hook | `git push` | Phases 0-5 (full validation) | Yes |
| GitHub Actions | Push/PR to main | Phase 1 + protected file check | Yes (CI status) |

To install hooks in a fresh clone: `git config core.hooksPath .githooks`

## Push Generic Improvements Upstream

If you make a generic improvement in an instance (new agent, script fix, template enhancement) that would benefit all instances:

```bash
cd /path/to/my-instance
/path/to/kipi-system/kipi-push-upstream.sh
```

The script:
1. Checks for instance-specific content in the subtree (blocks if found)
2. Pushes the subtree changes to the kipi-system remote

## Safety Rules

- Never put instance-specific content in `q-system/` (canonical files, my-project data, voice samples)
- The push script checks for common leaks (company names, personal info, hardcoded paths)
- If the safety check fails, clean the instance content out first

## What Belongs in the Skeleton

- Agent prompt files (generic pipeline logic, no domain-specific rules)
- Scripts (audit, verification, build tools)
- Canonical templates (empty `{{}}` placeholders, not populated content)
- Marketing templates (structure, not content)
- Voice skill framework (not voice DNA or writing samples)
- CLAUDE.md behavioral rules (not instance identity)

## What Stays in the Instance

- Populated canonical files (talk tracks, objections, positioning)
- my-project/ data (founder profile, relationships, current state)
- Marketing assets (bios, stats, proof points)
- Voice DNA and writing samples
- Instance-specific skills and commands
