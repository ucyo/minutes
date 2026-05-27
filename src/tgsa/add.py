from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import FuzzyWordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console

from .display import _TYPE_COLORS, _TYPE_LABELS
from .models import Entry, EntryStatus, EntryType
from .store import append_entry, get_projects

console = Console()

_STYLE = Style.from_dict({
    "bottom-toolbar": "bg:#2a2a2a #888888",
    "completion-menu.completion": "bg:#1e3a5f #ffffff",
    "completion-menu.completion.current": "bg:#0066cc #ffffff",
})

_WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

_entry_bindings = KeyBindings()

@_entry_bindings.add("c-d")
def _exit_on_ctrl_d(event):
    event.app.exit(exception=EOFError())


def _toolbar() -> HTML:
    return HTML(
        "  <b>Prefixes:</b>  "
        "<ansiblue>*</ansiblue> decision  "
        "<ansiyellow>!</ansiyellow> action  "
        "<ansimagenta>&gt;</ansimagenta> waiting  "
        "(none) note"
        "  │  "
        "<b>Date:</b> <ansigreen>@fri  @7  @2026-05-30</ansigreen>"
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
        m = re.search(r"(?:from|→)\s+(\w+)", rest, re.IGNORECASE)
        if m:
            person = m.group(1)
            rest = (rest[: m.start()] + rest[m.end() :]).strip()
        return Entry(
            id=entry_id, ts=ts, project="",
            type=EntryType.WAITING, text=rest, meeting=meeting, person=person,
        )

    return Entry(id=entry_id, ts=ts, project="", type=EntryType.NOTE, text=raw, meeting=meeting)


def _echo_entry(entry: Entry) -> None:
    color = _TYPE_COLORS[entry.type]
    label = _TYPE_LABELS[entry.type]
    extra = ""
    if entry.due:
        extra += f" [dim]due {entry.due}[/dim]"
    if entry.person:
        extra += f" [dim]→ {entry.person}[/dim]"
    console.print(f"  [{color}]{label:10}[/{color}] {entry.text}{extra}")


def run_add(store: Optional[Path] = None) -> None:
    projects = get_projects(store)
    project_session: PromptSession = PromptSession(
        style=_STYLE, completer=FuzzyWordCompleter(projects)
    )
    entry_session: PromptSession = PromptSession(style=_STYLE)

    console.print()

    try:
        project = project_session.prompt(
            HTML("<ansiblue><b>Project: </b></ansiblue>"),
        ).strip()
    except (EOFError, KeyboardInterrupt):
        console.print("[dim]Aborted.[/dim]")
        return

    if not project:
        console.print("[dim]Aborted.[/dim]")
        return

    try:
        meeting_raw = entry_session.prompt(HTML("<ansicyan>Meeting (optional): </ansicyan>")).strip()
    except (EOFError, KeyboardInterrupt):
        console.print("[dim]Aborted.[/dim]")
        return

    meeting = meeting_raw or None
    console.print()

    saved = 0
    while True:
        try:
            raw = entry_session.prompt(HTML("<b>→ </b>"), bottom_toolbar=_toolbar, key_bindings=_entry_bindings)
        except (EOFError, KeyboardInterrupt):
            break

        if not raw.strip():
            break

        entry = parse_line(raw, meeting)
        if entry is None:
            continue

        entry.project = project
        append_entry(entry, store)
        _echo_entry(entry)
        saved += 1

    if saved == 0:
        console.print()
        console.print("[dim]Nothing saved.[/dim]")
        return

    console.print()
    noun = "entry" if saved == 1 else "entries"
    console.print(f"[green]Saved {saved} {noun} to[/green] [bold cyan]{project}[/bold cyan].")
