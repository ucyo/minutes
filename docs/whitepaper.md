# minutes — Technical Whitepaper

## 1. Purpose

`minutes` is a command-line tool for capturing, organizing, and retrieving work context across projects. It is optimized for two retrieval patterns:

- **Breadth view**: all active projects summarized for a management update
- **Depth view**: one project's full activity for a team sync

Input happens asynchronously (after meetings, transcribed from paper). Retrieval happens on demand before an update is given. There are no notifications, no push reminders — the tool is pull-based by design.

---

## 2. Core Concepts

### Entry types

| Type | Meaning |
|---|---|
| `note` | Factual information worth remembering (no action required) |
| `action` | Something you need to do, optionally with a due date |
| `decision` | A choice that was made and should be on record |
| `waiting` | Blocked on someone else — you are not the actor |

### Entry status (actions only)

| Status | Meaning |
|---|---|
| `open` | Not yet done (default) |
| `done` | Completed |
| `cancelled` | No longer relevant |

### Projects

Projects are free-form strings. There is no project registry — a project comes into existence the first time it is referenced in an entry. Project names should be lowercase, hyphenated slugs (`api-migration`, `q3-hiring`).

### Follow-ups

An entry can link to a parent via `parent_id`, forming a one-level "follow-up" relationship. Creating a follow-up from an entry (key `f` in the browser, or the `⤴` button in the web UI) adds a new entry whose `parent_id` points at the original, so related work stays traceable while the parent's history is unchanged.

---

## 3. JSONL Schema

Each line in the JSONL file is a self-contained JSON object. Fields:

### Required fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Short unique identifier, e.g. `a3f2b1c` (first 7 chars of a UUID4) |
| `ts` | string | ISO 8601 timestamp, e.g. `2026-05-27T14:30` |
| `project` | string | Project slug |
| `type` | string | One of `note`, `action`, `decision`, `waiting` |
| `text` | string | The content of the entry |

### Optional fields

| Field | Type | Applies to | Description |
|---|---|---|---|
| `meeting` | string | all | Name of the meeting where this was captured |
| `due` | string | `action` | ISO date `YYYY-MM-DD` |
| `status` | string | `action` | `open` (default), `done`, `cancelled` |
| `person` | string | `waiting` | Who you are waiting on |
| `tags` | array of strings | all | Free-form labels, e.g. `["urgent", "infra"]` |
| `updated_ts` | string | `action` | Timestamp of last status change |
| `parent_id` | string | all | `id` of the entry this one follows up (links a follow-up action to its parent) |

### Example entries

```jsonl
{"id": "a3f2b1c", "ts": "2026-05-27T14:30", "project": "api-migration", "meeting": "team sync", "type": "decision", "text": "Drop support for v1 endpoints by end of Q3"}
{"id": "b81c4d2", "ts": "2026-05-27T14:30", "project": "api-migration", "meeting": "team sync", "type": "action", "text": "Write migration guide for downstream consumers", "due": "2026-05-30", "status": "open"}
{"id": "c55d9e3", "ts": "2026-05-27T14:30", "project": "api-migration", "type": "waiting", "text": "v2 spec approval", "person": "Marco"}
{"id": "d0091f4", "ts": "2026-05-27T09:15", "project": "onboarding", "type": "note", "text": "New hire Clara starts June 3, needs laptop provisioned"}
{"id": "e7a15b6", "ts": "2026-05-26T11:00", "project": "billing-rewrite", "meeting": "architecture review", "type": "decision", "text": "Use event sourcing for the audit log"}
```

### Storage

```
~/.local/share/minutes/
    entries.jsonl       # all entries, append-only
```

The file is append-only. Status updates (e.g. marking an action done), edits, and follow-ups write a new entry with the same `id` and updated fields. The last entry for a given `id` is the canonical state. This preserves full history without in-place mutation. Deletion is the one exception: `delete` rewrites the file, dropping every line whose `id` matches.

---

## 4. CLI Interface

### Common flags

These flags are available on the commands where they apply:

