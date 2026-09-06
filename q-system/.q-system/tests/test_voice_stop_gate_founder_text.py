"""Only text the FOUNDER typed is his request, and a route lane is enforced only
where one is installed.

Ported 2026-09-06 from the one instance that ran these live
(automation/test_harness_injection_is_not_the_founder.py and
test_founder_typed_text_rejects_peer_messages.py there), because every fleet
sync replaced that instance's gate with a skeleton copy that had none of this
and its pre-commit went red until the next restore (sp-745f5962). The record
shapes are the ones the harness actually writes: flags TOP-LEVEL on the record,
content as a list of text blocks.

The lane tests build a fake `q-consult/pipeline` package in a temp root and
point the gate's INSTANCE_ROOT at it, so the three outcomes of `_route_context`
(absent, broken, present) are each exercised without the real lane.
"""
import importlib.util
import json
import pathlib
import textwrap

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
GATE = REPO / "q-system" / ".q-system" / "scripts" / "voice-stop-gate.py"


def _load():
    spec = importlib.util.spec_from_file_location("voice_stop_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vsg = _load()

FOUNDER_MESSAGE = "Explain simply no tables."
SKILL_BODY = (
    "# Workflow authoring reference\n\n"
    "A workflow structures work across many agents.\n\n"
    "compose novel harnesses when the task calls for it\n\n"
    "To iterate on a workflow, edit that file with Write/Edit and re-invoke "
    "Workflow with scriptPath instead of resending the full script.\n"
)
PEER = (
    '<cross-session-message from="uds:/tmp/cc-socks/41361.sock" '
    'from-name="voice loop" from-mode="bypass">\n'
    'If you add a `social-comment` surface, its pointers are now verified.\n'
    '</cross-session-message>'
)


def _record(text, role="user", **flags):
    record = {
        "type": "user",
        "isSidechain": False,
        "userType": "external",
        "message": {"role": role, "content": [{"type": "text", "text": text}]},
    }
    record.update(flags)
    return record


@pytest.fixture
def transcript(tmp_path):
    def build(records):
        path = tmp_path / "transcript.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
        return str(path)
    return build


# --- the founder's words vs the harness's ---------------------------------

def test_a_skill_body_is_not_the_founders_request(transcript):
    path = transcript([
        _record(FOUNDER_MESSAGE),
        _record(SKILL_BODY, isMeta=True, turnCompanion=True),
    ])
    assert vsg.find_final_user_text(path) == FOUNDER_MESSAGE


@pytest.mark.parametrize("flags", [
    {"isMeta": True},
    {"turnCompanion": True},
    {"isMeta": True, "turnCompanion": True},
])
def test_either_flag_alone_is_enough(transcript, flags):
    path = transcript([_record(FOUNDER_MESSAGE), _record(SKILL_BODY, **flags)])
    assert vsg.find_final_user_text(path) == FOUNDER_MESSAGE


def test_stop_hook_feedback_is_not_his_words_either(transcript):
    path = transcript([
        _record(FOUNDER_MESSAGE),
        _record("Stop hook feedback:\nvoice-stop-gate: route request is unsupported",
                isMeta=True),
    ])
    assert vsg.find_final_user_text(path) == FOUNDER_MESSAGE


def test_an_unflagged_user_turn_is_still_read(transcript):
    """The negative control: a filter that swallows his real messages is worse
    than the bug, the gate would look green while measuring nothing."""
    path = transcript([
        _record("first message"),
        _record(SKILL_BODY, isMeta=True, turnCompanion=True),
        _record("write me a linkedin post about the audit"),
    ])
    assert vsg.find_final_user_text(path) == "write me a linkedin post about the audit"


def test_flags_are_read_from_the_record_not_the_message(transcript):
    """A flag INSIDE `message` must not count: that is not where the harness puts
    it, and honouring it there lets a crafted message hide from the gate."""
    record = _record(SKILL_BODY)
    record["message"]["isMeta"] = True
    path = transcript([_record(FOUNDER_MESSAGE), record])
    assert vsg.find_final_user_text(path) == SKILL_BODY.strip()


def test_a_cross_session_message_is_rejected_whole():
    assert vsg.founder_typed_text(PEER) == ""


def test_the_founders_own_words_still_survive():
    typed = "write this as a linkedin comment with voice loop"
    assert vsg.founder_typed_text(typed) == typed


def test_a_peer_block_inside_a_turn_is_stripped_not_kept():
    assert "social-comment" not in vsg.founder_typed_text("ok\n\n" + PEER)


def test_a_command_invocation_is_truncated_at_the_marker():
    typed = "make it shorter <command-name>/foo</command-name>\n# Foo\n\nlong skill body"
    assert vsg.founder_typed_text(typed) == "make it shorter"


def test_assistant_text_is_unaffected(transcript):
    """`_walk_transcript` grew a parameter; its other caller must not change."""
    path = transcript([
        _record(FOUNDER_MESSAGE),
        _record("here is the draft", role="assistant"),
    ])
    assert "here is the draft" in vsg.find_final_assistant_text(path)


# --- the route lane: absent, broken, present ------------------------------

def _fake_lane(root, broken=False, status="NOT_ROUTED"):
    pkg = root / "q-consult" / "pipeline"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    if broken:
        (pkg / "route_classifier.py").write_text("raise ImportError('half-installed lane')\n")
        for name in ("route_contract", "audit_only_routes", "route_registry"):
            (pkg / f"{name}.py").write_text("")
        return pkg
    (pkg / "route_classifier.py").write_text(textwrap.dedent(f"""
        import collections
        NOT_ROUTED = "NOT_ROUTED"
        ROUTE = "ROUTE"
        Result = collections.namedtuple("Result", "status surface channel reason")
        def classify(request):
            return Result({status!r}, "linkedin_post", "linkedin", "fixture")
    """))
    (pkg / "route_contract.py").write_text("")
    (pkg / "audit_only_routes.py").write_text(textwrap.dedent("""
        class AuditOnlyRouteError(Exception):
            pass
        def routes():
            return []
    """))
    (pkg / "route_registry.py").write_text(textwrap.dedent("""
        class RouteRegistryError(Exception):
            pass
        def resolve(surface, channel):
            raise RouteRegistryError("no owner in the fixture")
    """))
    return pkg


@pytest.fixture
def lane_root(tmp_path, monkeypatch):
    """A temp instance root the gate treats as its own, with `pipeline` evicted
    from sys.modules so each test imports the package it built."""
    import sys
    for name in list(sys.modules):
        if name == "pipeline" or name.startswith("pipeline."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(vsg, "INSTANCE_ROOT", tmp_path)
    return tmp_path


def test_no_lane_means_no_enforcement(lane_root):
    """The 24-instance case: nothing under q-consult/pipeline, nothing to verify,
    and no exception either (an uncaught ImportError in a Stop hook fails OPEN)."""
    assert vsg._route_context() is None
    assert vsg.enforce_route_receipt("write me a linkedin post", "a draft") is None


def test_a_lane_that_does_not_import_holds_the_turn(lane_root):
    """Present-but-broken is a broken verifier, not an absent one."""
    _fake_lane(lane_root, broken=True)
    with pytest.raises(vsg.RouteBoundaryError, match="did not import"):
        vsg.enforce_route_receipt("write me a linkedin post", "a draft")


def test_a_not_routed_request_passes_a_present_lane(lane_root):
    _fake_lane(lane_root, status="NOT_ROUTED")
    assert vsg.enforce_route_receipt("explain simply", "a reply") is None


def test_a_routed_request_with_no_owner_is_refused(lane_root):
    """Same words as the live gate: the route family is verbatim from the
    instance, so its refusals read the same on every instance that grows a lane."""
    _fake_lane(lane_root, status="ROUTE")
    with pytest.raises(vsg.RouteBoundaryError, match="no single registered active owner"):
        vsg.enforce_route_receipt("write me a linkedin post", "a draft")


def test_a_receipt_block_must_be_json():
    with pytest.raises(vsg.RouteBoundaryError, match="not valid JSON"):
        vsg._receipt_block("=== ROUTE RECEIPT ===\nnot json")
    assert vsg._receipt_block("no marker here") is None
    assert vsg._receipt_block('=== ROUTE RECEIPT ===\n{"surface": "x"}') == {"surface": "x"}
