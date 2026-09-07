# Audit: does the public repo match the tool? (2026-09-07)

Founder's ask, verbatim: "ensure that the kipi-system public repo matches the capabilities of the actual tool".

Base: `origin/main` at `4a3afa7f`. Branch: `sana/readme-matches-tool`.

## 1. Plan (this section replaces a plan file; the plan-file gate refuses a worktree subagent write to `q-system/output/plans/`)

**What / why.** The public front page of github.com/assafkip/kipi-system asserts capabilities. A stranger reads them. Any assertion with no executable behind it is a lie on the front page, and a capability the tool has that the page never names is the same mismatch pointed the other way.

**Scope of "public surface" on main today.**

- `README.md` (371 lines).
- `docs/` is NOT on main. `git ls-tree -r --name-only origin/main | grep -cE '^docs/'` returns `0`. The handbook is still only on the parked PR #306 branch. So there is no docs page to audit.
- `plugins/*/.claude-plugin/plugin.json` (6 manifests) plus the root `.claude-plugin/marketplace.json`.
- `CLAUDE.md`.

**Approach.** Build a numbered claims list from the README, one row per sentence that says the system DOES something. For each, name the executable and run or drive it in the cheapest way that can fail. Then invert: list CLI verbs, MCP tools and plugin commands the public surface never mentions.

**Acceptance criteria.**

- [x] Every README claim has a verdict and a command that produced it.
- [x] The three PR #310 minors re-checked against HEAD, not re-derived.
- [x] Reverse list produced.
- [ ] FALSE claims fixed in README prose only, on one branch off origin/main.
- [ ] Every touched claim re-verified by running the executable it now names.

**Patterns followed.** Recon before edit (read the code, not the docs about the code). A claim with no executable is FALSE, not UNVERIFIED. A claim whose executable exists but whose test is missing or red is UNVERIFIED.

---

## 2. The three PR #310 minors: still open on main

Task said check, do not re-derive. The decisive check is one command:

```
$ git log --oneline 67986e56..HEAD -- q-system/.q-system/scripts/knowledge_supply.py q-system/.q-system/knowledge-sources.json README.md
(no output)
```

Nothing has touched the README or the reader since PR #310 merged (`67986e56`, 2026-09-06 01:59Z). All three minors from that verdict are unfixed on main today. Each re-confirmed against HEAD below, because a review finding decays:

| # | Minor (PR #310 verdict comment) | README | Re-confirmed at HEAD by |
|---|---|---|---|
| M1 | A budget-cut pass reads `COVERAGE: FULL`, not PARTIAL | `README.md:74`, mermaid edge `README.md:82` | `knowledge_supply.py:2198` only appends a class to `missing` when `spec.get("required")` is truthy. `knowledge-sources.json:28,38` set `"docs": {"required": false}` in every task class. A truncated docs pass sets `searched_state="partial"` and never enters `missing`, so `knowledge_supply.py:2257` computes `FULL`. |
| M2 | "Every markdown folder the project keeps is a source" is an allowlist of eight declared names | `README.md:63` | `q-system/.q-system/knowledge-sources.json:10` is the literal list: `["output","research","inputs","investigation","build","docs","notes","memory"]`. |
| M3 | Security bullet assigns hard resets to a "shipped hook script" that exists only as a non-executable test fixture | `README.md:361` | `find . -name 'destructive-op-deny*' -not -path '*/.git/*'` returns exactly one file: `q-system/.q-system/tests/fixtures/destructive-op-deny.reference.sh`, mode `-rw-r--r--`, not executable. Nothing in the repo writes it to a hook path. |

M1's deadline half is sound and stays: `knowledge_supply.py:1747` emits an explicit `DEADLINE:` header and `class_search_state` (`:1282`) returns `False` for a cold-stopped class, which is required, which does enter `missing`. Only the *budget* half is wrong.

---

## 3. Claims ledger

Verdicts: TRUE = an executable delivers it and a run proved it. FALSE = no executable, or the executable does the opposite. UNVERIFIED = executable exists, no test or the check could not be driven cheaply.

Line numbers are the PRE-edit README on `origin/main` at `4a3afa7f`.

