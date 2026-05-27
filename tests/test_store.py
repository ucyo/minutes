import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from tgsa.models import Entry, EntryStatus, EntryType
from tgsa.store import (
    append_entry,
    filter_entries,
    load_entries,
    mark_done,
    parse_since,
)


@pytest.fixture
def store(tmp_path):
    return tmp_path / "entries.jsonl"


def _entry(project="proj", etype=EntryType.NOTE, text="hello", **kwargs) -> Entry:
    return Entry(
        id=Entry.make_id(),
        ts=kwargs.pop("ts", "2026-05-27T10:00"),
        project=project,
        type=etype,
        text=text,
        **kwargs,
    )


class TestAppendAndLoad:
    def test_append_creates_file(self, store):
        e = _entry()
        append_entry(e, store)
        assert store.exists()

    def test_load_roundtrip(self, store):
        e = _entry(text="test note")
        append_entry(e, store)
        loaded = load_entries(store)
        assert len(loaded) == 1
        assert loaded[0].text == "test note"

    def test_load_last_write_wins(self, store):
        e = _entry(etype=EntryType.ACTION, status=EntryStatus.OPEN)
        append_entry(e, store)
        e.status = EntryStatus.DONE
        e.updated_ts = "2026-05-27T15:00"
        append_entry(e, store)
        loaded = load_entries(store)
        assert len(loaded) == 1
        assert loaded[0].status == EntryStatus.DONE

    def test_load_empty_store(self, store):
        assert load_entries(store) == []

    def test_load_skips_malformed_lines(self, store):
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text('not json\n{"id":"x","ts":"2026-05-27T10:00","project":"p","type":"note","text":"ok"}\n')
        loaded = load_entries(store)
        assert len(loaded) == 1
        assert loaded[0].text == "ok"


class TestParseSince:
    def test_mon_returns_monday(self):
        d = parse_since("mon")
        assert d.weekday() == 0

    def test_integer_days_back(self):
        today = date.today()
        assert parse_since("7") == today - timedelta(days=7)
        assert parse_since("0") == today

    def test_iso_date(self):
        assert parse_since("2026-01-15") == date(2026, 1, 15)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_since("notadate")


class TestFilterEntries:
    def _entries(self):
        return [
            _entry(project="alpha", etype=EntryType.NOTE, ts="2026-05-26T09:00"),
            _entry(project="beta", etype=EntryType.ACTION, ts="2026-05-27T10:00",
                   status=EntryStatus.OPEN),
            _entry(project="alpha", etype=EntryType.DECISION, ts="2026-05-27T11:00"),
            _entry(project="beta", etype=EntryType.ACTION, ts="2026-05-27T12:00",
                   status=EntryStatus.DONE),
        ]

    def test_filter_by_project(self):
        result = filter_entries(self._entries(), project="alpha")
        assert all(e.project == "alpha" for e in result)
        assert len(result) == 2

    def test_filter_by_since(self):
        result = filter_entries(self._entries(), since=date(2026, 5, 27))
        assert all(e.ts >= "2026-05-27" for e in result)
        assert len(result) == 3

    def test_filter_by_type(self):
        result = filter_entries(self._entries(), entry_type=EntryType.ACTION)
        assert all(e.type == EntryType.ACTION for e in result)
        assert len(result) == 2

    def test_open_only_excludes_done_actions(self):
        result = filter_entries(self._entries(), open_only=True)
        assert all(e.status != EntryStatus.DONE for e in result if e.type == EntryType.ACTION)

    def test_open_only_excludes_notes_and_decisions(self):
        result = filter_entries(self._entries(), open_only=True)
        assert all(e.type in (EntryType.ACTION, EntryType.WAITING) for e in result)

    def test_no_filters_returns_all(self):
        entries = self._entries()
        assert filter_entries(entries) == entries


class TestMarkDone:
    def test_marks_existing_action_done(self, store):
        e = _entry(etype=EntryType.ACTION, status=EntryStatus.OPEN)
        append_entry(e, store)
        result = mark_done(e.id, store=store)
        assert result is not None
        assert result.status == EntryStatus.DONE
        loaded = load_entries(store)
        assert loaded[0].status == EntryStatus.DONE

    def test_returns_none_for_unknown_id(self, store):
        assert mark_done("zzzz", store=store) is None

    def test_sets_updated_ts(self, store):
        e = _entry(etype=EntryType.ACTION, status=EntryStatus.OPEN)
        append_entry(e, store)
        result = mark_done(e.id, store=store)
        assert result.updated_ts is not None
