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
minutes logs
```

Press `a` to open the add form. The project is prefilled from the selected entry (or locked to `--project` when given). Then enter entries one per line:

```
*  decision     → * Drop v1 endpoints by Q3
!  action       → ! Write migration guide @fri
>  waiting      → > Spec approval from Marco
   note         → Just a note, no prefix needed
```

Press Enter to save each entry; an empty entry line closes the form. Each entry is saved immediately.

For one-off entries from scripts, add inline:

```bash
minutes logs --add "Write migration guide @fri" --project api-migration
```

**Enable shell completion (once):**

```bash
minutes --install-completion
```

After restarting your shell, `minutes logs -p <TAB>` will autocomplete project names from your store.

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
