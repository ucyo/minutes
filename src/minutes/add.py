from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from prompt_toolkit.application import get_app
from prompt_toolkit.formatted_text import HTML

from .models import Entry, EntryStatus, EntryType

_WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _toolbar() -> HTML:
    try:
        text = get_app().current_buffer.text
    except Exception:
        text = ""

    if text.startswith("*"):
        return HTML(
            "  <ansiblue><b>decision</b></ansiblue>  —  type the decision text"
        )
    if text.startswith("!"):
        return HTML(
            "  <ansiyellow><b>action</b></ansiyellow>  —  "
            "due date: <ansigreen>@fri  @7  @2026-05-30</ansigreen>"
        )
    if text.startswith(">"):
        return HTML(
            "  <ansimagenta><b>waiting</b></ansimagenta>  —  "
            "person: <ansigreen>@Person</ansigreen>"
        )
    return HTML(
        "  <ansiblue>*</ansiblue> decision  "
        "<ansiyellow>!</ansiyellow> action  "
        "<ansimagenta>&gt;</ansimagenta> waiting  "
        "note"
        "  │  "
        "Empty line or Ctrl+D to finish"
    )


def _parse_due(token: str) -> Optional[str]:
    today = date.today()
    t = token.lower()
    if t in _WEEKDAYS:
        target_wd = _WEEKDAYS[t]
        delta = (target_wd - today.weekday()) % 7 or 7
        return (today + timedelta(days=delta)).isoformat()
    try:
        return (today + timedelta(days=int(t))).isoformat()
    except ValueError:
        pass
    try:
        return date.fromisoformat(t).isoformat()
    except ValueError:
        return None


def parse_line(raw: str, meeting: Optional[str] = None) -> Optional[Entry]:
    raw = raw.strip()
    if not raw:
        return None

    entry_id = Entry.make_id()
    ts = Entry.now_ts()

    if raw.startswith("*"):
        return Entry(
            id=entry_id, ts=ts, project="",
            type=EntryType.DECISION, text=raw[1:].strip(), meeting=meeting,
        )

    if raw.startswith("!"):
        rest = raw[1:].strip()
        due = None
        m = re.search(r"@(\S+)", rest)
        if m:
            due = _parse_due(m.group(1))
            rest = (rest[: m.start()] + rest[m.end() :]).strip()
        return Entry(
            id=entry_id, ts=ts, project="",
            type=EntryType.ACTION, text=rest, meeting=meeting,
            due=due, status=EntryStatus.OPEN,
        )

    if raw.startswith(">"):
        rest = raw[1:].strip()
        person = None
        m = re.search(r"@(\w+)", rest)
        if m:
            person = m.group(1)
            rest = (rest[: m.start()] + rest[m.end() :]).strip()
        return Entry(
            id=entry_id, ts=ts, project="",
            type=EntryType.WAITING, text=rest, meeting=meeting, person=person,
        )

    return Entry(id=entry_id, ts=ts, project="", type=EntryType.NOTE, text=raw, meeting=meeting)