```
--file <path>     Override default storage path (`logs`, `info`)
--project <slug>  Scope to a single project (`logs`)
```

---

### Adding entries (from `logs`)

Entries are added from the interactive `logs` browser by pressing `a`, which opens
an add form with three fields: **Project** (prefilled from the currently selected
entry, or locked when `--project` is given), **Meeting** (optional), and **Entry**.
Use `Tab` / `Shift+Tab` to move between fields. Type one entry per line:

```
*  decision     → * Drop v1 endpoints by Q3
!  action       → ! Write migration guide @fri
>  waiting      → > Spec approval from Marco
   note         → Just a note, no prefix needed
```

Press Enter to save each entry; an empty entry line closes the form. Each entry is
written to disk immediately after pressing Enter — a crash mid-session loses at most
the line currently being typed. The `meeting` value applies to every entry added
during the session.

**Inline variant** (no interactive prompt):

```bash
minutes logs --add "* Drop v1 endpoints by Q3" --project api-migration
```

**Date shorthand in `@` suffix:**

| Shorthand | Expands to |
|---|---|
| `@fri` | Next Friday |
| `@2026-05-30` | Absolute date |
| `@7` | 7 days from today |

---

### `minutes logs`

All entries shown chronologically, grouped into date buckets. Oldest entries appear at the top; the most recent bucket (Today) is at the bottom. Designed for update preparation.

```
$ minutes logs

──────────────── This week ──────────────────
Wed 14:30  api-migration  decision  Drop support for v1 endpoints by end of Q3
Wed 14:30  api-migration  action    Write migration guide for downstream consumers [ ]  due 2026-05-30
Wed 14:30  api-migration  waiting   v2 spec approval  → Marco

──────────────── Yesterday ──────────────────
09:15  onboarding     note      New hire Clara starts June 3, needs laptop provisioned

──────────────── Today ──────────────────────
11:00  billing-rewrite  decision  Use event sourcing for the audit log
```

Buckets (oldest first, empty buckets hidden): **Older → This year → Last month → This month → Last week → This week → Yesterday → Today**

Timestamps are rendered at the bucket's granularity: Today/Yesterday show `HH:MM`, This week/Last week show `Wed 14:30`, and older buckets show `YYYY-MM-DD`.

**Flags:**

```
--project <slug>          Filter to one project (also locks the add form's project)
--since <value>           Restrict entries to a time window (optional)
--open                    Show only open actions and waiting entries
--all                     Show additional columns: meeting, tags, done timestamp
--add <text>              Add an entry inline (requires --project) and exit
--web                     Serve entries in a local web UI instead of the TUI
--port <n>                Port for the web UI (only with --web, default 8123)
--no-open                 Do not open the browser when --web starts
```

**`--since` values:**

| Value | Meaning |
|---|---|
| `mon` | Monday of the current week |
| `14` | 14 days ago |
| `2026-05-20` | Absolute date |

When `--since` is omitted, all entries are shown.

### Interactive keybindings

While browsing, the following keys are available:

| Key | Action |
|---|---|
| `↑` / `↓` | Move the selection |
| `Enter` | Edit the selected entry (rewrites via append) |
| `a` | Open the add form |
| `x` | Mark the selected action done |
| `c` | Cancel the selected action |
| `o` | Reopen a done/cancelled action |
| `f` | Create a follow-up action linked to the selected entry |
| `d` | Delete the selected entry (confirmation required) |
| `q` / `Ctrl-C` | Quit |

Edit, status changes, and follow-ups are all append-only writes. Follow-ups are
created with `parent_id` set to the selected entry; when a follow-up is selected,
its parent is highlighted in the list.

### Web UI

```bash
minutes logs --web
```

Serves the same browse, add, edit, follow-up, and delete flow as a self-contained
local web page at `http://127.0.0.1:8123` and opens the browser automatically.
`--port` picks another port, `--no-open` skips opening the browser, and `--file`
points at a different store. Initial filters pass through the URL query string:

```bash
minutes logs --web --project api-migration --since mon --open
```

