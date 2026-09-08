"""The board carries only what he can act on, and every row he can act on can be started.

Founder-directed 2026-09-07, after a row-by-row walk of the live board: *"remove sana
stuff from the board"* and *"I want you to revamp the crm so it fits what I asked. Dont
punt anything to me. Fix it. right now its not useful."* DEC-34 in the consulting
instance's crm-working.md is the record.

Every case here was RED against the file as it stood that evening; the red run is in
the PR body. The property-name expectations are written out BY HAND rather than
derived from the module's own tables: a test that iterates the thing it is testing
cannot see that thing shrink, so a property silently dropped from the writer would
take its own test with it.
"""
import datetime as dt
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import board_rows as br  # noqa: E402
import consulting_board as cb  # noqa: E402

NOW = dt.datetime(2026, 9, 7, 8, 0, tzinfo=dt.timezone.utc)

#: GENERIC CLIENT LABELS ON PURPOSE. This repo is public and the client-name guard
#: blocks real ones in staged content; the shapes under test are the health dots and
#: the line grammar, and neither needs a real engagement's name.
CARD = """*Your book today* - 4 active - 2026-09-07
*THE MOVE* 🟡 *Yellow Engagement, LLC* · touch due 13 days ago
⚪ *White Engagement One* · an agent owes 6: run the long-running search
⚪ *White Engagement Two* · an agent owes 7: point at the key files
🟢 *Green Engagement* · nothing to do
🔴 *Red Engagement* · you said "the intake form" - not sent
"""


def _paths(tmp_path):
    """The module's OWN path map, rooted at a tmp dir. Restating the file names here
    would make this a second source of truth for them, and a rename would leave the
    test green against paths nothing uses."""
    paths = cb._paths(tmp_path)
    for f in paths.values():
        f.parent.mkdir(parents=True, exist_ok=True)
    paths["card"].write_text(CARD, encoding="utf-8")
    # The card is withheld unless its heartbeat is stamped TODAY in PT, which is the
    # freshness rule read_heartbeat enforces. The stamp is derived from the module's
    # own clock rather than hardcoded, because a hardcoded date is a time bomb.
    paths["heartbeat"].write_text(json.dumps(
        {"at": "x", "card": {"date": NOW.astimezone(cb.PT).date().isoformat(),
                             "counts": {"red": 1, "reach": 0}}}), encoding="utf-8")
    paths["gtm"].write_text(json.dumps({"rows": {}}), encoding="utf-8")
    return paths


def _card_items(tmp_path):
    rows, err = cb.read_card(_paths(tmp_path))
    assert err is None, err
    return rows


class TestSanaNeverReachesHisBoard:
    """⚪ is 'their move' or 'Sana owes n'. It is reported on the Slack card and is
    never a row on his board, because it is not an act he can perform (DEC-30/DEC-34)."""

    def test_the_card_still_carries_the_white_lines(self, tmp_path):
        # The reader is unchanged on purpose: the Slack card keeps its Sana line.
        healths = [r["health"] for r in _card_items(tmp_path)]
        assert healths.count("⚪") == 2, healths

    def test_no_white_or_green_line_becomes_a_board_row(self, tmp_path):
        out = cb.buckets(NOW, {}, _paths(tmp_path))
        titles = [i["title"] for i in out["top_of_mind"] + out["this_week"] + out["inbox"]]
        assert not [t for t in titles if t.startswith(("⚪", "🟢"))], titles

    def test_the_rows_he_can_act_on_are_still_there(self, tmp_path):
        out = cb.buckets(NOW, {}, _paths(tmp_path))
        titles = [i["title"] for i in out["top_of_mind"]]
        assert any(t.startswith("🔴") for t in titles), titles
        assert any(t.startswith("🟡") for t in titles), titles


