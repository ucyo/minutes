from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from minutes.cli import app
from minutes.models import Entry, EntryStatus, EntryType
from minutes.store import append_entry
from minutes.web.server import WebApp

runner = CliRunner()


def _app(tmp_path) -> WebApp:
    return WebApp(tmp_path / "entries.jsonl")


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


def _json(resp):
    status, _ctype, payload = resp
    return status, json.loads(payload.decode())


def _post(body: dict) -> bytes:
    return json.dumps(body).encode()


class TestPage:
    def test_serves_html(self, tmp_path):
        status, ctype, payload = _app(tmp_path).dispatch("GET", "/", None)
        assert status == 200
        assert "text/html" in ctype
        assert b"minutes" in payload


class TestList:
    def test_empty(self, tmp_path):
        status, data = _json(_app(tmp_path).dispatch("GET", "/api/entries", None))
        assert status == 200
        assert data == {"entries": [], "projects": []}

    def test_lists_entries_sorted_with_bucket(self, tmp_path):
        app = _app(tmp_path)
        append_entry(_entry(project="alpha", ts="2026-01-01T10:00"), app.store)
        append_entry(_entry(project="beta", ts="2026-05-30T10:00"), app.store)
        status, data = _json(app.dispatch("GET", "/api/entries", None))
        assert status == 200
        assert [e["project"] for e in data["entries"]] == ["alpha", "beta"]
        assert all("bucket" in e for e in data["entries"])

    def test_filter_project(self, tmp_path):
        app = _app(tmp_path)
        append_entry(_entry(project="alpha"), app.store)
        append_entry(_entry(project="beta"), app.store)
        _, data = _json(app.dispatch("GET", "/api/entries?project=alpha", None))
        assert [e["project"] for e in data["entries"]] == ["alpha"]

    def test_filter_open(self, tmp_path):
        app = _app(tmp_path)
        append_entry(_entry(type=EntryType.NOTE, text="a note"), app.store)
        append_entry(_entry(type=EntryType.ACTION, text="an action", status=EntryStatus.OPEN), app.store)
        _, data = _json(app.dispatch("GET", "/api/entries?open=1", None))
        assert [e["text"] for e in data["entries"]] == ["an action"]

    def test_filter_since(self, tmp_path):
        app = _app(tmp_path)
        append_entry(_entry(ts="2025-01-01T10:00"), app.store)
        append_entry(_entry(ts="2026-05-30T10:00"), app.store)
        _, data = _json(app.dispatch("GET", "/api/entries?since=2026-01-01", None))
        assert [e["ts"] for e in data["entries"]] == ["2026-05-30T10:00"]

    def test_invalid_since(self, tmp_path):
        status, _ = _json(_app(tmp_path).dispatch("GET", "/api/entries?since=notadate", None))
        assert status == 400


class TestAdd:
    def test_add_note(self, tmp_path):
        app = _app(tmp_path)
        status, data = _json(app.dispatch("POST", "/api/entries", _post({"raw": "just a note", "project": "proj"})))
        assert status == 201
        assert data["entries"][0]["type"] == "note"
        assert app.store.read_text().strip()

    def test_add_action_with_due(self, tmp_path):
        app = _app(tmp_path)
        status, data = _json(app.dispatch("POST", "/api/entries", _post({"raw": "! do the thing @fri", "project": "proj"})))
        assert status == 201
        e = data["entries"][0]
        assert e["type"] == "action"
        assert e["status"] == "open"
        assert e["due"]

    def test_add_multiple_lines(self, tmp_path):
        app = _app(tmp_path)
        status, data = _json(app.dispatch("POST", "/api/entries", _post({"raw": "note one\n! action two", "project": "proj"})))
        assert status == 201
        assert [e["type"] for e in data["entries"]] == ["note", "action"]

    def test_missing_project(self, tmp_path):
        app = _app(tmp_path)
        status, _ = _json(app.dispatch("POST", "/api/entries", _post({"raw": "hi"})))
        assert status == 400

    def test_missing_text(self, tmp_path):
        app = _app(tmp_path)
        status, _ = _json(app.dispatch("POST", "/api/entries", _post({"project": "proj"})))
        assert status == 400