The web UI adds a newest-first ordering toggle, a date picker for action due dates,
and type-specific add fields. It has no build step and no external assets.

### `minutes info`

```bash
minutes info
```

Prints the package version, store path, and entry count.

---

## 5. Color Scheme

| Element | Color |
|---|---|
| Project name | Bold cyan |
| `decision` | Blue |
| `action` open | Yellow, `[ ]` |
| `action` done | Green, `[x]` (strikethrough in table output) |
| `action` cancelled | Dim, `[-]` |
| `waiting` | Magenta |
| `note` | Dim/default |
| Overdue | Red |
| Due soon (≤ 2 days) | Yellow |

---

## 6. Interaction Flows

### After a meeting

1. Open terminal
2. `minutes logs`
3. Press `a` to open the add form
4. Confirm/adjust the project (prefilled from selection) and optional meeting, then `Tab` to the entry field
5. Transcribe action items, decisions, and notes from paper using prefixes
6. Empty entry line closes the form — takes under 2 minutes

### Before a team lead update

1. `minutes logs --since mon`
2. Read output top to bottom — one line per project

### Before a per-project dev sync

1. `minutes logs --project <slug> --since mon`
2. Use output as the agenda

### In a browser

1. `minutes logs --web`
2. Filter, add, edit, and mark actions from the browser at `http://127.0.0.1:8123`

### Daily check

1. `minutes logs --open`
2. Work through open actions and waiting entries interactively — `x` to mark done, `c` to cancel, `o` to reopen, `f` to add a follow-up, `d` to delete

---

## 7. Design Decisions

**Append-only writes.** The JSONL file is never mutated in place except for deletion. Updates (marking done, correcting text, adding follow-ups) append a new record; the last record for a given `id` is canonical. Deleting an entry rewrites the file to drop that `id`. Append-on-update makes the file safe to sync via Dropbox or git, easy to back up, and fully auditable.

**Write-on-enter.** Each entry is written to disk the moment the user presses Enter, not when the session ends. A crash loses at most the line currently being typed.

**No project registry.** Projects are inferred from entries. This removes a setup step and allows projects to be created mid-session without interrupting the capture flow.

**One application, scoped completion.** The interactive browser is a single `prompt_toolkit` Application with overlay `TextArea` widgets for the add and edit forms. Only the project field gets a fuzzy autocomplete completer, so the completer never leaks into note or entry text.

**Self-contained web UI.** `logs --web` reuses the same store, parsing, and querying code behind a tiny JSON API built on the standard library's `http.server`. The single page ships inline with no build step or external assets, keeping deployment to `pipx install` plus a browser.

**Pull-based retrieval.** No scheduled notifications or reminders. The tool assumes the user already has meeting cadence and knows when to check. Adding push behavior creates noise; the value is in fast retrieval when it matters.

**Flat storage.** One file for all projects and all time. At realistic volumes (hundreds of entries per year), a flat JSONL is faster to query with simple filtering than a database, requires no migrations, and is trivially portable.

---

## 8. Project Structure

```
minutes/
├── pyproject.toml
├── Dockerfile.test
├── docker-compose.yml
├── Makefile
├── docs/
│   └── whitepaper.md
└── src/
    └── minutes/
        ├── __init__.py
        ├── cli.py        # Typer commands and routing
        ├── models.py     # Entry dataclass, type enums, serialization
        ├── store.py      # JSONL read/write, filtering, querying, deletion
        ├── add.py        # entry line parsing and prefix help toolbar
        ├── browse.py     # prompt_toolkit interactive log browser
        ├── display.py    # Rich rendering for non-interactive output
        └── web/
            ├── __init__.py
            ├── server.py   # stdlib HTTP server + JSON API over the store
            └── page.py     # self-contained single-page web UI
```

## 9. Dependencies

| Package | Purpose |
|---|---|
| `typer` | CLI command definitions |
| `rich` | Colored terminal output |
| `prompt_toolkit` | Interactive browser and add/edit forms with autocomplete |
| `pytest` | Test runner (dev only) |