class TestThisWeekIsNotMachineFilledFromTheCard:
    """The section's own text says it is his and that nothing fills it automatically."""

    def test_the_card_writes_nothing_into_this_week(self, tmp_path):
        out = cb.buckets(NOW, {}, _paths(tmp_path))
        from_card = [i for i in out["this_week"] if i.get("scope") == "card"]
        assert from_card == [], from_card

    def test_a_yellow_row_is_top_of_mind_not_this_week(self, tmp_path):
        out = cb.buckets(NOW, {}, _paths(tmp_path))
        assert any(i["title"].startswith("🟡") for i in out["top_of_mind"])
        assert not any(i["title"].startswith("🟡") for i in out["this_week"])


class TestEveryMailRowCanBeStartedFromTheRow:
    """His standing rule: if he cannot click it, it does not belong."""

    def _mail(self, tmp_path, key):
        class Row(str):
            pass
        r = Row("someone@example.test  Intro: two people")
        r.key = key
        out = cb.buckets(NOW, {"mail": ([r], None)}, _paths(tmp_path))
        return out["inbox"][0]

    def test_a_gmail_row_carries_its_thread_link(self, tmp_path):
        item = self._mail(tmp_path, "mail:1a06eb5b0b03759f")
        assert item["link"] == (
            "https://mail.google.com/mail/u/0/#all/1a06eb5b0b03759f"), item

    def test_the_link_is_derived_from_the_id_not_the_text(self, tmp_path):
        # Same rendered line, different thread: different link. The PR #296 rounds 1-4
        # defect was an identity derived from presentation; this must not repeat it.
        a = self._mail(tmp_path, "mail:aaaaaaaaaaaaaaaa")["link"]
        b = self._mail(tmp_path, "mail:bbbbbbbbbbbbbbbb")["link"]
        assert a != b and a.endswith("aaaaaaaaaaaaaaaa"), (a, b)

    def test_the_producer_supplies_no_next_for_an_inbox_row(self, tmp_path):
        """A constant per source restates DONE_BY_SOURCE in the imperative, which is
        the duplication this change removes from Notes (PR reviewer, nit). The link
        and the subject are what make the row startable. Because the writer never
        blanks a property it was not given, a Next a human wrote there survives."""
        assert self._mail(tmp_path, "mail:1a06eb5b0b03759f").get("next") is None


class TestTheWriterCarriesLinkAndNext:
    """Written when the producer supplies them, never blanked when it does not."""

    #: BY HAND, not derived from the writer's own map. A property dropped from that map
    #: would otherwise take its test with it and the suite would still be green.
    EXPECTED = {"Task", "Item id", "Notes", "Domain", "Priority", "Source",
                "Link", "Next"}

    def test_link_and_next_are_written(self):
        props = br._properties({"title": "t", "key": "k", "done": "d",
                                "link": "https://example.test/x",
                                "next": "Open the thread and reply.",
                                "priority": "P1", "source": "Gmail"},
                               "Inbox", "cb:x", False)
        assert props["Link"] == {"url": "https://example.test/x"}
        assert props["Next"]["rich_text"][0]["text"]["content"] == (
            "Open the thread and reply.")

    def test_the_written_property_set_is_exactly_what_is_expected(self):
        props = br._properties({"title": "t", "key": "k", "done": "d",
                                "link": "https://example.test/x", "next": "go",
                                "priority": "P1", "source": "Gmail"},
                               "Inbox", "cb:x", False)
        assert set(props) == self.EXPECTED, set(props) ^ self.EXPECTED

    def test_a_producer_that_knows_neither_clears_neither(self):
        props = br._properties({"title": "t", "key": "k", "done": "d"},
                               "Inbox", "cb:x", False)
        assert "Link" not in props and "Next" not in props, sorted(props)


class TestTheNoteDoesNotRepeatItself:
    """6 of 12 live rows on 2026-09-07 printed one sentence twice."""

    def test_a_detail_equal_to_the_done_signal_is_written_once(self):
        signal = "the old token is dead and the new one is not in a tracked file."
        props = br._properties({"title": "t", "key": "k", "done": signal,
                                "detail": signal}, "This Week", "cb:x", False)
        note = props["Notes"]["rich_text"][0]["text"]["content"]
        assert note.count(signal) == 1, note

    def test_a_detail_that_adds_something_is_kept(self):
        props = br._properties({"title": "t", "key": "k", "done": "signal",
                                "detail": "a real extra fact"}, "This Week",
                               "cb:x", False)
        note = props["Notes"]["rich_text"][0]["text"]["content"]
        assert "a real extra fact" in note and "signal" in note, note


