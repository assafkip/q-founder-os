"""Regression coverage for the PRD gate lifecycle boundary."""

from __future__ import annotations

import importlib.util
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PRD_RUNNER = PLUGIN_ROOT / "scripts" / "prd_runner.py"
MIGRATE = PLUGIN_ROOT / "scripts" / "migrate_gate_lifecycle.py"


def run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PRD_RUNNER), "--repo-root", str(repo), *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".prd-os").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / ".prd-os" / "config.json").write_text(
        json.dumps(
            {
                "config_schema_version": 1,
                "prds_dir": ".prd-os/prds",
                "issues_dir": ".prd-os/issues",
                "findings_dir": ".prd-os/findings",
                "state_dir": ".claude/state",
            }
        )
    )
    return root


def write_gates(repo: Path, records: list[dict]) -> None:
    path = repo / ".prd-os" / "gates.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def test_list_filters_by_validated_lifecycle(repo):
    write_gates(
        repo,
        [
            {"gate_id": "current", "command": "true", "lifecycle": "regression"},
            {
                "gate_id": "receipt",
                "command": "false",
                "lifecycle": "historical-receipt",
            },
        ],
    )

    result = run(repo, "gates", "list", "--lifecycle", "regression")

    assert result.returncode == 0, result.stderr
    assert [record["gate_id"] for record in json.loads(result.stdout)] == ["current"]


def test_run_executes_only_regression_gates(repo):
    write_gates(
        repo,
        [
            {"gate_id": "receipt", "command": "false"},
            {"gate_id": "retired", "command": "false", "lifecycle": "retired"},
            {"gate_id": "external", "command": "false", "lifecycle": "external"},
            {"gate_id": "current", "command": "true", "lifecycle": "regression"},
        ],
    )

    result = run(repo, "gates", "run")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "current" in result.stdout
    assert "receipt" not in result.stdout
    assert "retired" not in result.stdout
    assert "external" not in result.stdout


def test_invalid_registry_lifecycle_fails_closed(repo):
    write_gates(
        repo,
        [{"gate_id": "bad", "command": "true", "lifecycle": "sometimes"}],
    )

    result = run(repo, "gates", "list")

    assert result.returncode == 2
    assert "invalid lifecycle" in result.stderr


def test_gate_register_validates_and_persists_lifecycle(repo):
    spec = importlib.util.spec_from_file_location("prd_runner_lifecycle", PRD_RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PRD_RUNNER.parent))
    spec.loader.exec_module(module)
    cfg = module.load_config(repo)

    registered = module.gate_register(
        cfg,
        prd_id="prd-x",
        issue_id="issue-x",
        command="true",
        lifecycle="regression",
    )

    record = json.loads((repo / ".prd-os" / "gates.jsonl").read_text())
    assert registered["registered"] is True
    assert record["lifecycle"] == "regression"
    with pytest.raises(ValueError, match="invalid gate lifecycle"):
        module.gate_register(
            cfg,
            prd_id="prd-x",
            issue_id="issue-y",
            command="true",
            lifecycle="sometimes",
        )


@pytest.mark.parametrize("cmd", [
    # The two shapes that live specs in this repo actually use. Both are refused by
    # a raw `cmd.split()[0]` probe and both are run fine by bash.
    "PYTHONPATH=plugins/kipi-core/kipi-mcp/src python3 -m pytest -q tests/test_paths.py",
    "PYTHONPATH=. python3 -m pytest plugins/prd-os/tests -q",
    "(cd plugins/prd-os && python3 -m pytest -q)",
    "FOO=1 BAR=2 true",
    "{ true; }",
])
def test_a_command_bash_can_run_is_not_called_prose(cmd):
    """The door must not refuse a shape the shell executes (PR #330 review, MAJOR 1).

    This is not hypothetical and it is not cosmetic. `issue_runner` RUNS the
    bypass_check and requires exit 0 BEFORE it registers, so by the time this guard
    sees the command it is PROVEN runnable -- and issue_runner turns any raise here
    into a hard `cannot close`. Census over all 204 decoded bypass_checks in
    .prd-os/issues/: 16 refused, 2 of them this false-positive class. An unattended
    closeout died on a check that had just gone green, blaming prose.

    The first token of `PYTHONPATH=x python3 ...` is an ASSIGNMENT, and of
    `(cd x && y)` is shell GRAMMAR. Neither is a command name.
    """
    _runner_module()._reject_unrunnable_gate(cmd)