| # | Claim | file:line | Executable | Command run | Verdict |
|---|---|---|---|---|---|
| 1 | "It runs in Claude Code. Plain markdown all the way down. No vector database" | README.md:11 | none needed; absence claim | `grep -rl 'faiss\|chromadb\|pinecone\|sentence_transformers' --include='*.py' .` returns nothing outside `.git` | TRUE |
| 2 | The reader works out what you are asking about, reads the sources that matter, and puts the evidence in front of the model | README.md:7 | `q-system/.q-system/scripts/knowledge_supply.py`, wired UserPromptSubmit as `knowledge-inject.py` | `grep -o '"command": "[^"]*"' settings-template.json` shows `knowledge-inject.py` under UserPromptSubmit | TRUE |
| 3 | Sub-stores: a project holds many knowledge bases, one per case, and naming one scopes the search | README.md:62 | `knowledge_supply.py` + manifest `stores` | `knowledge-sources.json:9` = `{"name":"case","glob":"investigations/case-*"}`; PR #310 review reproduced the per-case block behaviour | TRUE |
| 4 | "Every markdown folder the project keeps is a source" | README.md:63 | `knowledge-sources.json` `folders` | `grep -n 'folders' q-system/.q-system/knowledge-sources.json` returns line 10, a literal 8-name allowlist | **FALSE** (fixed) |
| 5 | A word found in more than four knowledge bases is dropped and the receipt says so | README.md:64 | `knowledge_supply.py` `MAX_CANDIDATE_STORES` | PR #310 review measured `MAX_CANDIDATE_STORES = 4` and `candidates_dropped` in the receipt | TRUE |
| 6 | "Any pass that stopped early reads as partial, never as full" | README.md:74, mermaid README.md:82 | `knowledge_supply.py:2198`, `:2257` | `knowledge_supply.py:2198` gates on `spec.get("required")`; `knowledge-sources.json:28,38,...` set `"docs": {"required": false}`; verdict at `:2257` is `FULL` when `missing` is empty | **FALSE** (fixed) |
| 7 | `COVERAGE: NONE` exists and means no declared source could be read | README.md:74 | `knowledge_supply.py:2257` | read: `"NONE" if all(not r["present"] for r in source_rows)` | TRUE |
| 8 | A deadline is recorded and named in the header | README.md:74 | `knowledge_supply.py:1747`, `class_search_state` at `:1282` | read: `DEADLINE: stopped after {elapsed_ms} ms at {at_class}/{at_entity}` | TRUE |
| 9 | Every excerpt is verbatim with its file and line; no summarize step | README.md:104 | `knowledge_supply.py` `search_docs` returns `(Path, int, str)` triples | `sed -n '1292,1300p'` shows the return type carries path and line number | TRUE |
| 10 | Every name the index could not resolve goes to a misses ledger | README.md:107 | misses ledger writer | not driven this pass; no command run | UNVERIFIED (missing check: a test that asserts an unresolved name lands in the misses file) |
| 11 | Relevant lesson bodies are placed in the prompt before the work starts | README.md:118 | `lessons-inject.py` | `grep -o '"command": "[^"]*"' settings-template.json` shows `lessons-inject.py` under UserPromptSubmit | TRUE |
| 12 | A memory that never gets opened stops being trusted | README.md:136 | `memory-scores-surface.py`, `memory-confidence-surface.py` | both appear in the SessionStart block of `settings-template.json` | TRUE |
| 13 | Small scripts run before, during and after every action | README.md:159 | `settings-template.json` | `grep -o '"command": "[^"]*"' settings-template.json \| wc -l` = **65**; events SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostCompact, Stop all present | TRUE |
| 14 | A local tool server gives deterministic checks | README.md:152 | `plugins/kipi-core/kipi-mcp/src/kipi_mcp/server.py` | `grep -c '@mcp.tool' .../server.py` = **73** | TRUE |
| 15 | Scheduled jobs review, merge and report without you in the loop | README.md:153, :164 | committed launchd plists | `find . -name '*.plist' -not -path '*/.wt-*' -not -path '*/.git/*' \| wc -l` = **15**; `launchctl list \| grep -c -i kipi` = **14** loaded here | TRUE |
| 16 | All of it lives in one template repository and is copied to every project | README.md:164 | `kipi-update.sh`, `instance-registry.json` | `grep -c '"path"' instance-registry.json` = **28** registered copies | TRUE |
| 17 | The updater has a dry run that prints what would be copied and removed per copy | README.md:268 | `kipi` dispatcher `update` arm at `kipi:60`, usage at `kipi:10` | `./kipi help` prints the dry-run line; not executed (it walks 28 live checkouts) | TRUE |
| 18 | "The apply has no prompt of its own" | README.md:271 | `kipi-update.sh` | PR #310 review measured: no `read -p`, no `/dev/tty`, no confirm branch | TRUE |
| 19 | The destructive-command hook refuses the apply, and a person runs it | README.md:272 | the hook | measured 2026-09-06: the fleet apply was denied three times and printed a one-time hash (debrief section A). Note: the hook is NOT in this repo, see claim 25 | TRUE on this machine, not reproducible from a clone |
| 20 | A copy with uncommitted work refuses the sync | README.md:274 | `kipi-update.sh` dirty guard | measured 2026-09-06: consulting refused twice on a dirty `active-issue.json` (debrief section A, refusals 1 and 2) | TRUE |
| 21 | "Six roles are live right now" | README.md:280 | `instance-registry.json` | `grep -o '"role"[^,]*' instance-registry.json` returns nothing: the registry has no role field, and nothing enumerates roles | UNVERIFIED (missing check: a role field in the registry, or any script that counts roles) |
| 22 | "A handbook is in review as PR #306 ... It lands at `docs/README.md` when that review closes" | README.md:293 | PR #306 | `gh pr view 306 --json state,mergeable,updatedAt` = `OPEN`, `CONFLICTING`, last updated 2026-09-05T22:20:36Z | TRUE on the letter, stale in fact: the PR is parked at round 3 with two open spillover items |
| 23 | The install block gets you a running system | README.md:304 | npm + git clone | not run (would clone into a new dir); the three lines are standard and each names a real command | TRUE, but incomplete: it omits `./kipi install-jobs`, without which nothing the page claims about scheduled jobs happens (`kipi:22`) |
| 24 | Eight `/q-*` and `/wiring-check` slash commands | README.md:318-327 | none | `find . -type d -name commands -not -path '*/.git/*'` returns only three plugin dirs plus one misplaced dir; **no `commands/` at the repo root and none under `.claude/`**. `find . -name 'q-*.md' -path '*commands*'` returns one file, `plugins/kipi-core/skills/research-mode/commands/q-research.md`, which sits under `skills/` and is not a registered command. `q-system/.q-system/commands.md:3` says in its own words these are "conventions ... natural language triggers" | **FALSE** for 7 of the 8 rows (fixed) |
| 25 | The wider destructive guard "is a shipped hook script that a person wires per machine" | README.md:361 | none shipped | `find . -name 'destructive-op-deny*' -not -path '*/.git/*'` returns one file, `q-system/.q-system/tests/fixtures/destructive-op-deny.reference.sh`, mode `-rw-r--r--`. `grep -n 'HOOK=\|hook not found' plugins/kipi-core/scripts/install-capability-token.sh` shows `:19` targets a path in the user's home and `:51` gives up when it is absent: it patches, it never installs | **FALSE** (fixed) |
| 26 | `sudo` and force-push denied by default | README.md:361 | `settings-template.json` `permissions.deny` | `grep -n -A14 '"deny"' settings-template.json` shows nine Bash denials, including hard reset, rebase, `chmod 777` and piped installers, which the README under-claimed | TRUE but under-claimed (fixed) |
| 27 | Integrations table: Notion, Calendar, Gmail, Linear, Slack, Chrome, Apify, Reddit | README.md:336-344 | MCP servers | every one appears as a live MCP server or a named script in this session's server list; Reddit is `kipi_reddit_listing` / `kipi_reddit_thread` in the MCP server plus `reddit-build-radar` | TRUE |

