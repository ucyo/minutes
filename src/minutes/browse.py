from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Optional

from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, TextArea

from .add import _toolbar as _edit_toolbar, parse_line
from .display import _BUCKET_ORDER, _date_bucket
from .models import Entry, EntryStatus, EntryType
from .store import append_entry, mark_done

_PT_COLORS = {
    EntryType.DECISION: "ansiblue",
    EntryType.ACTION: "ansiyellow",
    EntryType.WAITING: "ansimagenta",
    EntryType.NOTE: "#888888",
}

_STYLE = Style.from_dict({
    "bottom-toolbar": "bg:#2a2a2a #888888",
    "completion-menu.completion": "bg:#1e3a5f #ffffff",
    "completion-menu.completion.current": "bg:#0066cc #ffffff",
    "frame.border": "#555555",
    "frame.label": "#888888",
    "text-area": "#cccccc",
    "text-area last-line": "#cccccc",
})


def _entry_to_raw(entry: Entry) -> str:
    if entry.type == EntryType.DECISION:
        return f"* {entry.text}"
    if entry.type == EntryType.ACTION:
        raw = f"! {entry.text}"
        if entry.due:
            raw += f" @{entry.due}"
        return raw
    if entry.type == EntryType.WAITING:
        raw = f"> {entry.text}"
        if entry.person:
            raw += f" @{entry.person}"
        return raw
    return entry.text


def _build_display(
    entries: list[Entry],
    cursor: int,
    today: date,
) -> list[tuple[str, str]]:
    from collections import defaultdict

    groups: dict[str, list[tuple[int, Entry]]] = defaultdict(list)
    for i, entry in enumerate(entries):
        bucket = _date_bucket(date.fromisoformat(entry.ts[:10]), today)
        groups[bucket].append((i, entry))

    lines: list[tuple[str, str]] = []
    first_bucket = True

    for bucket_name in _BUCKET_ORDER:
        items = groups.get(bucket_name, [])
        if not items:
            continue

        if not first_bucket:
            lines.append(("", "\n"))
        first_bucket = False

        lines.append(("#888888", f"  {bucket_name}\n"))

        for entry_idx, entry in items:
            sel = entry_idx == cursor
            if sel:
                lines.append(("[SetCursorPosition]", ""))

            bg = "bg:#1e3a5f " if sel else ""
            color = _PT_COLORS[entry.type]
            label = entry.type.value

            checkbox = ""
            if entry.type == EntryType.ACTION:
                if entry.status == EntryStatus.DONE:
                    color = "ansigreen"
                    checkbox = " [x]"
                elif entry.status == EntryStatus.CANCELLED:
                    color = "#888888"
                    checkbox = " [-]"
                else:
                    checkbox = " [ ]"

            ts = entry.ts[:16].replace("T", " ")
            marker = ">" if sel else " "

            lines += [
                (bg + "#888888", f"  {marker} {ts}  "),
                (bg + "ansicyan", f"{entry.project:<12}  "),
                (bg + color, f"{label:<9}  "),
                (bg + color, f"{entry.text}{checkbox}"),
            ]

            if (
                entry.type == EntryType.ACTION
                and entry.due
                and entry.status not in (EntryStatus.DONE, EntryStatus.CANCELLED)
            ):
                lines.append((bg + "#888888", f"  due {entry.due}"))
            if entry.type == EntryType.WAITING and entry.person:
                lines.append((bg + "ansimagenta", f"  → {entry.person}"))

            lines.append(("", "\n"))

    return lines