def test_a_NEGATED_prose_command_is_refused(repo):
    """`!` inverts, so accepting it makes a gate that passes forever.

    Round 3 of the PR #330 review found this hole, which I opened myself by
    grouping `!` with `(` and `{` as "shell grammar, bash already parsed it".
    The difference is the direction of failure: prose inside a subshell exits 127
    and the gate goes RED loudly, but `! <prose>` runs the same missing command,
    gets 127, and the negation turns it into exit 0. In an append-only registry
    that is a permanent green gate that never executed anything.
    """
    mod = _runner_module()
    with pytest.raises(ValueError, match="does not start with a runnable command"):
        mod._reject_unrunnable_gate("! check:the ledger is append-only")
    # A BARE `!` IS REFUSED ON BOTH PLATFORMS, BY DIFFERENT GUARDS, and pinning
    # either one is how this test went red in CI while passing locally.
    #
    #   macOS, bash 3.2.57  : `bash -n -c '!'` is a SYNTAX ERROR
    #                         -> step 1 refuses with "not valid shell"
    #   CI, Linux bash 5.x  : `bash -n -c '!'` PARSES
    #                         -> the negation branch refuses with "only a negation"
    #
    # Measured, after CI failed on exactly this: 'Expected regex: not valid shell /
    # Actual message: gate command is only a negation'. The previous comment here
    # called that branch unreachable belt-and-braces. That was WRONG -- on the
    # platform CI actually runs, it is the live guard, and the version of this
    # comment that called it dead code would have justified deleting it.
    #
    # So the assertion is on the OUTCOME (refused, with a reason naming the input)
    # rather than on which of the two doors closed.
    with pytest.raises(ValueError) as bare:
        mod._reject_unrunnable_gate("!")
    assert "not valid shell" in str(bare.value) or "only a negation" in str(bare.value), \
        f"a bare negation must be refused with a reason, got: {bare.value}"
    # and a genuinely negated REAL command still passes, so the fix is not a ban
    mod._reject_unrunnable_gate("! false")


def test_a_run_that_executed_nothing_never_prints_the_green_sentence(repo):
    """The last line must not contradict the WARN three lines above it.

    It printed "all 0 regression gates green" directly under a WARN saying
    nothing executed. That is the ASK-1038 sentence itself, still present, under
    its own alarm -- and a reader who scrolls to the end, or a script that greps
    the last line, sees only the reassurance.
    """
    write_gates(repo, [{"gate_id": "inert", "command": "exit 1",
                        "lifecycle": "historical-receipt"}])
    result = run(repo, "gates", "run")
    out = result.stdout + result.stderr
    assert "NO regression gate executed" in out, out
    assert "regression gates green" not in out, (
        "the run executed nothing and still printed the green sentence:\n" + out)


def test_prose_is_STILL_refused_after_the_assignment_fix():
    """The negative half: widening the door must not open it (MAJOR 1 fix control).

    An assignment-looking prefix must not become a way to smuggle prose past the
    guard, and prose that merely follows an assignment is still prose.
    """
    mod = _runner_module()
    for bad in ("check:the ledger is append-only",
                "PYTHONPATH=. check:the ledger is append-only",
                "asserting the gate runs"):
        with pytest.raises(ValueError, match="does not start with a runnable command"):
            mod._reject_unrunnable_gate(bad)
    # An assignment with no command runs no check, and says so in its own words.
    with pytest.raises(ValueError, match="only environment assignments"):
        mod._reject_unrunnable_gate("PYTHONPATH=.")


