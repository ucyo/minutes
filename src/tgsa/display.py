from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from rich.console import Console
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


def _log_line(entry: Entry, show_project: bool = True) -> None:
    ts = entry.ts[:16].replace("T", " ")
    line = Text()
    line.append(ts, style="dim")

    if show_project:
        line.append(f"  {entry.project:<20}", style="cyan")

    line.append("  ")

    color = _TYPE_COLORS[entry.type]
    label = _TYPE_LABELS[entry.type]

    if entry.type == EntryType.ACTION:
        done = entry.status == EntryStatus.DONE
        if done:
            color = "green"
        elif entry.due:
            color = _due_style(entry.due) or color
        checkbox = " [x]" if done else " [ ]"
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

    console.print(line)


def render_logs(entries: list[Entry], since: Optional[date] = None, project: Optional[str] = None) -> None:
    if not entries:
        console.print("[dim]No entries found.[/dim]")
        return

    for entry in sorted(entries, key=lambda e: e.ts):
        _log_line(entry, show_project=True)




