from __future__ import annotations

from datetime import date, timedelta

import pytest
from rich.console import Console as RichConsole

import minutes.display as display_mod
from minutes.display import _build_meta, _build_parts, _date_bucket, _due_style
from minutes.models import Entry, EntryStatus, EntryType


def _entry(**kwargs) -> Entry:
    defaults = dict(
        id="abc1234",
        ts="2026-05-30T10:00",
        project="proj",
        type=EntryType.NOTE,
        text="hello",
    )
    defaults.update(kwargs)
    return Entry(**defaults)


@pytest.fixture
def capturing_console(monkeypatch):
    con = RichConsole(record=True, width=200, highlight=False)
    monkeypatch.setattr(display_mod, "console", con)
    return con


class TestDateBucket:
    # 2026-05-30 is a Saturday in ISO week 22
    TODAY = date(2026, 5, 30)

    def test_today(self):
        assert _date_bucket(self.TODAY, self.TODAY) == "Today"

    def test_yesterday(self):
        assert _date_bucket(date(2026, 5, 29), self.TODAY) == "Yesterday"

    def test_this_week(self):
        # 2026-05-26 (Tue) is in ISO week 22, same as today but not today/yesterday
        assert _date_bucket(date(2026, 5, 26), self.TODAY) == "This week"

    def test_this_month(self):
        # 2026-05-10 is in May but a different ISO week
        assert _date_bucket(date(2026, 5, 10), self.TODAY) == "This month"

    def test_this_year(self):
        assert _date_bucket(date(2026, 2, 15), self.TODAY) == "This year"

    def test_older(self):
        assert _date_bucket(date(2025, 12, 31), self.TODAY) == "Older"


class TestDueStyle:
    def test_none_returns_empty(self):
        assert _due_style(None) == ""

    def test_overdue_returns_red(self):
        past = (date.today() - timedelta(days=1)).isoformat()
        assert _due_style(past) == "bold red"

    def test_due_today_returns_yellow(self):
        assert _due_style(date.today().isoformat()) == "yellow"

    def test_due_tomorrow_returns_yellow(self):
        assert _due_style((date.today() + timedelta(days=1)).isoformat()) == "yellow"

    def test_due_in_two_days_returns_yellow(self):
        assert _due_style((date.today() + timedelta(days=2)).isoformat()) == "yellow"

    def test_due_in_future_returns_empty(self):
        assert _due_style((date.today() + timedelta(days=30)).isoformat()) == ""


class TestBuildParts:
    def test_note(self):
        label, content = _build_parts(_entry(type=EntryType.NOTE, text="a note"))
        assert label.plain == "note"
        assert content.plain == "a note"

    def test_decision(self):
        label, content = _build_parts(_entry(type=EntryType.DECISION, text="drop v1"))
        assert label.plain == "decision"
        assert content.plain == "drop v1"

    def test_action_open_has_checkbox(self):
        e = _entry(type=EntryType.ACTION, text="do it", status=EntryStatus.OPEN)
        label, content = _build_parts(e)
        assert label.plain == "action"
        assert "[ ]" in content.plain

    def test_action_done_has_checkbox_and_strikethrough(self):
        e = _entry(type=EntryType.ACTION, text="done it", status=EntryStatus.DONE)
        _, content = _build_parts(e)
        assert "[x]" in content.plain
        assert "strike" in str(content._spans[0].style)

    def test_action_cancelled_has_checkbox(self):
        e = _entry(type=EntryType.ACTION, text="forget it", status=EntryStatus.CANCELLED)
        _, content = _build_parts(e)
        assert "[-]" in content.plain

    def test_action_open_with_due_shows_date(self):
        due = (date.today() + timedelta(days=30)).isoformat()
        e = _entry(type=EntryType.ACTION, text="plan", status=EntryStatus.OPEN, due=due)
        _, content = _build_parts(e)
        assert f"due {due}" in content.plain

    def test_action_done_hides_due(self):
        due = (date.today() + timedelta(days=30)).isoformat()
        e = _entry(type=EntryType.ACTION, text="done", status=EntryStatus.DONE, due=due)
        _, content = _build_parts(e)
        assert "due" not in content.plain

    def test_waiting_without_person(self):
        e = _entry(type=EntryType.WAITING, text="spec approval")
        label, content = _build_parts(e)
        assert label.plain == "waiting"
        assert content.plain == "spec approval"

    def test_waiting_person_appended(self):
        e = _entry(type=EntryType.WAITING, text="spec approval", person="Marco")
        _, content = _build_parts(e)
        assert "spec approval" in content.plain
        assert "Marco" in content.plain


class TestBuildMeta:
    def test_meeting_populated(self):
        meeting, _, _ = _build_meta(_entry(meeting="team sync"))
        assert meeting.plain == "team sync"

    def test_meeting_empty_when_absent(self):
        meeting, _, _ = _build_meta(_entry())
        assert meeting.plain == ""

    def test_tags_formatted(self):
        _, tags, _ = _build_meta(_entry(tags=["urgent", "infra"]))
        assert tags.plain == "#urgent  #infra"

    def test_tags_empty_when_absent(self):
        _, tags, _ = _build_meta(_entry())
        assert tags.plain == ""

    def test_updated_ts_shown_for_done_action(self):
        e = _entry(type=EntryType.ACTION, status=EntryStatus.DONE, updated_ts="2026-05-30T15:00")
        _, _, updated = _build_meta(e)
        assert updated.plain == "2026-05-30 15:00"

    def test_updated_ts_empty_for_open_action(self):
        e = _entry(type=EntryType.ACTION, status=EntryStatus.OPEN, updated_ts="2026-05-30T15:00")
        _, _, updated = _build_meta(e)
        assert updated.plain == ""

    def test_updated_ts_empty_for_non_action(self):
        e = _entry(type=EntryType.NOTE, updated_ts="2026-05-30T15:00")
        _, _, updated = _build_meta(e)
        assert updated.plain == ""


class TestRenderLogs:
    def test_empty_shows_no_entries_message(self, capturing_console):
        display_mod.render_logs([])
        assert "No entries found" in capturing_console.export_text()

    def test_entries_appear_in_output(self, capturing_console):
        entries = [_entry(project="myproj", text="a note")]
        display_mod.render_logs(entries)
        out = capturing_console.export_text()
        assert "myproj" in out
        assert "a note" in out

    def test_bucket_header_shown(self, capturing_console):
        entries = [_entry(ts="2020-01-01T10:00")]
        display_mod.render_logs(entries)
        assert "Older" in capturing_console.export_text()

    def test_empty_buckets_hidden(self, capturing_console):
        entries = [_entry(ts="2020-01-01T10:00")]
        display_mod.render_logs(entries)
        out = capturing_console.export_text()
        assert "Older" in out
        assert "Today" not in out
        assert "This week" not in out
