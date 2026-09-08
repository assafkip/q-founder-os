"""Regression coverage for the PRD gate lifecycle boundary."""

from __future__ import annotations

import importlib.util
import json
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
    assert "NONE executable" in out, out
    assert "1 registered" in out, out


def test_the_closeout_registrar_asks_for_regression_at_the_call_site(repo):
    """Pinned at the CALL SITE, not at gate_register's default.

    The default is `historical-receipt` and is named LEGACY_GATE_LIFECYCLE,
    which reads to every reviewer as "applies to rows written before the field
    existed". It was in fact the live default for every new registration. A test
    on the function's default would have passed throughout the outage.
    """
    src = (PLUGIN_ROOT.parent / "kipi-dsse" / "scripts" / "issue_runner.py").read_text()
    i = src.index("_prd_runner.gate_register(")
    call = src[i:i + 260]
    assert 'lifecycle="regression"' in call, (
        "the closeout registrar must name its lifecycle explicitly; "
        f"call site reads:\n{call}")


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
