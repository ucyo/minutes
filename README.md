# minutes

Project-centric meeting notes and task tracker for the command line.

Capture notes from meetings, track actions and decisions per project, and get a clean weekly summary before giving updates.

## Getting started

**Requirements:** Python 3.11+

```bash
pip install -e .
```

**Add entries after a meeting:**

```bash
minutes add
```

You will be prompted for a project name (with autocomplete) and an optional meeting name. Then enter entries one per line:

```
*  decision     → * Drop v1 endpoints by Q3
!  action       → ! Write migration guide @fri
>  waiting      → > Spec approval from Marco
   note         → Just a note, no prefix needed
```

Press Enter on an empty line or Ctrl+D to finish. Each entry is saved immediately.

**Enable shell completion (once):**

```bash
minutes --install-completion
```

After restarting your shell, `minutes logs -p <TAB>` and `minutes add -p <TAB>` will autocomplete project names from your store.

**Browse entries:**

```bash
minutes logs                          # all projects, all entries
minutes logs --project api-migration  # one project in detail
minutes logs --since 14               # last 14 days
minutes logs --since mon              # since Monday
```

**Check open actions:**

```bash
minutes logs --open
```

## Running tests

```bash
make test
```

## Data

Entries are stored as JSONL at `~/.local/share/minutes/entries.jsonl`.

See [docs/whitepaper.md](docs/whitepaper.md) for the full specification.
