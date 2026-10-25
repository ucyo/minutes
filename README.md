# minutes

Project-centric meeting notes and task tracker for the command line.

Capture notes from meetings, track actions and decisions per project, and get a clean weekly summary before giving updates.

## Installation

**Requirements:** Python 3.11+

**From PyPI (recommended):**

```bash
pipx install minutes-cli
```

**Development install:**

```bash
pip install -e .
```

## Usage

### Add entries

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

### Browse entries

```bash
minutes logs                          # all projects, all entries
minutes logs --project api-migration  # one project in detail
minutes logs --since 14               # last 14 days
minutes logs --since mon              # since Monday
```

### Open actions

```bash
minutes logs --open
```

### Web UI

```bash
minutes logs --web
```

Serves the same browse + add flow as a local web page at `http://127.0.0.1:8123` and opens your browser automatically. Use `--port` to pick another port, `--no-open` to skip opening the browser, and `--file` to point at a different store. Initial filters pass through: `minutes logs --web --project api-migration --since mon --open`. Stop with `Ctrl-C`.

### Shell completion

Enable once:

```bash
minutes --install-completion
```

After restarting your shell, `minutes logs -p <TAB>` will autocomplete project names from your store.

## Data

Entries are stored as JSONL at `~/.local/share/minutes/entries.jsonl`.

See [docs/whitepaper.md](docs/whitepaper.md) for the full specification.

## Development

### Running tests

```bash
make test
```

### Publishing to PyPI

Releases are built and uploaded with `twine` inside the test container, using the API tokens in `.pypirc` (which is not committed).

**Dry run against TestPyPI:**

```bash
make dry-run
```

**Publish to PyPI:**

```bash
make push
```

Both targets clean `dist/`, build the sdist and wheel with `python -m build`, validate them with `twine check`, and upload. `make dry-run` targets TestPyPI, while `make push` uploads to PyPI. Bump the `version` in `pyproject.toml` before publishing.
