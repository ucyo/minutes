from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .models import Entry, EntryStatus, EntryType

console = Console()

_DUE_SOON_DAYS = 2


def _due_style(due_str: Optional[str]) -> str:
    if due_str is None:
        return ""
    today = date.today()
    d = date.fromisoformat(due_str)
    if d < today:
        return "bold red"
    if d <= today + timedelta(days=_DUE_SOON_DAYS):
        return "yellow"
    return ""


_TYPE_COLORS = {
    EntryType.DECISION: "blue",
    EntryType.ACTION: "yellow",
    EntryType.WAITING: "magenta",
    EntryType.NOTE: "dim",
}

_TYPE_LABELS = {
    EntryType.DECISION: "decision",
    EntryType.ACTION: "action",
    EntryType.WAITING: "waiting",
    EntryType.NOTE: "note",
}


def _build_line(entry: Entry) -> Text:
    ts = entry.ts[:16].replace("T", " ")
    line = Text()
    line.append(ts, style="dim")
    line.append(f"  {entry.project:<20}", style="cyan")
    line.append("  ")

    color = _TYPE_COLORS[entry.type]
    label = _TYPE_LABELS[entry.type]

    if entry.type == EntryType.ACTION:
        done = entry.status == EntryStatus.DONE
        cancelled = entry.status == EntryStatus.CANCELLED
        if done:
            color = "green"
        elif cancelled:
            color = "dim"
        elif entry.due:
            color = _due_style(entry.due) or color
        checkbox = " [x]" if done else (" [-]" if cancelled else " [ ]")
        line.append(f"{label:<10}", style=color)
        line.append(entry.text + checkbox, style=f"{color} strike" if done else color)
        if entry.due and not done:
            line.append(f"  due {entry.due}", style=_due_style(entry.due) or "dim")

    elif entry.type == EntryType.WAITING:
        line.append(f"{label:<10}", style=color)
        line.append(entry.text, style=color)
        if entry.person:
            line.append(f"  → {entry.person}", style="dim magenta")

    else:
        line.append(f"{label:<10}", style=color)
        line.append(entry.text, style=color)

    return line


def _build_meta(entry: Entry) -> Text:
    meta = Text()
    parts = []
    if entry.meeting:
        parts.append((entry.meeting, "dim"))
    for tag in entry.tags:
        parts.append((f"#{tag}", "dim"))
    if entry.type == EntryType.ACTION and entry.status == EntryStatus.DONE and entry.updated_ts:
        parts.append((f"done {entry.updated_ts[:16].replace('T', ' ')}", "dim"))
    for i, (text, style) in enumerate(parts):
        if i:
            meta.append("  ", style="dim")
        meta.append(text, style=style)
    return meta


def render_logs(
    entries: list[Entry],
    since: Optional[date] = None,
    project: Optional[str] = None,
    show_all: bool = False,
) -> None:
    if not entries:
        console.print("[dim]No entries found.[/dim]")
        return

    sorted_entries = sorted(entries, key=lambda e: e.ts)

    if not show_all:
        for entry in sorted_entries:
            console.print(_build_line(entry))
    else:
        table = Table(box=None, show_header=False, padding=(0, 2, 0, 0))
        table.add_column()
        table.add_column(style="dim")
        for entry in sorted_entries:
            table.add_row(_build_line(entry), _build_meta(entry))
        console.print(table)
