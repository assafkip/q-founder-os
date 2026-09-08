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

    def test_a_gmail_row_says_what_to_do(self, tmp_path):
        assert self._mail(tmp_path, "mail:1a06eb5b0b03759f")["next"] == (
            "Open the thread and reply.")


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
