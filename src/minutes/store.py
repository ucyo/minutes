from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from .models import Entry, EntryStatus, EntryType

DEFAULT_PATH = Path.home() / ".local" / "share" / "minutes" / "entries.jsonl"


def get_store_path(override: Optional[Path] = None) -> Path:
    p = override or DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append_entry(entry: Entry, store: Optional[Path] = None) -> None:
    path = get_store_path(store)
    with open(path, "a") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")


def load_entries(store: Optional[Path] = None) -> list[Entry]:
    path = get_store_path(store)
    if not path.exists():
        return []
    seen: dict[str, Entry] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                seen[d["id"]] = Entry.from_dict(d)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return list(seen.values())


def get_projects(store: Optional[Path] = None) -> list[str]:
    entries = load_entries(store)
    projects: dict[str, str] = {}
    for e in entries:
        if e.project not in projects or e.ts > projects[e.project]:
            projects[e.project] = e.ts
    return sorted(projects.keys())


def parse_since(value: str) -> date:
    today = date.today()
    if value == "mon":
        return today - timedelta(days=today.weekday())
    try:
        days = int(value)
        return today - timedelta(days=days)
    except ValueError:
        pass
    return date.fromisoformat(value)


def filter_entries(
    entries: list[Entry],
    since: Optional[date] = None,
    project: Optional[str] = None,
    entry_type: Optional[EntryType] = None,
    open_only: bool = False,
) -> list[Entry]:
    result = []
    for e in entries:
        if since and date.fromisoformat(e.ts[:10]) < since:
            continue
        if project and e.project != project:
            continue
        if entry_type and e.type != entry_type:
            continue
        if open_only:
            if e.type == EntryType.ACTION:
                if e.status in (EntryStatus.DONE, EntryStatus.CANCELLED):
                    continue
            elif e.type != EntryType.WAITING:
                continue
        result.append(e)
    return result


def delete_entry(entry_id: str, store: Optional[Path] = None) -> None:
    """Rewrite the store, dropping every line whose id matches entry_id."""
    path = get_store_path(store)
    if not path.exists():
        return
    lines = path.read_text().splitlines()
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            if json.loads(stripped).get("id") != entry_id:
                kept.append(stripped)
        except (json.JSONDecodeError, KeyError):
            kept.append(stripped)
    path.write_text("\n".join(kept) + ("\n" if kept else ""))


def mark_done(
    entry_id: str,
    status: EntryStatus = EntryStatus.DONE,
    store: Optional[Path] = None,
) -> Optional[Entry]:
    entries = load_entries(store)
    target = next((e for e in entries if e.id == entry_id), None)
    if target is None:
        return None
    target.status = status
    target.updated_ts = Entry.now_ts()
    append_entry(target, store)
    return target