**Counts: 27 claims. TRUE 20 (two of them under-claiming). FALSE 5. UNVERIFIED 2.**

The five FALSE: claims 4, 6, 24, 25, and the omission in 23. Claim 26 was true but understated the deny list, and is corrected in the same edit as 25.

---

## 4. The reverse list: capabilities the public surface never mentions

A README that under-claims is a mismatch too. Everything below is real and was invisible on the front page before this change.

| Capability | Measured by | Named on main before? |
|---|---|---|
| 23 CLI verbs | `grep -cE '^  [a-z][a-z0-9\|_-]*\)' kipi` = 23 | Only the sync verb, and only inside a mermaid edge label at README.md:257. The other 22 appear nowhere: `rollback`, `new`, `dev`, `sync-skills`, `push`, `promote`, `review`, `converge`, `jobs`, `work`, `install-jobs`, `dor`, `alert-triage`, `health`, `judgment`, `linear`, `check`, `migrate`, `cluster`, `list`, `lessons-run`, `home` |
| 73 MCP tools | `grep -c '@mcp.tool' plugins/kipi-core/kipi-mcp/src/kipi_mcp/server.py` = 73 | No. README.md:152 says "a local tool server" with no name and no count |
| 22 registered slash commands | `find plugins -path '*/commands/*.md' \| wc -l` = 22 | One, and under the wrong name (`/wiring-check`; the live name is `/kipi-core:wiring-check`). The nine `/prd-os:*` and six `/kipi-dsse:*` commands, which are the whole "Architect for itself" role at README.md:287, were absent |
| 65 hook entries + 7 in plugin `hooks.json` | `grep -o '"command": "[^"]*"' settings-template.json \| wc -l` = 65; `grep -c '"command"' plugins/*/hooks/hooks.json` sums to 14, two per hook, so 7 | No count anywhere |
| 6 plugins | `ls -d plugins/*/ \| wc -l` = 6 | None named. `.claude-plugin/marketplace.json` lists all six |
| 15 launchd jobs and the verb that installs them | `find . -name '*.plist' ... \| wc -l` = 15; `kipi:120` is the `install-jobs` arm | The jobs are described at README.md:153 as a capability. The command that makes them exist was not mentioned, so a reader following Install gets none of them |

