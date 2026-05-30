from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .models import Entry, EntryStatus, EntryType

console = Console()

_DUE_SOON_DAYS = 2

_BUCKET_ORDER = ["Older", "This year", "This month", "This week", "Yesterday", "Today"]


def _date_bucket(entry_date: date, today: date) -> str:
    if entry_date == today:
        return "Today"
    if entry_date == today - timedelta(days=1):
        return "Yesterday"
    if entry_date.isocalendar()[:2] == today.isocalendar()[:2]:
        return "This week"
    if entry_date.year == today.year and entry_date.month == today.month:
        return "This month"
    if entry_date.year == today.year:
        return "This year"
    return "Older"


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


def _build_parts(entry: Entry) -> tuple[Text, Text]:
    """Return (label, content) Text objects for a single entry."""
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
        content = Text()
        content.append(entry.text + checkbox, style=f"{color} strike" if done else color)
        if entry.due and not done and not cancelled:
            content.append(f"  due {entry.due}", style=_due_style(entry.due) or "dim")

    elif entry.type == EntryType.WAITING:
        content = Text()
        content.append(entry.text, style=color)
        if entry.person:
            content.append(f"  → {entry.person}", style="dim magenta")

    else:
        content = Text(entry.text, style=color)

    return Text(label, style=color), content


def _build_meta(entry: Entry) -> tuple[Text, Text, Text]:
    """Return (meeting, tags, updated_ts) as separate Text objects."""
    meeting = Text(entry.meeting or "", style="dim")
    tags = Text("  ".join(f"#{t}" for t in entry.tags), style="dim")
    updated = Text()
    if entry.type == EntryType.ACTION and entry.status == EntryStatus.DONE and entry.updated_ts:
        updated = Text(entry.updated_ts[:16].replace("T", " "), style="dim")
    return meeting, tags, updated


def _make_table(show_all: bool) -> Table:
    table = Table(box=None, show_header=False, padding=(0, 2, 0, 0))
    table.add_column(no_wrap=True)   # timestamp
    table.add_column(no_wrap=True)   # project
    table.add_column(no_wrap=True)   # type label
    table.add_column()               # content — wraps here
    if show_all:
        table.add_column(no_wrap=True)  # meeting
        table.add_column(no_wrap=True)  # tags
        table.add_column(no_wrap=True)  # updated_ts
    return table


def _add_row(table: Table, entry: Entry, show_all: bool) -> None:
    ts = Text(entry.ts[:16].replace("T", " "), style="dim")
    proj = Text(entry.project, style="cyan")
    label, content = _build_parts(entry)
    if show_all:
        meeting, tags, updated = _build_meta(entry)
        table.add_row(ts, proj, label, content, meeting, tags, updated)
    else:
        table.add_row(ts, proj, label, content)


def render_logs(
    entries: list[Entry],
    since: Optional[date] = None,
    project: Optional[str] = None,
    show_all: bool = False,
) -> None:
    if not entries:
        console.print("[dim]No entries found.[/dim]")
        return

    today = date.today()
    sorted_entries = sorted(entries, key=lambda e: e.ts)

    groups: dict[str, list[Entry]] = {b: [] for b in _BUCKET_ORDER}
    for entry in sorted_entries:
        bucket = _date_bucket(date.fromisoformat(entry.ts[:10]), today)
        groups[bucket].append(entry)

    first = True
    for bucket in _BUCKET_ORDER:
        bucket_entries = groups[bucket]
        if not bucket_entries:
            continue
        if not first:
            console.print()
        console.rule(f"[dim]{bucket}[/dim]", style="dim")
        table = _make_table(show_all)
        for entry in bucket_entries:
            _add_row(table, entry, show_all)
        console.print(table)
        first = False