def run_logs_interactive(
    entries: list[Entry],
    store: Optional[Path] = None,
    since: Optional[date] = None,
    project: Optional[str] = None,
    show_all: bool = False,
) -> None:
    from .display import render_logs
    from rich.console import Console

    if not entries:
        Console().print("[dim]No entries found.[/dim]")
        return

    if not sys.stdout.isatty():
        render_logs(entries, since=since, project=project, show_all=show_all)
        return

    today = date.today()
    sorted_entries = sorted(entries, key=lambda e: e.ts)
    state: dict = {"cursor": len(sorted_entries) - 1, "entries": sorted_entries, "editing": False, "edit_entry": None}

    is_editing = Condition(lambda: bool(state["editing"]))

    def _current_entry() -> Entry:
        return state["entries"][state["cursor"]]

    is_action = Condition(lambda: _current_entry().type == EntryType.ACTION)

    def get_content() -> list[tuple[str, str]]:
        return _build_display(state["entries"], state["cursor"], today)

    def get_toolbar() -> HTML:
        if state["editing"]:
            return _edit_toolbar()
        parts = (
            "  <b>↑↓</b> navigate"
            "  │  "
            "<ansiyellow><b>↵</b></ansiyellow> edit"
        )
        entry = _current_entry()
        if entry.type == EntryType.ACTION:
            s = entry.status
            parts += "  │"
            if s != EntryStatus.DONE:
                parts += "  <ansigreen><b>d</b>/<b>x</b></ansigreen> done"
            if s != EntryStatus.CANCELLED:
                parts += "  <ansimagenta><b>c</b></ansimagenta> cancel"
            if s in (EntryStatus.DONE, EntryStatus.CANCELLED):
                parts += "  <ansicyan><b>o</b></ansicyan> reopen"
        parts += "  │  <ansiblue><b>q</b></ansiblue> quit"
        return HTML(parts)

    # --- edit overlay ---

    edit_area = TextArea(multiline=True, dont_extend_height=True, focusable=True)

    edit_body = HSplit([
        Window(height=1),
        VSplit([Window(width=2), edit_area, Window(width=2)]),
        Window(height=1),
    ])

    edit_overlay = ConditionalContainer(
        content=Frame(
            title="Edit  Enter:save  Esc:cancel",
            body=edit_body,
            style="",
        ),
        filter=is_editing,
    )

    # --- main layout ---

    main_window = Window(
        FormattedTextControl(get_content, focusable=True),
        wrap_lines=False,
    )

    kb = KeyBindings()

    @kb.add("up", filter=~is_editing)
    def _up(event):
        if state["cursor"] > 0:
            state["cursor"] -= 1

    @kb.add("down", filter=~is_editing)
    def _down(event):
        if state["cursor"] < len(state["entries"]) - 1:
            state["cursor"] += 1

    @kb.add("enter", filter=~is_editing)
    def _open_edit(event):
        entry = state["entries"][state["cursor"]]
        state["editing"] = True
        state["edit_entry"] = entry
        edit_area.text = _entry_to_raw(entry)
        edit_area.buffer.cursor_position = len(edit_area.text)
        event.app.layout.focus(edit_area.window)

    @kb.add("q", filter=~is_editing)
    @kb.add("c-c", filter=~is_editing)
    def _quit(event):
        event.app.exit()

    @kb.add("d", filter=~is_editing & is_action)
    @kb.add("x", filter=~is_editing & is_action)
    def _mark_done(event):
        entry = _current_entry()
        if entry.status != EntryStatus.DONE:
            updated = mark_done(entry.id, EntryStatus.DONE, store)
            if updated:
                state["entries"][state["cursor"]] = updated

    @kb.add("c", filter=~is_editing & is_action)
    def _mark_cancelled(event):
        entry = _current_entry()
        if entry.status != EntryStatus.CANCELLED:
            updated = mark_done(entry.id, EntryStatus.CANCELLED, store)
            if updated:
                state["entries"][state["cursor"]] = updated

    @kb.add("o", filter=~is_editing & is_action)
    def _mark_open(event):
        entry = _current_entry()
        if entry.status != EntryStatus.OPEN:
            updated = mark_done(entry.id, EntryStatus.OPEN, store)
            if updated:
                state["entries"][state["cursor"]] = updated

    @kb.add("escape", filter=has_focus(edit_area.buffer), eager=True)
    @kb.add("c-c", filter=has_focus(edit_area.buffer), eager=True)
    def _cancel(event):
        state["editing"] = False
        event.app.layout.focus(main_window)

    @kb.add("enter", filter=has_focus(edit_area.buffer), eager=True)
    def _confirm(event):
        raw = edit_area.text.strip()
        state["editing"] = False
        if raw and state["edit_entry"]:
            entry = state["edit_entry"]
            new_entry = parse_line(raw)
            if new_entry:
                new_entry.id = entry.id
                new_entry.ts = entry.ts
                new_entry.project = entry.project
                new_entry.meeting = entry.meeting
                new_entry.tags = entry.tags
                append_entry(new_entry, store)
                state["entries"][state["cursor"]] = new_entry
        event.app.layout.focus(main_window)

    layout = Layout(
        FloatContainer(
            content=HSplit([
                main_window,
                Window(FormattedTextControl(get_toolbar), height=1, style="class:bottom-toolbar"),
            ]),
            floats=[Float(content=edit_overlay, width=80)],
        ),
        focused_element=main_window,
    )

    Application(
        layout=layout,
        key_bindings=kb,
        style=_STYLE,
        full_screen=True,
        mouse_support=False,
    ).run()