class TestHisPlacementSurvivesTheProducerDroppingTheRow:
    """The module's contract is that a row a human moved is never moved by the machine.
    The archive loop was the hole in it: a pinned row was archived the moment its
    producer stopped emitting it, taking his placement and his Status with it. Filtering
    white client lines off the board makes that flip ordinary rather than rare."""

    def _page(self, iid, note):
        return {"id": f"page-{iid}",
                "properties": {"Item id": {"rich_text": [{"plain_text": iid}]},
                               "Notes": {"rich_text": [{"plain_text": note}]}}}

    def test_a_pinned_row_is_kept_when_its_producer_stops_emitting_it(self, monkeypatch):
        page = self._page("cb:gone", "Done signal: x\nscope=card\nbucket=This Week\npinned=1")
        sent = []
        monkeypatch.setattr(br, "existing_rows", lambda *a, **k: {"cb:gone": page})
        monkeypatch.setattr(br, "_request",
                            lambda tok, m, path, body, op=None, bud=None: sent.append((m, path, body)))
        counts = br.paint({"top_of_mind": [], "this_week": [], "inbox": [],
                           "healthy_scopes": {"card"}}, "tok", "db")
        assert counts["archived"] == 0, sent
        # `held`, not `kept`: a quiet source and a row he pinned whose source is
        # healthy are different facts and the morning line reports both.
        assert counts["held"] == 1 and counts["kept"] == 0, counts
        assert not [s for s in sent if s[2].get("archived")], sent

    def test_a_held_row_is_a_term_of_the_read_back_sum(self, monkeypatch):
        """A held row IS on the board. Leaving it out of the sum made the proof report
        a mismatch every run once any pinned row's producer went quiet, which is the
        false-alarm shape that trains him to ignore the word (PR reviewer round 4)."""
        page = self._page("cb:gone", "Done signal: x\nscope=card\nbucket=This Week\npinned=1")
        monkeypatch.setattr(br, "existing_rows", lambda *a, **k: {"cb:gone": page})
        monkeypatch.setattr(br, "_request", lambda *a, **k: None)
        counts = br.paint({"top_of_mind": [], "this_week": [], "inbox": [],
                           "healthy_scopes": {"card"}}, "tok", "db")
        expected = (counts["wanted"] + counts["kept"] + counts["held"]
                    - counts["deferred_new"])
        assert expected == 1, counts
        assert counts["held"] == 1 and counts["kept"] == 0, counts

    def test_nothing_is_written_to_a_held_row(self, monkeypatch):
        """The first answer to 'a pinned row has no exit' wrote a stamp into its Notes,
        and truncating the note to fit deleted `pinned=1` itself. Nothing is written
        now; his exit is his own archive."""
        page = self._page("cb:gone", "Done signal: x\nscope=card\nbucket=This Week\npinned=1")
        sent = []
        monkeypatch.setattr(br, "existing_rows", lambda *a, **k: {"cb:gone": page})
        monkeypatch.setattr(br, "_request",
                            lambda tok, m, path, body, op=None, bud=None: sent.append((m, path, body)))
        br.paint({"top_of_mind": [], "this_week": [], "inbox": [],
                  "healthy_scopes": {"card"}}, "tok", "db")
        assert sent == [], sent

    def test_an_unpinned_row_the_producer_dropped_is_still_archived(self, monkeypatch):
        page = self._page("cb:gone", "Done signal: x\nscope=card\nbucket=This Week")
        sent = []
        monkeypatch.setattr(br, "existing_rows", lambda *a, **k: {"cb:gone": page})
        monkeypatch.setattr(br, "_request",
                            lambda tok, m, path, body, op=None, bud=None: sent.append((m, path, body)))
        counts = br.paint({"top_of_mind": [], "this_week": [], "inbox": [],
                           "healthy_scopes": {"card"}}, "tok", "db")
        assert counts["archived"] == 1, (counts, sent)


