#!/usr/bin/env bash
# A LIVE index.lock is another writer, not debris: the updater waits for it,
# says which step is waiting, retries a commit that died on it, and refuses
# the instance only when the lock outlives the bound.
#
# 2026-09-06 14:30, consulting: the q-system commit landed, the config commit
# died seconds later on "Unable to create '.git/index.lock': File exists",
# and the instance was abandoned half-delivered. The holder was a peer
# session's `git status`, which takes that lock for a fraction of a second to
# refresh the index. The stale-lock deletion at the top of the instance loop
# only covers a crashed writer's leftover (sp-2c1bcc3f); a live writer needs a
# wait, not a delete (sp-523c1a25). The run marker written for the hook's
# half (sp-9306036e) is what lets this test hold the lock at exactly the
# right moment: the holder waits for the marker, then takes the lock, so the
# first index write of the run meets a live lock every time.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
fail() { echo "FAIL: $1" >&2; exit 1; }
G() { git -c user.email=t@t.t -c user.name=test -c commit.gpgsign=false "$@"; }

# ------------------------------------------------------------------ the fixture
# The same skeleton-plus-instance shape test-kipi-update-system-state-commit.sh
# builds, minus its dirty-tree provocations: one clean instance whose
# q-system/tracked.md differs from the skeleton's, so the run has exactly one
# thing to stage and commit.
build() {
  local work="$1" sk="$work/skel" inst="$work/inst"
  mkdir -p "$sk/q-system/.q-system/scripts" "$sk/q-system/.q-system/state" \
           "$sk/q-system/hooks" "$sk/plugins/demo" "$sk/.claude/rules"
  for f in kipi-update.sh kipi-update-preserve-scan.py kipi-update-deletion-guard.py \
           validate-separation.py; do
    cp "$ROOT/$f" "$sk/$f"
  done
  # The two gates the updater is fail-closed on, plus the replica-divergence
  # gate when the checkout carries it (it disarms on this one-instance
  # population either way; test-kipi-update-system-state-commit.sh runs
  # without it).
  for f in propagation-leak-gate.py containment-targets.py fleet-replica-divergence.py; do
    if [ -f "$ROOT/q-system/.q-system/scripts/$f" ]; then
      cp "$ROOT/q-system/.q-system/scripts/$f" "$sk/q-system/.q-system/scripts/$f"
    fi
  done
  cp "$ROOT/q-system/hooks/auto-commit.py" "$sk/q-system/hooks/auto-commit.py"
  cat > "$sk/q-system/.q-system/state/propagation-leak-baseline.json" <<'JSON'
{
  "schema_version": 1,
  "blocking_classes": ["case_proof_gap", "client_identity", "dated_interaction",
                       "pricing", "relationship", "source_identity",
                       "sourced_interaction"],
  "classifier_sha256": null,
  "entries": []
}
JSON
  printf 'generic skeleton content\n' > "$sk/q-system/tracked.md"
  printf 'plugin v2\n' > "$sk/plugins/demo/content.txt"
  printf '# demo rule\n' > "$sk/.claude/rules/demo.md"
  ( cd "$sk" && G init -q -b main && G add -A -f && G commit -qm skel )
  printf '{"instances":[{"name":"testinst","path":"%s","subtree_prefix":"q-system","type":"subtree"}]}\n' \
    "$inst" > "$sk/instance-registry.json"

  mkdir -p "$inst/q-system/.q-system" "$inst/plugins/demo" "$inst/.claude"
  printf 'instance state\n' > "$inst/q-system/tracked.md"
  printf 'plugin v1\n' > "$inst/plugins/demo/content.txt"
  ( cd "$inst" && G init -q -b main && G add -A -f && G commit -qm inst )
}