Six real capability groups missing, well over the three the brief set as the threshold, so a "What else is in the box" section was added to the README rather than left in this file.

---

## 5. Fix list, ordered by how visible the lie is

1. **Commands table, README.md:318-327.** Seven of eight rows are slash commands that do not exist. This is the most actionable text on the page: a reader types it and gets nothing. Rewritten to separate the `/q-*` conventions from the 22 registered, namespaced plugin commands.
2. **Security bullet, README.md:361.** A reader making a trust decision is told a guard ships that does not. Rewritten to list the nine real denials by name and to say plainly that the wider guard is a non-executable test fixture no installer wires.
3. **Coverage honesty, README.md:74 and the mermaid edge at :82.** The false sentence sits inside the section whose entire thesis is coverage honesty, which makes it the most self-undermining line on the page. Rewritten to keep the deadline half, which is true, and to state that a budget truncation is recorded per source and does not move the verdict. The mermaid now draws the budget edge into FULL, which is what the code does.
4. **Document folders, README.md:63.** "Every markdown folder" overstates an eight-name allowlist. Rewritten to name the eight and point at the manifest.
5. **Install, README.md:310.** Added the one line for `./kipi install-jobs`, without which every scheduled-job claim on the page is unreachable from a clone.
6. **What else is in the box (new section).** The six under-claimed capability groups above.

Not fixed, and why:

- **Claim 21, "six roles are live right now" (README.md:280).** UNVERIFIED, not false. The registry has no role field, so nothing on disk can confirm or refute it. Missing check: a `role` key in `instance-registry.json`, or a script that enumerates roles. Prose left alone.
- **Claim 10, the misses ledger (README.md:107).** UNVERIFIED. Missing check: a test asserting that an unresolved capitalized name lands in the misses file. Prose left alone.
- **Claim 22, PR #306 (README.md:293).** Literally true, the PR is OPEN. It is also CONFLICTING and untouched since 2026-09-05, with `sp-c1c0464c` and `sp-c4d26576` open against it. Prose left alone because a stale-but-true sentence is not a false claim, but if the PR stays parked this line should say so.
- **`CLAUDE.md` has the same commands defect** and one of its own: it documents the morning brief as running at 07:00, while `q-system/.q-system/scripts/com.kipi.morning-brief.plist:56` is `Hour 7, Minute 40`. Out of scope for this branch (the brief scoped edits to README and tracked docs pages); captured rather than bundled.

