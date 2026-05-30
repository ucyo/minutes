from __future__ import annotations

import json
from importlib.metadata import version as pkg_version
from pathlib import Path

import pytest
from rich.console import Console as RichConsole
from typer.testing import CliRunner

import minutes.cli as cli_mod
import minutes.display as display_mod
from minutes.cli import app
from minutes.models import Entry, EntryStatus, EntryType
from minutes.store import append_entry

runner = CliRunner()


def _entry(**kwargs) -> Entry:
    defaults = dict(
        id=Entry.make_id(),
        ts="2026-05-30T10:00",
        project="proj",
        type=EntryType.NOTE,
        text="hello",
    )
    defaults.update(kwargs)
    return Entry(**defaults)


@pytest.fixture
def captured(monkeypatch):
    """Replace module-level Rich consoles with recording ones."""
    cli_con = RichConsole(record=True, width=200, highlight=False)
    display_con = RichConsole(record=True, width=200, highlight=False)
    monkeypatch.setattr(cli_mod, "console", cli_con)
    monkeypatch.setattr(display_mod, "console", display_con)
    return cli_con, display_con


class TestInlineAdd:
    def test_saves_entry_to_store(self, tmp_path):
        store = tmp_path / "entries.jsonl"
        result = runner.invoke(app, ["add", "--project", "proj", "--file", str(store), "just a note"])
        assert result.exit_code == 0
        data = json.loads(store.read_text().strip())
        assert data["text"] == "just a note"
        assert data["project"] == "proj"

    def test_saves_action_type(self, tmp_path):
        store = tmp_path / "entries.jsonl"
        runner.invoke(app, ["add", "--project", "proj", "--file", str(store), "! do the thing"])
        assert json.loads(store.read_text().strip())["type"] == "action"

    def test_saves_decision_type(self, tmp_path):
        store = tmp_path / "entries.jsonl"
        runner.invoke(app, ["add", "--project", "proj", "--file", str(store), "* a decision"])
        assert json.loads(store.read_text().strip())["type"] == "decision"

    def test_saves_waiting_type(self, tmp_path):
        store = tmp_path / "entries.jsonl"
        runner.invoke(app, ["add", "--project", "proj", "--file", str(store), "> waiting on Marco"])
        assert json.loads(store.read_text().strip())["type"] == "waiting"

    def test_missing_project_exits_nonzero(self, tmp_path):
        store = tmp_path / "entries.jsonl"
        result = runner.invoke(app, ["add", "--file", str(store), "just a note"])
        assert result.exit_code != 0


class TestInfo:
    def test_exits_ok(self, tmp_path):
        store = tmp_path / "entries.jsonl"
        result = runner.invoke(app, ["info", "--file", str(store)])
        assert result.exit_code == 0

    def test_missing_store_shows_not_initialised(self, tmp_path, captured):
        cli_con, _ = captured
        store = tmp_path / "entries.jsonl"
        runner.invoke(app, ["info", "--file", str(store)])
        assert "not initialised" in cli_con.export_text()

    def test_existing_store_shows_count(self, tmp_path, captured):
        cli_con, _ = captured
        store = tmp_path / "entries.jsonl"
        append_entry(_entry(), store)
        append_entry(_entry(), store)
        runner.invoke(app, ["info", "--file", str(store)])
        assert "2" in cli_con.export_text()

    def test_shows_store_path(self, tmp_path, captured):
        cli_con, _ = captured
        store = tmp_path / "entries.jsonl"
        runner.invoke(app, ["info", "--file", str(store)])
        assert str(store) in cli_con.export_text()

    def test_shows_version(self, tmp_path, captured):
        cli_con, _ = captured
        store = tmp_path / "entries.jsonl"
        runner.invoke(app, ["info", "--file", str(store)])
        assert pkg_version("minutes-cli") in cli_con.export_text()


class TestLogs:
    def test_empty_store_exits_ok(self, tmp_path):
        store = tmp_path / "entries.jsonl"
        result = runner.invoke(app, ["logs", "--file", str(store)])
        assert result.exit_code == 0

    def test_shows_all_entries(self, tmp_path, captured):
        _, display_con = captured
        store = tmp_path / "entries.jsonl"
        append_entry(_entry(project="alpha"), store)
        append_entry(_entry(project="beta"), store)
        runner.invoke(app, ["logs", "--file", str(store)])
        out = display_con.export_text()
        assert "alpha" in out
        assert "beta" in out

    def test_filter_by_project(self, tmp_path, captured):
        _, display_con = captured
        store = tmp_path / "entries.jsonl"
        append_entry(_entry(project="alpha"), store)
        append_entry(_entry(project="beta"), store)
        runner.invoke(app, ["logs", "--project", "alpha", "--file", str(store)])
        out = display_con.export_text()
        assert "alpha" in out
        assert "beta" not in out

    def test_open_only_excludes_notes(self, tmp_path, captured):
        _, display_con = captured
        store = tmp_path / "entries.jsonl"
        append_entry(_entry(type=EntryType.NOTE, text="a note"), store)
        append_entry(_entry(type=EntryType.ACTION, text="an action", status=EntryStatus.OPEN), store)
        runner.invoke(app, ["logs", "--open", "--file", str(store)])
        out = display_con.export_text()
        assert "an action" in out
        assert "a note" not in out

    def test_since_filters_old_entries(self, tmp_path, captured):
        _, display_con = captured
        store = tmp_path / "entries.jsonl"
        append_entry(_entry(project="old", ts="2025-01-01T10:00"), store)
        append_entry(_entry(project="new", ts="2026-05-30T10:00"), store)
        runner.invoke(app, ["logs", "--since", "2026-01-01", "--file", str(store)])
        out = display_con.export_text()
        assert "new" in out
        assert "old" not in out
