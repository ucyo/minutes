from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Optional

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.completion import Completer, Completion
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
from .display import _BUCKET_ORDER, _TS_WIDTH, _date_bucket, format_ts
from .models import Entry, EntryStatus, EntryType
from .store import append_entry, delete_entry, get_projects, mark_done

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


class _ProjectCompleter(Completer):
    def __init__(self, store: Optional[Path] = None):
        self.store = store

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor()
        for project_name in get_projects(self.store):
            if not word or word.lower() in project_name.lower():
                yield Completion(project_name, start_position=-len(word))


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
    highlight_id: Optional[str] = None,
) -> list[tuple[str, str]]:
    from collections import defaultdict

    entry_by_id = {e.id: e for e in entries}

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

        prev_project: Optional[str] = None
        group_idx = 0
        _ALT_BG = ("", "bg:#252525 ")
        for entry_idx, entry in items:
            if prev_project is not None and entry.project != prev_project:
                group_idx += 1
            prev_project = entry.project
            sel = entry_idx == cursor
            if sel:
                lines.append(("[SetCursorPosition]", ""))

            is_parent = highlight_id is not None and entry.id == highlight_id
            bg = (
                "bg:#1e3a5f " if sel
                else "bg:#26301e " if is_parent
                else _ALT_BG[group_idx % 2]
            )
            marker_override = "↑" if is_parent and not sel else None
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

            ts = format_ts(entry.ts, bucket_name).ljust(_TS_WIDTH)
            marker = ">" if sel else (marker_override or " ")

            has_due = (
                entry.type == EntryType.ACTION
                and entry.due
                and entry.status not in (EntryStatus.DONE, EntryStatus.CANCELLED)
            )
            has_person = entry.type == EntryType.WAITING and entry.person

            term_width = get_app().output.get_size().columns
            # prefix: "  {marker} {ts}  " (16) + project (14) + label (11) = 41
            PREFIX = 41
            text_avail = max(1, term_width - PREFIX)

            def _fill(used: int) -> tuple[str, str]:
                return (bg, " " * ((-used) % term_width))

            def _sub_line(text: str, color_: str) -> None:
                lines.append(("", "\n"))
                lines.append((bg, " " * PREFIX))
                lines.append((bg + color_, text))
                lines.append(_fill(PREFIX + len(text)))

            text_full = f"{entry.text}{checkbox}"
            chunks = [text_full[i:i + text_avail] for i in range(0, max(len(text_full), 1), text_avail)]

            proj_sep = "● " if is_parent and not sel else "  "
            lines += [
                (bg + "#888888", f"  {marker} {ts}  "),
                (bg + "ansicyan", f"{entry.project:<12}"),
                (bg + "ansiyellow", proj_sep),
                (bg + color, f"{label:<9}  "),
                (bg + color, chunks[0]),
            ]
            last_len = PREFIX + len(chunks[0])

            for chunk in chunks[1:]:
                lines.append(_fill(last_len))
                lines.append(("", "\n"))
                lines.append((bg, " " * PREFIX))
                lines.append((bg + color, chunk))
                last_len = PREFIX + len(chunk)

            if has_due:
                due_str = f"  due {entry.due}"
                lines.append((bg + "#888888", due_str))
                last_len += len(due_str)
            if has_person:
                person_str = f"  → {entry.person}"
                lines.append((bg + "ansimagenta", person_str))
                last_len += len(person_str)

            lines.append(_fill(last_len))
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

    if not sys.stdout.isatty():
        render_logs(entries, since=since, project=project, show_all=show_all)
        return

    today = date.today()
    sorted_entries = sorted(entries, key=lambda e: e.ts)
    state: dict = {
        "cursor": len(sorted_entries) - 1 if sorted_entries else 0,
        "entries": sorted_entries,
        "editing": False,
        "follow_up": False,
        "edit_entry": None,
        "confirm_delete": False,
        "adding": False,
        "add_error": "",
    }

    is_editing = Condition(lambda: bool(state["editing"]))
    is_confirm_delete = Condition(lambda: bool(state["confirm_delete"]))
    is_adding = Condition(lambda: bool(state["adding"]))
    has_entries = Condition(lambda: bool(state["entries"]))

    def _current_entry() -> Entry:
        return state["entries"][state["cursor"]]

    is_action = Condition(
        lambda: bool(state["entries"]) and _current_entry().type == EntryType.ACTION
    )

    def get_content() -> list[tuple[str, str]]:
        entries = state["entries"]
        if not entries:
            return [("#888888", "  No entries yet — press a to add the first one.\n")]
        cur = entries[state["cursor"]]
        return _build_display(entries, state["cursor"], today, highlight_id=cur.parent_id)

    def get_toolbar() -> HTML:
        if state["editing"]:
            return _edit_toolbar()
        if state["confirm_delete"]:
            return HTML(
                "  <ansired><b>Delete this entry?</b></ansired>"
                "  <ansigreen><b>y</b></ansigreen> confirm"
                "  │  "
                "<b>Esc</b>/<b>n</b> cancel"
            )
        if state["adding"]:
            if state["add_error"]:
                return HTML(
                    f"  <ansired><b>{state['add_error']}</b></ansired>"
                    "  │  "
                    "<b>Tab</b> field  <b>Enter</b> save  <b>Esc</b> cancel"
                )
            return HTML(
                "  <b>Tab</b>/<b>Shift+Tab</b> field"
                "  │  "
                "<ansiyellow><b>Enter</b></ansiyellow> save"
                "  │  "
                "empty Enter closes"
                "  │  "
                "<b>Esc</b> cancel"
            )
        parts = (
            "  <b>↑↓</b> navigate"
            "  │  "
            "<ansiyellow><b>↵</b></ansiyellow> edit"
            "  │  "
            "<ansiblue><b>a</b></ansiblue> add"
        )
        if state["entries"]:
            entry = _current_entry()
            if entry.type == EntryType.ACTION:
                s = entry.status
                parts += "  │"
                if s != EntryStatus.DONE:
                    parts += "  <ansigreen><b>x</b></ansigreen> done"
                if s != EntryStatus.CANCELLED:
                    parts += "  <ansimagenta><b>c</b></ansimagenta> cancel"
                if s in (EntryStatus.DONE, EntryStatus.CANCELLED):
                    parts += "  <ansicyan><b>o</b></ansicyan> reopen"
            parts += (
                "  │  "
                "<b>f</b> follow-up"
                "  │  "
                "<ansired><b>d</b></ansired> delete"
            )
        parts += (
            "  │  "
            "<ansiblue><b>q</b></ansiblue> quit"
        )
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
            title=lambda: "Follow-up  Enter:save  Esc:cancel" if state["follow_up"] else "Edit  Enter:save  Esc:cancel",
            body=edit_body,
            style="",
        ),
        filter=is_editing,
    )

    # --- add overlay ---

    project_locked = project is not None

    add_project_area = TextArea(
        text="", height=1, multiline=False, focusable=True,
        completer=_ProjectCompleter(store),
        read_only=project_locked,
    )
    add_meeting_area = TextArea(text="", height=1, multiline=False, focusable=True)
    add_entry_area = TextArea(multiline=True, dont_extend_height=True, focusable=True)

    add_body = HSplit([
        Window(height=1),
        VSplit([
            Window(width=2),
            HSplit([
                Window(FormattedTextControl("  Project"), height=1),
                add_project_area,
                Window(height=1),
                Window(FormattedTextControl("  Meeting (optional)"), height=1),
                add_meeting_area,
                Window(height=1),
                Window(FormattedTextControl("  Entry"), height=1),
                add_entry_area,
            ]),
            Window(width=2),
        ]),
        Window(height=1),
    ])

    add_overlay = ConditionalContainer(
        content=Frame(
            title="Add entries  Enter:save  empty:close  Esc:cancel",
            body=add_body,
        ),
        filter=is_adding,
    )

    def _add_fields() -> list[TextArea]:
        fields = []
        if not project_locked:
            fields.append(add_project_area)
        fields.append(add_meeting_area)
        fields.append(add_entry_area)
        return fields

    def _focus_next_field(event) -> None:
        fields = _add_fields()
        current = event.app.layout.current_window
        for i, f in enumerate(fields):
            if current == f.window:
                event.app.layout.focus(fields[(i + 1) % len(fields)].window)
                return
        event.app.layout.focus(fields[0].window)

    def _focus_prev_field(event) -> None:
        fields = _add_fields()
        current = event.app.layout.current_window
        for i, f in enumerate(fields):
            if current == f.window:
                event.app.layout.focus(fields[(i - 1) % len(fields)].window)
                return
        event.app.layout.focus(fields[-1].window)

    # --- main layout ---

    main_window = Window(
        FormattedTextControl(get_content, focusable=True),
        wrap_lines=False,
    )

    kb = KeyBindings()

    _browsing = ~is_editing & ~is_confirm_delete & ~is_adding

    @kb.add("up", filter=_browsing & has_entries)
    def _up(event):
        if state["cursor"] > 0:
            state["cursor"] -= 1

    @kb.add("down", filter=_browsing & has_entries)
    def _down(event):
        if state["cursor"] < len(state["entries"]) - 1:
            state["cursor"] += 1

    @kb.add("enter", filter=_browsing & has_entries)
    def _open_edit(event):
        entry = state["entries"][state["cursor"]]
        state["editing"] = True
        state["edit_entry"] = entry
        edit_area.text = _entry_to_raw(entry)
        edit_area.buffer.cursor_position = len(edit_area.text)
        event.app.layout.focus(edit_area.window)

    @kb.add("a", filter=_browsing)
    def _open_add(event):
        state["adding"] = True
        state["add_error"] = ""
        if project:
            add_project_area.text = project
        elif state["entries"]:
            add_project_area.text = state["entries"][state["cursor"]].project
        else:
            add_project_area.text = ""
        if state["entries"]:
            add_meeting_area.text = state["entries"][state["cursor"]].meeting or ""
        else:
            add_meeting_area.text = ""
        add_entry_area.text = ""
        add_project_area.buffer.cursor_position = len(add_project_area.text)
        if not project_locked and not add_project_area.text:
            event.app.layout.focus(add_project_area.window)
        else:
            event.app.layout.focus(add_entry_area.window)

    @kb.add("q", filter=_browsing)
    @kb.add("c-c", filter=_browsing)
    def _quit(event):
        event.app.exit()

    @kb.add("x", filter=_browsing & is_action)
    def _mark_done(event):
        entry = _current_entry()
        if entry.status != EntryStatus.DONE:
            mark_done(entry.id, EntryStatus.DONE, store)
            entry.status = EntryStatus.DONE
            entry.updated_ts = Entry.now_ts()

    @kb.add("c", filter=_browsing & is_action)
    def _mark_cancelled(event):
        entry = _current_entry()
        if entry.status != EntryStatus.CANCELLED:
            mark_done(entry.id, EntryStatus.CANCELLED, store)
            entry.status = EntryStatus.CANCELLED
            entry.updated_ts = Entry.now_ts()

    @kb.add("o", filter=_browsing & is_action)
    def _mark_open(event):
        entry = _current_entry()
        if entry.status != EntryStatus.OPEN:
            mark_done(entry.id, EntryStatus.OPEN, store)
            entry.status = EntryStatus.OPEN
            entry.updated_ts = None

    @kb.add("f", filter=_browsing & has_entries)
    def _follow_up(event):
        parent = _current_entry()
        state["editing"] = True
        state["follow_up"] = True
        state["edit_entry"] = parent
        edit_area.text = "! "
        edit_area.buffer.cursor_position = len(edit_area.text)
        event.app.layout.focus(edit_area.window)

    @kb.add("d", filter=_browsing & has_entries)
    def _delete_prompt(event):
        state["confirm_delete"] = True

    @kb.add("y", filter=is_confirm_delete, eager=True)
    def _confirm_delete(event):
        state["confirm_delete"] = False
        idx = state["cursor"]
        entry = state["entries"][idx]
        delete_entry(entry.id, store)
        state["entries"].pop(idx)
        if not state["entries"]:
            event.app.exit()
            return
        if state["cursor"] >= len(state["entries"]):
            state["cursor"] = len(state["entries"]) - 1

    @kb.add("escape", filter=is_confirm_delete, eager=True)
    @kb.add("n", filter=is_confirm_delete, eager=True)
    def _cancel_delete(event):
        state["confirm_delete"] = False

    @kb.add("escape", filter=has_focus(edit_area.buffer), eager=True)
    @kb.add("c-c", filter=has_focus(edit_area.buffer), eager=True)
    def _cancel(event):
        state["editing"] = False
        state["follow_up"] = False
        event.app.layout.focus(main_window)

    @kb.add("enter", filter=has_focus(edit_area.buffer), eager=True)
    def _confirm(event):
        raw = edit_area.text.strip()
        follow_up = state["follow_up"]
        state["editing"] = False
        state["follow_up"] = False
        if raw and state["edit_entry"]:
            parent = state["edit_entry"]
            new_entry = parse_line(raw)
            if new_entry:
                new_entry.project = parent.project
                new_entry.meeting = parent.meeting
                if follow_up:
                    new_entry.parent_id = parent.id
                    append_entry(new_entry, store)
                    state["entries"].append(new_entry)
                    state["cursor"] = len(state["entries"]) - 1
                else:
                    new_entry.id = parent.id
                    new_entry.ts = parent.ts
                    new_entry.tags = parent.tags
                    new_entry.parent_id = parent.parent_id
                    append_entry(new_entry, store)
                    state["entries"][state["cursor"]] = new_entry
        event.app.layout.focus(main_window)

    # --- add-mode keybindings ---

    @kb.add("tab", filter=is_adding, eager=True)
    def _add_tab(event):
        _focus_next_field(event)

    @kb.add("s-tab", filter=is_adding, eager=True)
    def _add_shift_tab(event):
        _focus_prev_field(event)

    @kb.add("enter", filter=is_adding & has_focus(add_project_area.buffer), eager=True)
    def _add_next_from_project(event):
        _focus_next_field(event)

    @kb.add("enter", filter=is_adding & has_focus(add_meeting_area.buffer), eager=True)
    def _add_next_from_meeting(event):
        _focus_next_field(event)

    @kb.add("enter", filter=is_adding & has_focus(add_entry_area.buffer), eager=True)
    def _add_confirm(event):
        raw = add_entry_area.text.strip()
        if not raw:
            state["adding"] = False
            state["add_error"] = ""
            event.app.layout.focus(main_window)
            return
        entry = parse_line(raw, meeting=add_meeting_area.text.strip() or None)
        if entry is None:
            return
        project_name = project if project_locked else add_project_area.text.strip()
        entry.project = project_name
        if not entry.project:
            state["add_error"] = "Project is required"
            if not project_locked:
                event.app.layout.focus(add_project_area.window)
            return
        append_entry(entry, store)
        state["entries"].append(entry)
        state["entries"].sort(key=lambda e: e.ts)
        state["cursor"] = next(
            i for i, e in enumerate(state["entries"]) if e.id == entry.id
        )
        add_entry_area.text = ""
        state["add_error"] = ""
        event.app.layout.focus(add_entry_area.window)

    @kb.add("escape", filter=is_adding, eager=True)
    @kb.add("c-c", filter=is_adding, eager=True)
    def _add_cancel(event):
        state["adding"] = False
        state["add_error"] = ""
        event.app.layout.focus(main_window)

    layout = Layout(
        FloatContainer(
            content=HSplit([
                main_window,
                Window(FormattedTextControl(get_toolbar), height=1, style="class:bottom-toolbar"),
            ]),
            floats=[
                Float(content=edit_overlay, width=80),
                Float(content=add_overlay, width=80),
            ],
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