---

## 6. Verification of the claims the README now makes

Every sentence changed above, re-checked by running the executable it now names.

| New claim | Command | Result |
|---|---|---|
| Eight declared folder names live in `knowledge-sources.json` | `grep -n 'folders' q-system/.q-system/knowledge-sources.json` | `:10 "folders": ["output","research","inputs","investigation","build","docs","notes","memory"]` |
| One function computes the verdict, in `knowledge_supply.py` | `grep -n 'verdict.*=.*FULL\|"FULL" if' q-system/.q-system/scripts/knowledge_supply.py` | one hit, `:2257` |
| A budget truncation does not move the verdict | `sed -n '2196,2201p'` and `sed -n '2245,2257p'` of the same file | `missing.append(cls)` is gated on `spec.get("required")`; `docs` is `required: false` at `knowledge-sources.json:28` |
| Nine Bash denials in `settings-template.json` `permissions.deny` | `grep -n -A14 '"deny"' settings-template.json` | lines 57-65: the two recursive-remove globs, `sudo*`, `git push --force*`, `git reset --hard*`, `git rebase*`, `chmod 777*`, `curl * \| bash*`, `wget * \| bash*` |
| The reference fixture is non-executable and no installer writes it | `find . -name 'destructive-op-deny*' -not -path '*/.git/*' -exec ls -la {} \;` then `grep -n 'HOOK=\|hook not found' plugins/kipi-core/scripts/install-capability-token.sh` | one file, `-rw-r--r--`; installer `:19` points at a path under the user's home and `:51` prints "hook not found ... left unpatched" |
| `find plugins -path '*/commands/*.md'` lists 22 | that command, piped to `wc -l` | 22 |
| Nine `/prd-os:*` and six `/kipi-dsse:*` | `find plugins/prd-os/commands plugins/kipi-dsse/commands -name '*.md'` | 9 and 6 (prd-os also carries a `.gitkeep`, not counted) |
| `com.kipi.morning-brief` fires at 07:40 | `grep -n -A3 'StartCalendarInterval' q-system/.q-system/scripts/com.kipi.morning-brief.plist` | `:56 Hour 7 Minute 40` |
| `./kipi install-jobs` exists and 15 plists are committed | `grep -nE '^  install-jobs\)' kipi` and `find . -name '*.plist' -not -path '*/.wt-*' -not -path '*/.git/*' \| wc -l` | `kipi:120`; 15 |
| 23 CLI verbs | `grep -cE '^  [a-z][a-z0-9\|_-]*\)' kipi` | 23 |
| 73 MCP tools | `grep -c '@mcp.tool' plugins/kipi-core/kipi-mcp/src/kipi_mcp/server.py` | 73 |
| 65 hook entries, plus 7 in the plugins | `grep -o '"command": "[^"]*"' settings-template.json \| wc -l`; `grep -c '"command"' plugins/*/hooks/hooks.json` | 65; 4+2+4+4 = 14 occurrences at two per hook = 7 |
| Six plugins | `ls -d plugins/*/ \| wc -l` | 6 |

One honest gap in the new prose: claim 19 (the destructive hook refuses the fleet apply) is TRUE on this machine and not reproducible from a clone, for exactly the reason the corrected security bullet now states. The two sentences are consistent with each other and both are on the page.

---

## 7. Spillover notes on README.md surfaced during this work

The ratchet raised three open notes when README.md was first edited. Addresses, not fixes:

- `sp-9427e29f` (PR #309 nits, one of which is the security bullet at the old README.md:350): the security half is fixed by this branch. Address after merge.
- `sp-076fac26` (dead `memory/working|weekly|monthly` layers) and `sp-206ec4ba` (`plugins/memory-lifecycle` re-created daily in travel-agent and lawyer-class instances): both unrelated to the public surface. Left for their owners.