def test_re_registering_an_existing_gate_is_a_no_op_not_a_raise(repo):
    """Re-close must stay possible (PR #330 review, MAJOR 2).

    gate_id is issue_id + sha256(command), so re-closing an issue with the same
    bypass_check resolves to an existing row. Validating the command BEFORE the
    idempotency lookup turned that no-op into a raise, and issue_runner converts
    any raise into `cannot close` -- breaking a workflow issue_runner itself
    documents ("spec closed once, reopened, amended, closed again").

    Registered here with a command the door accepts, then re-registered, which is
    the path a real re-close takes.
    """
    module = _runner_module()
    cfg = module.load_config(repo)
    first = module.gate_register(cfg, prd_id="prd-x", issue_id="issue-recl",
                                 command="true", lifecycle="regression")
    assert first["registered"] is True
    again = module.gate_register(cfg, prd_id="prd-x", issue_id="issue-recl",
                                 command="true", lifecycle="regression")
    assert again == {"gate_id": first["gate_id"], "registered": False}


def test_a_lifecycle_conflict_names_its_recovery(repo):
    """A dead-end error at 3am is a defect (PR #330 review, MAJOR 2).

    Every gate this fleet's closeout wrote before the lifecycle fix took
    LEGACY_GATE_LIFECYCLE, so the FIRST re-close of any such issue hits this
    branch. The recovery exists but lives outside the closeout flow, so the
    message has to carry it.
    """
    module = _runner_module()
    cfg = module.load_config(repo)
    module.gate_register(cfg, prd_id="prd-x", issue_id="issue-conf",
                         command="true", lifecycle="historical-receipt")
    with pytest.raises(ValueError) as exc:
        module.gate_register(cfg, prd_id="prd-x", issue_id="issue-conf",
                             command="true", lifecycle="regression")
    msg = str(exc.value)
    assert "migrate_gate_lifecycle.py" in msg
    # THE FLAG, not just the filename (review of PR #330 round 2, MINOR 1). The
    # first version matched the substring and stayed green against a command that
    # exits 2, because --registry is required=True in that script. A recovery
    # pointer is only a recovery if it runs.
    assert "--registry" in msg, f"recovery command omits a required flag:\n{msg}"
    quoted = msg.split("`")[1]
    for flag in ("--registry", "--regression", "--apply"):
        assert flag in quoted, f"{flag} missing from the printed command: {quoted}"


def test_gate_register_ACTUALLY_CALLS_the_unrunnable_guard(repo):
    """The guard is WIRED, not merely present. This is the wiring half.

    The four tests below drive `_reject_unrunnable_gate` DIRECTLY, so all four stay
    green even when nothing calls it. Measured 2026-09-07 while carrying this guard
    upstream: deleting the single `_reject_unrunnable_gate(command)` line from
    `gate_register` left the whole file green at 17 passed. A guard nobody invokes
    reads exactly like one that works, and the registry it protects is append-only,
    so a bad row is close to permanent.

    This one goes through the real entry point with the exact shape that happened
    seven times -- prose where the command goes -- and it is the test that dies if
    the call site is ever dropped again.
    """
    spec = importlib.util.spec_from_file_location("prd_runner_wiring", PRD_RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PRD_RUNNER.parent))
    spec.loader.exec_module(module)
    cfg = module.load_config(repo)

    with pytest.raises(ValueError, match="does not start with a runnable command"):
        module.gate_register(
            cfg,
            prd_id="prd-x",
            issue_id="issue-wiring",
            command="check:the ledger is append-only",
            lifecycle="regression",
        )

    # AND IT REFUSED BEFORE WRITING. A guard that raises after the append still
    # leaves the permanent row it exists to prevent.
    gates = repo / ".prd-os" / "gates.jsonl"
    assert not gates.exists() or "issue-wiring" not in gates.read_text()


