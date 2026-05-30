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

The file is append-only. Status updates (e.g. marking an action done) write a new entry with the same `id` and updated `status` and `updated_ts` fields. The last entry for a given `id` is the canonical state. This preserves full history without in-place mutation.

---

## 4. CLI Interface

### Common flags

These flags are available on most commands where they apply:

```
--file <path>     Override default storage path (all commands)
--project <slug>  Scope to a single project
```

---

### `minutes add`

Interactively add one or more entries after a meeting.

```
$ minutes add
Project: api[↵]          ← fuzzy autocomplete from existing projects
  → api-migration
  → api-gateway

Meeting (optional): team sync

→ * Drop v1 endpoints by Q3
→ ! Write migration guide @fri
→ > v2 spec from Marco
→ just a note here
→
```

The bottom toolbar remains visible while typing entries:

```
Prefixes:  * decision  ! action  > waiting  (none) note  │  Date: @fri  @7  @2026-05-30  │  Empty line or Ctrl+D to finish
```

Each entry is written to disk immediately after pressing Enter — a crash mid-session loses at most the line currently being typed.

**Inline variant** (no interactive prompt):

```bash
minutes add --project api-migration "* Drop v1 endpoints by Q3"
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
2026-05-27 14:30  api-migration  decision  Drop support for v1 endpoints by end of Q3
2026-05-27 14:30  api-migration  action    Write migration guide for downstream consumers [ ]  due 2026-05-30
2026-05-27 14:30  api-migration  waiting   v2 spec approval  → Marco

──────────────── Yesterday ──────────────────
2026-05-29 09:15  onboarding     note      New hire Clara starts June 3, needs laptop provisioned

──────────────── Today ──────────────────────
2026-05-30 11:00  billing-rewrite  decision  Use event sourcing for the audit log
```

Buckets (oldest first, empty buckets hidden): **Older → This year → This month → This week → Yesterday → Today**

**Flags:**

```
--project <slug>          Filter to one project
--since <value>           Restrict entries to a time window (optional)
--open                    Show only open actions and waiting entries
--all                     Show additional columns: meeting, tags, done timestamp
```

**`--since` values:**

| Value | Meaning |
|---|---|
| `mon` | Monday of the current week |
| `14` | 14 days ago |
| `2026-05-20` | Absolute date |

When `--since` is omitted, all entries are shown.

---

## 5. Color Scheme

| Element | Color |
|---|---|
| Project name | Bold cyan |
| `decision` | Blue |
| `action` open | Yellow |
| `action` done | Green + strikethrough |
| `waiting` | Magenta |
| `note` | Dim/default |
| Overdue | Red |
| Due soon (≤ 2 days) | Yellow |

---

## 6. Interaction Flows

### After a meeting

1. Open terminal
2. `minutes add`
3. Enter project name — autocomplete suggests existing slugs
4. Enter optional meeting name
5. Transcribe action items, decisions, and notes from paper using prefixes
6. Empty line or Ctrl+D to finish — takes under 2 minutes

### Before a team lead update

1. `minutes logs --since mon`
2. Read output top to bottom — one line per project

### Before a per-project dev sync

1. `minutes logs --project <slug> --since mon`
2. Use output as the agenda

### Daily check

1. `minutes logs --open`
2. Work through open actions and waiting entries interactively

---

## 7. Design Decisions

**Append-only writes.** The JSONL file is never mutated in place. Updates (marking done, correcting text) append a new record. The last record for a given `id` is canonical. This makes the file safe to sync via Dropbox or git, easy to back up, and fully auditable.

**Write-on-enter.** Each entry is written to disk the moment the user presses Enter, not when the session ends. A crash loses at most the line currently being typed.

**No project registry.** Projects are inferred from entries. This removes a setup step and allows projects to be created mid-session without interrupting the capture flow.

**Two prompt sessions.** The interactive add flow uses separate `PromptSession` instances for project entry (with fuzzy autocomplete) and for the entry loop (no completer). This prevents the completer from leaking into note input.

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
        ├── store.py      # JSONL read/write, filtering, querying
        ├── add.py        # prompt_toolkit interactive add flow
        └── display.py    # Rich rendering for all output commands
```

## 9. Dependencies

| Package | Purpose |
|---|---|
| `typer` | CLI command definitions |
| `rich` | Colored terminal output |
| `prompt_toolkit` | Interactive add flow with autocomplete |
| `pytest` | Test runner (dev only) |
