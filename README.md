# tgsa

Project-centric meeting notes and task tracker for the command line.

Capture notes from meetings, track actions and decisions per project, and get a clean weekly summary before giving updates.

## Getting started

**Requirements:** Python 3.11+

```bash
pip install -e .
```

**Add entries after a meeting:**

```bash
tgsa add
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
tgsa --install-completion
```

After restarting your shell, `tgsa logs -p <TAB>` and `tgsa add -p <TAB>` will autocomplete project names from your store.

**Browse entries:**

```bash
tgsa logs                          # all projects, all entries
tgsa logs --project api-migration  # one project in detail
tgsa logs --since 14               # last 14 days
tgsa logs --since mon              # since Monday
```

**Check open actions:**

```bash
tgsa logs --open
```

## Running tests

```bash
make test
```

## Data

Entries are stored as JSONL at `~/.local/share/tgsa/entries.jsonl`.

See [docs/whitepaper.md](docs/whitepaper.md) for the full specification.
