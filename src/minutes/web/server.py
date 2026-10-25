from __future__ import annotations

import json
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlsplit

from rich.console import Console

from ..add import parse_line
from ..display import _date_bucket
from ..models import Entry, EntryStatus, EntryType
from ..store import (
    append_entry,
    delete_entry,
    filter_entries,
    get_projects,
    load_entries,
    mark_done,
    parse_since,
)
from .page import PAGE


class WebApp:
    """Tiny JSON API over the existing JSONL store."""

    def __init__(self, store: Optional[Path] = None) -> None:
        self.store = store

    # -- dispatch -----------------------------------------------------------

    def dispatch(self, method: str, path: str, body: Optional[bytes]) -> tuple[int, str, bytes]:
        split = urlsplit(path)
        segments = [s for s in split.path.split("/") if s]
        query = {k: v[0] for k, v in parse_qs(split.query).items()}

        if method == "GET":
            if not segments:
                return 200, "text/html; charset=utf-8", PAGE.encode("utf-8")
            if segments == ["api", "entries"]:
                return self._list_entries(query)
        elif method == "POST":
            if segments == ["api", "entries"]:
                return self._add_entries(body)
            if len(segments) == 4 and segments[:2] == ["api", "entries"]:
                if segments[3] == "status":
                    return self._set_status(segments[2], body)
                if segments[3] == "followup":
                    return self._followup(segments[2], body)
        elif method == "PATCH":
            if len(segments) == 3 and segments[:2] == ["api", "entries"]:
                return self._edit_entry(segments[2], body)
        elif method == "DELETE":
            if len(segments) == 3 and segments[:2] == ["api", "entries"]:
                return self._delete_entry(segments[2])

        return self._json({"error": "not found"}, 404)

    # -- helpers ------------------------------------------------------------

    def _json(self, obj: object, status: int = 200) -> tuple[int, str, bytes]:
        return status, "application/json; charset=utf-8", json.dumps(obj).encode("utf-8")

    def _read_json(self, body: Optional[bytes]) -> Optional[dict]:
        if not body:
            return {}
        try:
            data = json.loads(body.decode("utf-8"))
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _find(self, entry_id: str) -> Optional[Entry]:
        return next((e for e in load_entries(self.store) if e.id == entry_id), None)

    # -- endpoints ----------------------------------------------------------

    def _list_entries(self, query: dict) -> tuple[int, str, bytes]:
        try:
            since = parse_since(query["since"]) if query.get("since") else None
            filtered = filter_entries(
                load_entries(self.store),
                since=since,
                project=query.get("project") or None,
                open_only=query.get("open") in ("1", "true", "yes"),
            )
        except ValueError:
            return self._json({"error": "invalid 'since' value"}, 400)

        filtered.sort(key=lambda e: e.ts)
        today = date.today()
        out = []
        for e in filtered:
            d = e.to_dict()
            try:
                d["bucket"] = _date_bucket(date.fromisoformat(e.ts[:10]), today)
            except ValueError:
                d["bucket"] = "Older"
            out.append(d)
        return self._json({"entries": out, "projects": get_projects(self.store)})

    def _add_entries(self, body: Optional[bytes]) -> tuple[int, str, bytes]:
        data = self._read_json(body)
        if data is None:
            return self._json({"error": "invalid JSON body"}, 400)
        project = (data.get("project") or "").strip()
        meeting = (data.get("meeting") or "").strip() or None
        raw = (data.get("raw") or "").strip()
        if not project:
            return self._json({"error": "project is required"}, 400)
        if not raw:
            return self._json({"error": "entry text is required"}, 400)

        created = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            entry = parse_line(line, meeting=meeting)
            if entry is None:
                continue
            entry.project = project
            append_entry(entry, self.store)
            created.append(entry.to_dict())
        return self._json({"entries": created}, 201)

    def _edit_entry(self, entry_id: str, body: Optional[bytes]) -> tuple[int, str, bytes]:
        data = self._read_json(body)
        if data is None:
            return self._json({"error": "invalid JSON body"}, 400)
        raw = (data.get("raw") or "").strip()
        if not raw:
            return self._json({"error": "entry text is required"}, 400)
        parent = self._find(entry_id)
        if parent is None:
            return self._json({"error": "entry not found"}, 404)
        new_entry = parse_line(raw)
        if new_entry is None:
            return self._json({"error": "could not parse entry"}, 400)
        new_entry.id = parent.id
        new_entry.ts = parent.ts
        new_entry.project = parent.project
        new_entry.meeting = parent.meeting
        new_entry.tags = parent.tags
        new_entry.parent_id = parent.parent_id
        append_entry(new_entry, self.store)
        return self._json({"entry": new_entry.to_dict()})

    def _set_status(self, entry_id: str, body: Optional[bytes]) -> tuple[int, str, bytes]:
        data = self._read_json(body)
        if data is None:
            return self._json({"error": "invalid JSON body"}, 400)
        try:
            status = EntryStatus(data.get("status") or "")
        except ValueError:
            return self._json({"error": "invalid status"}, 400)
        target = self._find(entry_id)
        if target is None:
            return self._json({"error": "entry not found"}, 404)
        if target.type != EntryType.ACTION:
            return self._json({"error": "only actions have a status"}, 400)
        updated = mark_done(entry_id, status, self.store)
        return self._json({"entry": updated.to_dict() if updated else None})

    def _followup(self, entry_id: str, body: Optional[bytes]) -> tuple[int, str, bytes]:
        data = self._read_json(body)
        raw = ((data.get("raw") if data else None) or "").strip() or "! "
        parent = self._find(entry_id)
        if parent is None:
            return self._json({"error": "entry not found"}, 404)
        child = parse_line(raw)
        if child is None:
            return self._json({"error": "could not parse entry"}, 400)
        child.project = parent.project
        child.meeting = parent.meeting
        child.parent_id = parent.id
        append_entry(child, self.store)
        return self._json({"entry": child.to_dict()}, 201)

    def _delete_entry(self, entry_id: str) -> tuple[int, str, bytes]:
        if self._find(entry_id) is None:
            return self._json({"error": "entry not found"}, 404)
        delete_entry(entry_id, self.store)
        return 204, "application/json; charset=utf-8", b""


def make_handler(app: WebApp) -> type:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._route("GET")

        def do_POST(self) -> None:
            self._route("POST")

        def do_PATCH(self) -> None:
            self._route("PATCH")

        def do_DELETE(self) -> None:
            self._route("DELETE")

        def _route(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            status, ctype, payload = app.dispatch(method, self.path, body)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if payload:
                self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass

    return Handler


def run(
    store: Optional[Path] = None,
    port: int = 8123,
    open_browser: bool = True,
    initial: Optional[dict] = None,
) -> None:
    """Serve the web UI in the foreground until Ctrl-C."""
    app = WebApp(store)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    url = f"http://127.0.0.1:{server.server_port}"
    target = url
    if initial:
        qs = urlencode(initial)
        if qs:
            target = f"{url}/?{qs}"
    if open_browser:
        webbrowser.open(target)
    Console().print(f"[green]minutes web[/green]  [cyan]{url}[/cyan]  (Ctrl-C to quit)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