class TestEdit:
    def test_edits_preserving_identity(self, tmp_path):
        app = _app(tmp_path)
        e = _entry(project="proj", ts="2026-05-30T10:00", type=EntryType.NOTE, text="old")
        append_entry(e, app.store)
        status, data = _json(app.dispatch("PATCH", f"/api/entries/{e.id}", _post({"raw": "new text"})))
        assert status == 200
        assert data["entry"]["text"] == "new text"
        assert data["entry"]["id"] == e.id
        assert data["entry"]["ts"] == e.ts
        assert data["entry"]["project"] == "proj"

    def test_edit_unknown(self, tmp_path):
        status, _ = _json(_app(tmp_path).dispatch("PATCH", "/api/entries/nope", _post({"raw": "x"})))
        assert status == 404


class TestStatus:
    def test_mark_done(self, tmp_path):
        app = _app(tmp_path)
        e = _entry(type=EntryType.ACTION, status=EntryStatus.OPEN)
        append_entry(e, app.store)
        status, data = _json(app.dispatch("POST", f"/api/entries/{e.id}/status", _post({"status": "done"})))
        assert status == 200
        assert data["entry"]["status"] == "done"

    def test_status_on_note_rejected(self, tmp_path):
        app = _app(tmp_path)
        e = _entry(type=EntryType.NOTE)
        append_entry(e, app.store)
        status, _ = _json(app.dispatch("POST", f"/api/entries/{e.id}/status", _post({"status": "done"})))
        assert status == 400

    def test_invalid_status(self, tmp_path):
        app = _app(tmp_path)
        e = _entry(type=EntryType.ACTION, status=EntryStatus.OPEN)
        append_entry(e, app.store)
        status, _ = _json(app.dispatch("POST", f"/api/entries/{e.id}/status", _post({"status": "nope"})))
        assert status == 400


class TestFollowup:
    def test_creates_child(self, tmp_path):
        app = _app(tmp_path)
        parent = _entry(project="proj", meeting="sync")
        append_entry(parent, app.store)
        status, data = _json(app.dispatch("POST", f"/api/entries/{parent.id}/followup", _post({"raw": "! follow up later"})))
        assert status == 201
        child = data["entry"]
        assert child["parent_id"] == parent.id
        assert child["project"] == "proj"
        assert child["meeting"] == "sync"


class TestDelete:
    def test_deletes(self, tmp_path):
        app = _app(tmp_path)
        e = _entry()
        append_entry(e, app.store)
        status, _, payload = app.dispatch("DELETE", f"/api/entries/{e.id}", None)
        assert status == 204
        assert payload == b""
        assert app.store.read_text() == ""

    def test_delete_unknown(self, tmp_path):
        status, _ = _json(_app(tmp_path).dispatch("DELETE", "/api/entries/nope", None))
        assert status == 404


class TestCliWeb:
    def test_web_flag_calls_run(self, monkeypatch, tmp_path):
        import minutes.web.server as server_mod

        calls = {}

        def fake_run(store=None, port=8123, open_browser=True, initial=None):
            calls.update(store=store, port=port, open_browser=open_browser, initial=initial)

        monkeypatch.setattr(server_mod, "run", fake_run)
        store = tmp_path / "entries.jsonl"
        result = runner.invoke(
            app,
            ["logs", "--web", "--no-open", "--port", "9000", "--project", "proj", "--since", "mon", "--file", str(store)],
        )
        assert result.exit_code == 0
        assert calls["port"] == 9000
        assert calls["open_browser"] is False
        assert calls["initial"] == {"project": "proj", "since": "mon"}
        assert calls["store"] == Path(str(store))