def test_migration_classifies_every_record_without_deleting_receipts(repo):
    write_gates(
        repo,
        [
            {"gate_id": "old", "command": "true"},
            {"gate_id": "current", "command": "true"},
            {"gate_id": "remote", "command": "true"},
            {"gate_id": "gone", "command": "true"},
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(MIGRATE),
            "--registry",
            str(repo / ".prd-os" / "gates.jsonl"),
            "--regression",
            "current",
            "--external",
            "remote",
            "--retired",
            "gone",
            "--apply",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    records = [
        json.loads(line)
        for line in (repo / ".prd-os" / "gates.jsonl").read_text().splitlines()
    ]
    assert [record["gate_id"] for record in records] == [
        "old",
        "current",
        "remote",
        "gone",
    ]
    assert [record["lifecycle"] for record in records] == [
        "historical-receipt",
        "regression",
        "external",
        "retired",
    ]


def test_incremental_migration_preserves_existing_lifecycles(repo):
    write_gates(
        repo,
        [
            {"gate_id": "current", "command": "true", "lifecycle": "regression"},
            {"gate_id": "gone", "command": "true", "lifecycle": "retired"},
            {"gate_id": "remote", "command": "true"},
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(MIGRATE),
            "--registry",
            str(repo / ".prd-os" / "gates.jsonl"),
            "--external",
            "remote",
            "--apply",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    records = [
        json.loads(line)
        for line in (repo / ".prd-os" / "gates.jsonl").read_text().splitlines()
    ]
    assert [record["lifecycle"] for record in records] == [
        "regression",
        "retired",
        "external",
    ]


# ---------------------------------------------------------------------------
# ASK-1038: the run half went inert for 29 days and reported success
# ---------------------------------------------------------------------------


def test_a_failing_regression_gate_actually_turns_the_run_red(repo):
    """POSITIVE CONTROL. The check nobody had, and its absence cost 29 days.

    Every other test here asserts which gates are SELECTED. None asserted that a
    selected gate can fail the run. So when the closeout registrar started
    writing every gate as historical-receipt, the executed set went to zero, the
    command printed "all 0 regression gates green" and exited 0, and the suite
    stayed green because nothing ever demanded that a red gate produce a red run.
    A gate set that cannot fail is decoration.
    """
    write_gates(repo, [{"gate_id": "boom", "command": "exit 7",
                        "lifecycle": "regression"}])
    result = run(repo, "gates", "run")
    assert result.returncode != 0, (
        "a failing regression gate MUST fail the run; got "
        f"rc={result.returncode}\n{result.stdout}\n{result.stderr}")
    assert "boom" in (result.stdout + result.stderr)


def test_a_registry_with_nothing_executable_is_not_reported_as_green(repo):
    """A count of zero is an anomaly, not a pass.

    "all 0 regression gates green" is TRUE and reads as reassurance, which is
    exactly how it survived. With a non-empty registry and an empty executed
    set, the run must say so out loud.
    """
    write_gates(repo, [{"gate_id": "inert", "command": "exit 1",
                        "lifecycle": "historical-receipt"}])
    result = run(repo, "gates", "run")
    out = result.stdout + result.stderr
    # "executable" was the wrong word and is now "executed": these gates ARE
    # executable, they simply did not run. The distinction is the whole finding.
    assert "[WARN]" in out, out
    assert "NONE executed" in out, out
    assert "1 registered" in out, out


def test_a_registry_whose_gates_are_ALL_SKIPPED_is_not_reported_as_green(repo):
    """The other way to execute nothing (review of PR #330 round 2, MINOR 2).

    The WARN keyed on `len(records) == 0`. A registry whose regression gates are
    all skipped as self-referential has records NON-empty and zero commands run,
    so it printed "all 1 regression gates green" at exit 0 with nothing executed --
    the identical sentence ASK-1038 was written to stop. `skipped_self_ref` was
    already being counted and never read.

    No producer emits this shape today (0 of 204 bypass_checks in .prd-os/issues
    are self-referential), which is precisely the condition under which a hole
    survives unnoticed.
    """
    write_gates(repo, [{"gate_id": "selfref",
                        "command": "python3 plugins/prd-os/scripts/prd_runner.py gates run",
                        "lifecycle": "regression"}])
    result = run(repo, "gates", "run")
    out = result.stdout + result.stderr
    assert "[WARN]" in out, out
    assert "NONE executed" in out, out
    assert "self-referential" in out, out


def test_the_closeout_registrar_asks_for_regression_at_the_call_site(repo):
    """Pinned at the CALL SITE, not at gate_register's default.

    The default is `historical-receipt` and is named LEGACY_GATE_LIFECYCLE,
    which reads to every reviewer as "applies to rows written before the field
    existed". It was in fact the live default for every new registration. A test
    on the function's default would have passed throughout the outage.

    EVERY call site, not `src.index(...)` (review of PR #330, MINOR 3). The first
    version inspected only the first match plus 260 characters, so a SECOND
    registrar added later with no lifecycle kept it green. There is exactly one
    call site today, which is what made that a latent hole rather than a live one
    -- and exactly the condition under which nobody notices.

    THE ARGUMENT LIST IS PARSED, NOT WINDOWED (review of PR #330 round 2, MINOR 3).
    The first fix replaced `src.index(...)` with every match but kept a 260-char
    forward window per match, so two ADJACENT registrars fall inside each other's
    window and a lifecycled second call donates its `lifecycle="regression"` to an
    unlifecycled first. Reproduced: 2 call sites, first one unlifecycled, verdict
    GREEN. Adjacency is the likeliest arrangement for the very second registrar this
    test exists to catch, so `ast` removes the window rather than widening it.
    """
    src = (PLUGIN_ROOT.parent / "kipi-dsse" / "scripts" / "issue_runner.py").read_text()

    def _is_gate_register(node):
        f = node.func
        return (isinstance(f, ast.Attribute) and f.attr == "gate_register") or (
            isinstance(f, ast.Name) and f.id == "gate_register")

    calls = [n for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call) and _is_gate_register(n)]
    assert calls, "no gate_register call site found at all -- the test lost its subject"
    bad = []
    for n in calls:
        kw = {k.arg: k for k in n.keywords if k.arg}
        val = kw.get("lifecycle")
        ok = (val is not None
              and isinstance(val.value, ast.Constant)
              and val.value.value == "regression")
        if not ok:
            bad.append(f"line {n.lineno}: lifecycle="
                       f"{ast.unparse(val.value) if val is not None else '<absent>'}")
    assert not bad, (
        f"{len(bad)} of {len(calls)} closeout registrar call site(s) do not pass "
        'lifecycle="regression", so they take LEGACY_GATE_LIFECYCLE and `gates run` '
        "filters them out:\n" + "\n".join(bad))


# ---------------------------------------------------------------------------
# ASK-1040: prose in the command slot, accepted 47 times without a word
# ---------------------------------------------------------------------------


def _runner_module():
    spec = importlib.util.spec_from_file_location("pr_mod", PRD_RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("prose", [
    "check:the brake never leaks into the test suite",
    "check:adding a demo sentence fails the approval test",
    "asserting the X body stays under the ceiling",
])
def test_prose_in_the_command_slot_is_refused(prose):
    """The class that actually happened, seven times, verbatim from the registry.

    Somebody wrote a DESCRIPTION of the check where the check goes. The shell
    was then asked to run `check:the` and exited 127, and every one of those was
    recorded as permanent protection.
    """
    mod = _runner_module()
    with pytest.raises(ValueError, match="does not start with a runnable command"):
        mod._reject_unrunnable_gate(prose)


def test_a_shell_syntax_error_is_refused():
    """`bash -n` is more permissive than it looks, and that is worth pinning.

    The first draft of this test used an unterminated heredoc, assuming that was
    a syntax error. `bash -n -c` accepts it (rc=0), so the test failed and the
    CODE was fine. Pinned here with a construct bash genuinely rejects, so the
    next reader does not re-derive that the heredoc case is NOT covered.
    """
    mod = _runner_module()
    with pytest.raises(ValueError, match="not valid shell"):
        mod._reject_unrunnable_gate("if true; then")


def test_an_empty_command_is_refused():
    mod = _runner_module()
    with pytest.raises(ValueError, match="runs nothing"):
        mod._reject_unrunnable_gate("   ")


@pytest.mark.parametrize("good", [
    "cd q-consult && python3 -m pytest pipeline/tests/test_sameness.py -q",
    "bash -c '! grep -rn VOICE_SOURCE_GLOBS q-consult/pipeline/*.py'",
    "python3 -c \"import sys; sys.exit(0)\"",
])
def test_real_gate_commands_are_not_false_positived(good):
    """THE CONTROL THAT MATTERS MORE THAN THE REFUSAL.

    A door check that rejects valid gates would push people to stop registering
    them, which is worse than the prose it prevents. Verified 2026-08-24 against
    the live registry: all 34 regression gates pass this, 0 false positives.
    """
    _runner_module()._reject_unrunnable_gate(good)