class TestALinkIsComparable:
    """Without url in `_prop_value` every row carrying a Link read as unreadable, so
    `_already_holds` was always False and the painter rewrote every Gmail row every
    run (PR reviewer, major)."""

    def test_a_url_property_reads_back_as_its_value(self):
        assert br._prop_value({"url": "https://example.test/x"}) == "https://example.test/x"

    def test_an_unchanged_link_is_not_rewritten(self):
        props = br._properties({"title": "t", "key": "k", "done": "d",
                                "link": "https://example.test/x"},
                               "Inbox", "cb:x", False)
        page = {"properties": {k: v for k, v in props.items()}}
        assert br._already_holds(page, props), "a row that already holds its Link was rewritten"

    def test_a_changed_link_is_rewritten(self):
        props = br._properties({"title": "t", "key": "k", "done": "d",
                                "link": "https://example.test/new"},
                               "Inbox", "cb:x", False)
        page = {"properties": dict(props, Link={"url": "https://example.test/old"})}
        assert not br._already_holds(page, props)


class TestAColumnThisBoardLacksIsNotAWholeLostMorning:
    """`Link` and `Next` are new. Notion answers an unknown property with a 400 that
    aborts the paint mid-write, so a board that predates them would lose every row of
    that morning to a column nobody noticed was missing (PR reviewer round 5, major)."""

    ITEM = {"title": "t", "key": "k", "done": "d", "priority": "P1",
            "source": "Gmail", "link": "https://example.test/x", "next": "go"}

    def test_a_board_without_the_new_columns_is_written_without_them(self):
        props = br._properties(self.ITEM, "Inbox", "cb:x", False)
        assert {"Link", "Next"} <= set(props), sorted(props)
        old_board = {"Task", "Item id", "Notes", "Domain", "Priority", "Source"}
        assert set(br._only_known(props, old_board)) == old_board, sorted(props)

    def test_the_create_path_is_filtered_too(self, monkeypatch):
        """The first fix filtered the PATCH and not the POST, so a board lacking the
        column still took a 400 on its first NEW row and abandoned the whole paint.
        The patch printed "write sites filtered: 1" and nobody asked whether there were
        two (PR reviewer round 6, major)."""
        sent = []
        monkeypatch.setattr(br, "existing_rows", lambda *a, **k: {})
        monkeypatch.setattr(br, "_request",
                            lambda tok, m, path, body, op=None, bud=None: sent.append((m, path, body)))
        old_board = {"Task", "Item id", "Notes", "Domain", "Priority", "Source",
                     "Bucket", "Status"}
        br.paint({"top_of_mind": [dict(self.ITEM, scope="card")], "this_week": [],
                  "inbox": [], "healthy_scopes": {"card"}},
                 "tok", "db", known=old_board)
        posts = [s for s in sent if s[0] == "POST"]
        assert posts, sent
        written = set(posts[0][2]["properties"])
        assert "Link" not in written and "Next" not in written, sorted(written)

    def test_a_board_with_them_keeps_them(self):
        props = br._properties(self.ITEM, "Inbox", "cb:x", False)
        assert br._only_known(props, set(props)) == props

    def test_an_unreadable_schema_writes_everything_exactly_as_before(self):
        """The read failing is not the columns being gone. Refusing to write on a bad
        response would turn one bad answer into a blank morning."""
        props = br._properties(self.ITEM, "Inbox", "cb:x", False)
        assert br._only_known(props, None) == props

    def test_a_failed_schema_request_is_None_not_an_exception(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("notion said no")
        monkeypatch.setattr(br, "_request", boom)
        assert br._schema_properties("tok", "db") is None

    def test_an_empty_schema_answer_is_None_not_an_empty_set(self, monkeypatch):
        """An empty set would filter EVERY property out and write nothing at all,
        which is the same lost morning by a different route."""
        monkeypatch.setattr(br, "_request", lambda *a, **k: {"properties": {}})
        assert br._schema_properties("tok", "db") is None