# The lock holder. It waits for the updater's run marker (written after the
# stale-lock cleanup, before any index write), takes index.lock, and releases
# it only after the updater has SAID it is waiting. That handshake is what
# makes the green case a test of the wait path rather than of timing: a
# build that never waits never prints the line, so the lock is never released
# and the run fails.
hold_lock() {
  local inst="$1" log="$2" release="$3"
  local marker="$inst/.git/kipi-update.run" lock="$inst/.git/index.lock"
  local spins=0
  while [ ! -f "$marker" ]; do
    sleep 0.1
    spins=$((spins + 1))
    [ "$spins" -gt 600 ] && return 0
  done
  : > "$lock"
  if [ "$release" = "after-wait-line" ]; then
    spins=0
    while ! grep -q "waiting for index.lock at" "$log" 2>/dev/null; do
      sleep 0.1
      spins=$((spins + 1))
      [ "$spins" -gt 600 ] && return 0
    done
    sleep 1
    rm -- "$lock"
  fi
}

# ------------------------------------------------------------------ property 1
assert_a_live_lock_is_waited_out_and_the_sync_lands() {
  local work sk inst; work="$(mktemp -d)"; sk="$work/skel"; inst="$work/inst"
  build "$work"
  : > "$work/out"
  hold_lock "$inst" "$work/out" after-wait-line &
  local holder=$!
  KIPI_UPDATE_LOCK_WAIT_S=20 bash "$sk/kipi-update.sh" >"$work/out" 2>&1 || true
  wait "$holder" || true

  grep -q "waiting for index.lock at q-system sync staging" "$work/out" || \
    fail "the updater never said it was waiting: $(tail -n 20 "$work/out")"
  grep -q "Updated: 1" "$work/out" || \
    fail "the sync did not land after the lock cleared: $(tail -n 20 "$work/out")"
  # The q-system commit is followed by the config+plugins commit in this
  # fixture, so the sync commit is in the log, not necessarily at HEAD.
  G -C "$inst" log --format=%s | grep -q "sync q-system from skeleton" || \
    fail "the q-system sync commit is not in the instance history: $(G -C "$inst" log --format=%s)"
  [ ! -f "$inst/.git/kipi-update.run" ] || fail "the run marker survived a successful run"
  [ ! -f "$inst/.git/index.lock" ] || fail "index.lock survived the run"
  echo "PASS: a live index.lock is waited out, the step is named, and the sync lands"
}

# ------------------------------------------------------------------ property 2
assert_a_lock_past_the_bound_refuses_the_instance_by_name() {
  local work sk inst; work="$(mktemp -d)"; sk="$work/skel"; inst="$work/inst"
  build "$work"
  : > "$work/out"
  hold_lock "$inst" "$work/out" never &
  local holder=$!
  KIPI_UPDATE_LOCK_WAIT_S=3 bash "$sk/kipi-update.sh" >"$work/out" 2>&1 || true
  wait "$holder" || true
  rm -f -- "$inst/.git/index.lock"

  grep -q "index.lock held past 3s at q-system sync staging" "$work/out" || \
    fail "the refusal does not name the bound and the step: $(tail -n 20 "$work/out")"
  grep -q "Failed:  1" "$work/out" || \
    fail "a lock past the bound did not fail the instance: $(tail -n 20 "$work/out")"
  local subject; subject="$(G -C "$inst" log -1 --format=%s)"
  [ "$subject" = "inst" ] || fail "a refused run left a commit behind: $subject"
  [ ! -f "$inst/.git/kipi-update.run" ] || fail "the run marker survived a refused run"
  echo "PASS: a lock past the bound refuses the instance, names the step, commits nothing"
}

# ------------------------------------------------------------------ property 3
# The mutant. Redefine wait_for_index_lock as a no-op just before the main loop
# (a later bash definition wins) and re-run the green case: the holder never
# sees the waiting line, never releases, and the first index write dies on the
# lock. If this stays green, property 1 was passing on timing, not on the wait.
assert_without_the_wait_the_green_case_goes_red() {
  local work sk inst; work="$(mktemp -d)"; sk="$work/skel"; inst="$work/inst"
  build "$work"
  python3 - "$sk/kipi-update.sh" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
needle = "while IFS='|' read -r name path prefix itype declared; do"
assert text.count(needle) == 1, "main loop header moved; update the mutant"
text = text.replace(needle, "wait_for_index_lock() { return 0; }\n" + needle)
open(path, "w", encoding="utf-8").write(text)
PY
  : > "$work/out"
  hold_lock "$inst" "$work/out" after-wait-line &
  local holder=$!
  KIPI_UPDATE_LOCK_WAIT_S=20 bash "$sk/kipi-update.sh" >"$work/out" 2>&1 || true
  kill "$holder" 2>/dev/null || true
  wait "$holder" 2>/dev/null || true
  rm -f -- "$inst/.git/index.lock"

  if grep -q "Updated: 1" "$work/out"; then
    fail "the mutant without the wait still synced; property 1 is decoration"
  fi
  grep -q "Failed:  1" "$work/out" || \
    fail "the mutant neither synced nor failed the instance: $(tail -n 20 "$work/out")"
  echo "PASS: removing the wait makes the live-lock case red (the wait is load-bearing)"
}

