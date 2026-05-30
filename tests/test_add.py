from datetime import date, timedelta

import pytest

from minutes.add import parse_line, _parse_due
from minutes.models import EntryStatus, EntryType


class TestParseDue:
    def test_integer_days(self):
        today = date.today()
        assert _parse_due("7") == (today + timedelta(days=7)).isoformat()
        assert _parse_due("0") == today.isoformat()

    def test_weekday_is_future(self):
        result = _parse_due("fri")
        d = date.fromisoformat(result)
        assert d.weekday() == 4  # Friday
        assert d >= date.today()

    def test_all_weekday_abbreviations(self):
        for abbr, wd in [("mon", 0), ("tue", 1), ("wed", 2), ("thu", 3),
                          ("fri", 4), ("sat", 5), ("sun", 6)]:
            result = _parse_due(abbr)
            assert date.fromisoformat(result).weekday() == wd

    def test_iso_date(self):
        assert _parse_due("2026-12-31") == "2026-12-31"

    def test_invalid_returns_none(self):
        assert _parse_due("notadate") is None


class TestParseLine:
    def test_note_no_prefix(self):
        e = parse_line("just a note")
        assert e is not None
        assert e.type == EntryType.NOTE
        assert e.text == "just a note"

    def test_decision_prefix(self):
        e = parse_line("* Drop v1 endpoints")
        assert e is not None
        assert e.type == EntryType.DECISION
        assert e.text == "Drop v1 endpoints"

    def test_action_prefix(self):
        e = parse_line("! Write migration guide")
        assert e is not None
        assert e.type == EntryType.ACTION
        assert e.text == "Write migration guide"
        assert e.status == EntryStatus.OPEN

    def test_action_with_date(self):
        e = parse_line("! Write migration guide @7")
        assert e is not None
        assert e.type == EntryType.ACTION
        assert e.due == (date.today() + timedelta(days=7)).isoformat()
        assert "@" not in e.text

    def test_action_with_iso_date(self):
        e = parse_line("! Write migration guide @2026-06-01")
        assert e is not None
        assert e.due == "2026-06-01"

    def test_waiting_prefix(self):
        e = parse_line("> v2 spec approval")
        assert e is not None
        assert e.type == EntryType.WAITING
        assert e.text == "v2 spec approval"

    def test_waiting_with_person(self):
        e = parse_line("> v2 spec @Marco")
        assert e is not None
        assert e.person == "Marco"
        assert "@Marco" not in e.text

    def test_waiting_person_stripped_from_text(self):
        e = parse_line("> get approval @Anna")
        assert e is not None
        assert e.person == "Anna"
        assert e.text == "get approval"

    def test_empty_line_returns_none(self):
        assert parse_line("") is None
        assert parse_line("   ") is None

    def test_meeting_is_attached(self):
        e = parse_line("* A decision", meeting="team sync")
        assert e is not None
        assert e.meeting == "team sync"

    def test_project_is_empty_placeholder(self):
        e = parse_line("some note")
        assert e is not None
        assert e.project == ""

    def test_id_is_four_chars(self):
        e = parse_line("a note")
        assert e is not None
        assert len(e.id) == 7
