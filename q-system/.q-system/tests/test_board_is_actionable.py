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

import pytest
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

    def test_a_held_row_is_reported_as_held_and_as_nothing_else(self, monkeypatch):
        """A held row IS on the board, so it has to be a term of `collect`'s read-back
        sum or the proof reports a mismatch every run once any pinned row's producer
        goes quiet (PR reviewer round 4, major).

        THIS TEST DOES NOT RECOMPUTE THAT SUM. The first version did, and a test that
        recomputes the formula it guards stays green when the real one drops a term
        (round 7, minor). The sum itself is held by
        test_every_row_on_the_board_is_a_term_of_the_read_back_sum in
        test_consulting_board.py, which reads the expression `collect` actually uses.
        What belongs here is the count that expression consumes."""
        page = self._page("cb:gone", "Done signal: x\nscope=card\nbucket=This Week\npinned=1")
        monkeypatch.setattr(br, "existing_rows", lambda *a, **k: {"cb:gone": page})
        monkeypatch.setattr(br, "_request", lambda *a, **k: None)
        counts = br.paint({"top_of_mind": [], "this_week": [], "inbox": [],
                           "healthy_scopes": {"card"}}, "tok", "db")
        assert counts["held"] == 1, counts
        assert counts["kept"] == 0 and counts["archived"] == 0, counts
        assert counts["wanted"] == 0 and counts["deferred_new"] == 0, counts

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
    that morning to a column nobody noticed was missing (PR reviewer round 5, major).

    `known` maps a column name to its TYPE. Name alone was not enough: a board carrying
    `Link` as rich_text rather than url takes the same 400 the guard exists to prevent,
    and the guard would have called the column fine (round 7, minor)."""

    ITEM = {"title": "t", "key": "k", "done": "d", "priority": "P1",
            "source": "Gmail", "link": "https://example.test/x", "next": "go"}
    #: BY HAND, never derived from WRITES_TYPE: a column dropped from that map would
    #: otherwise take its own test with it and the suite would stay green.
    OLD_BOARD = {"Task": "title", "Item id": "rich_text", "Notes": "rich_text",
                 "Domain": "multi_select", "Priority": "select", "Source": "select",
                 "Bucket": "select", "Status": "select"}

    def _props(self):
        return br._properties(self.ITEM, "Inbox", "cb:x", False)

    def test_a_board_without_the_new_columns_is_written_without_them(self):
        keep, dropped = br._only_known(self._props(), self.OLD_BOARD)
        assert "Link" not in keep and "Next" not in keep, sorted(keep)
        assert dropped == ("Link", "Next"), dropped

    def test_a_board_that_has_them_as_the_WRONG_TYPE_drops_them_too(self):
        board = dict(self.OLD_BOARD, Link="rich_text", Next="rich_text")
        keep, dropped = br._only_known(self._props(), board)
        assert dropped == ("Link",), dropped
        assert "Next" in keep, sorted(keep)

    def test_a_board_with_them_keeps_them(self):
        board = dict(self.OLD_BOARD, Link="url", Next="rich_text")
        keep, dropped = br._only_known(self._props(), board)
        assert keep == self._props() and dropped == (), dropped

    def test_an_unreadable_schema_writes_everything_exactly_as_before(self):
        """The read failing is not the columns being gone. Refusing to write on a bad
        response would turn one bad answer into a blank morning."""
        keep, dropped = br._only_known(self._props(), None)
        assert keep == self._props() and dropped == ()

    def test_a_failed_schema_request_is_None_not_an_exception(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("notion said no")
        monkeypatch.setattr(br, "_request", boom)
        assert br._schema_properties("tok", "db") is None

    def test_an_empty_schema_answer_is_None_not_an_empty_map(self, monkeypatch):
        """An empty map would drop EVERY property and write nothing at all, which is
        the same lost morning by a different route."""
        monkeypatch.setattr(br, "_request", lambda *a, **k: {"properties": {}})
        assert br._schema_properties("tok", "db") is None

    def test_the_schema_read_keeps_the_type(self, monkeypatch):
        monkeypatch.setattr(br, "_request", lambda *a, **k: {
            "properties": {"Task": {"type": "title"}, "Link": {"type": "url"}}})
        assert br._schema_properties("tok", "db") == {"Task": "title", "Link": "url"}

    def _paint_against(self, monkeypatch, board):
        sent = []
        monkeypatch.setattr(br, "existing_rows", lambda *a, **k: {})
        monkeypatch.setattr(br, "_request",
                            lambda tok, m, path, body, op=None, bud=None: sent.append((m, path, body)))
        counts = br.paint({"top_of_mind": [dict(self.ITEM, scope="card")],
                           "this_week": [], "inbox": [], "healthy_scopes": {"card"}},
                          "tok", "db", known=board)
        return counts, sent

    def test_the_create_path_is_filtered_too(self, monkeypatch):
        """The first fix filtered the PATCH and not the POST, so a board lacking the
        column still took a 400 on its first NEW row and abandoned the whole paint. The
        patch printed "write sites filtered: 1" and nobody asked whether there were two
        (round 6, major)."""
        counts, sent = self._paint_against(monkeypatch, self.OLD_BOARD)
        posts = [s for s in sent if s[0] == "POST"]
        assert posts, sent
        written = set(posts[0][2]["properties"])
        assert "Link" not in written and "Next" not in written, sorted(written)

    def test_what_could_not_be_written_is_reported_never_silent(self, monkeypatch):
        """A board without `Link` wrote every row with no link and still said
        "read-back ok". A silent half-write is worse than the crash it replaced,
        because the crash gets looked at (round 7, major)."""
        counts, _ = self._paint_against(monkeypatch, self.OLD_BOARD)
        assert counts["dropped_columns"] == ("Link", "Next"), counts["dropped_columns"]

    def test_a_complete_board_reports_nothing_dropped(self, monkeypatch):
        board = dict(self.OLD_BOARD, Link="url", Next="rich_text")
        counts, _ = self._paint_against(monkeypatch, board)
        assert counts["dropped_columns"] == (), counts["dropped_columns"]


class TestTheIdentityColumnIsNeverDropped:
    """`Item id` is how every lookup, refresh and archive decision finds a row, and
    `existing_rows` queries the board by its prefix. Dropping it does not degrade a
    row: it creates a page this module can never find again, one more per wanted row
    per run, with no error anywhere (PR reviewer round 8, major)."""

    ITEM = {"title": "t", "key": "k", "done": "d", "priority": "P1", "source": "Gmail"}

    def _props(self):
        return br._properties(self.ITEM, "Inbox", "cb:x", False)

    def test_a_board_that_cannot_take_the_id_stops_the_paint(self):
        board = {"Task": "title", "Notes": "rich_text", "Domain": "multi_select",
                 "Priority": "select", "Source": "select"}
        with pytest.raises(br.MissingIdentityColumn) as e:
            br._only_known(self._props(), board)
        assert "Item id" in str(e.value)

    def test_the_id_under_the_wrong_type_stops_it_too(self):
        board = {"Task": "title", "Item id": "select", "Notes": "rich_text",
                 "Domain": "multi_select", "Priority": "select", "Source": "select"}
        with pytest.raises(br.MissingIdentityColumn):
            br._only_known(self._props(), board)

    def test_a_missing_title_stops_it(self):
        board = {"Item id": "rich_text", "Notes": "rich_text",
                 "Domain": "multi_select", "Priority": "select", "Source": "select"}
        with pytest.raises(br.MissingIdentityColumn) as e:
            br._only_known(self._props(), board)
        assert "Task" in str(e.value)

    def test_an_optional_column_still_only_drops(self):
        """The refusal is for identity, not for everything. A board missing `Link`
        still paints, minus the link, and says so."""
        board = {"Task": "title", "Item id": "rich_text", "Notes": "rich_text",
                 "Domain": "multi_select", "Priority": "select", "Source": "select"}
        keep, dropped = br._only_known(
            br._properties(dict(self.ITEM, link="https://example.test/x"),
                           "Inbox", "cb:x", False), board)
        assert dropped == ("Link",) and "Item id" in keep


class TestTheSchemaGuardIsActuallyWiredIntoTheRun:
    """A guard the production path never passes is a guard that does not exist, and the
    suite would stay green either way (PR reviewer round 8, nit)."""

    def test_the_runner_hands_paint_the_schema_it_read(self, monkeypatch, tmp_path):
        seen = {}
        monkeypatch.setattr(br, "_schema_properties",
                            lambda *a, **k: {"Task": "title", "Item id": "rich_text"})

        def spy_paint(buckets, token, db, opener=None, budget=None, known=None):
            seen["known"] = known
            return {"created": 0, "updated": 0, "archived": 0, "kept": 0, "held": 0,
                    "wanted": 0, "moved": 0, "pinned": 0, "over_cap": 0,
                    "unchanged": 0, "deferred": 0, "deferred_new": 0,
                    "dropped_columns": ()}

        monkeypatch.setattr(br, "paint", spy_paint)
        monkeypatch.setattr(br, "existing_rows", lambda *a, **k: {})
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("KIPI_BRIEF_DRY_RUN", raising=False)
        tf = tmp_path / "notion-token"; tf.write_text("t", encoding="utf-8")
        dbf = tmp_path / "notion-board-db"; dbf.write_text("d", encoding="utf-8")
        br.collect(NOW, {}, token_file=str(tf), db_file=str(dbf))
        assert seen.get("known") == {"Task": "title", "Item id": "rich_text"}, seen