# ------------------------------------------------------------------ property 4
# The retry half, exercised directly. The helper functions are extracted from
# the updater's own text, never restated here, so the test cannot drift from
# the code it pins (floor: the extraction is non-empty).
assert_a_commit_that_dies_on_the_lock_is_retried_and_other_errors_are_not() {
  local work; work="$(mktemp -d)"
  sed -n '/^index_lock_path() {$/,/^}$/p;/^wait_for_index_lock() {$/,/^}$/p;/^retry_on_index_lock() {$/,/^}$/p' \
    "$ROOT/kipi-update.sh" > "$work/helpers.sh"
  grep -q '^retry_on_index_lock() {' "$work/helpers.sh" || fail "could not extract retry_on_index_lock from kipi-update.sh"
  grep -q '^wait_for_index_lock() {' "$work/helpers.sh" || fail "could not extract wait_for_index_lock from kipi-update.sh"
  mkdir -p "$work/repo" && ( cd "$work/repo" && G init -q -b main )

  cat > "$work/case.sh" <<'SH'
set -euo pipefail
source "$1/helpers.sh"
LOCK_WAIT_S=5
LOCK_RETRY_MAX=3
counter="$1/count"
: > "$counter"
flaky_commit() {
  local repo="$1"
  echo x >> "$counter"
  if [ "$(wc -l < "$counter" | tr -d ' ')" -lt 3 ]; then
    echo "fatal: Unable to create '$repo/.git/index.lock': File exists." >&2
    return 128
  fi
  return 0
}
other_failure() {
  echo x >> "$counter"
  echo "error: pathspec 'nope' did not match any file(s) known to git" >&2
  return 1
}
case "$3" in
  flaky) retry_on_index_lock "$2" "unit commit" flaky_commit "$2" ;;
  other) retry_on_index_lock "$2" "unit commit" other_failure ;;
esac
SH
  local out rc
  out="$(bash "$work/case.sh" "$work" "$work/repo" flaky 2>&1)" && rc=0 || rc=$?
  [ "$rc" -eq 0 ] || fail "a commit that succeeds on attempt 3 returned rc=$rc: $out"
  [ "$(wc -l < "$work/count" | tr -d ' ')" -eq 3 ] || fail "expected 3 attempts, got $(wc -l < "$work/count")"
  echo "$out" | grep -q "attempt 1 of 3" || fail "attempt 1 was not logged: $out"
  echo "$out" | grep -q "attempt 2 of 3" || fail "attempt 2 was not logged: $out"

  out="$(bash "$work/case.sh" "$work" "$work/repo" other 2>&1)" && rc=0 || rc=$?
  [ "$rc" -eq 1 ] || fail "a non-lock failure did not return its own rc (got $rc): $out"
  [ "$(wc -l < "$work/count" | tr -d ' ')" -eq 1 ] || fail "a non-lock failure was retried"
  echo "$out" | grep -q "did not match" || fail "the original stderr was swallowed: $out"
  echo "PASS: a commit that dies on the live lock is retried up to the cap; any other error returns on attempt 1"
}

assert_a_commit_that_dies_on_the_lock_is_retried_and_other_errors_are_not
assert_a_live_lock_is_waited_out_and_the_sync_lands
assert_a_lock_past_the_bound_refuses_the_instance_by_name
assert_without_the_wait_the_green_case_goes_red
