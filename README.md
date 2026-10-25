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

Releases are built and published by the GitHub Actions workflow in `.github/workflows/release.yml`, which runs on `v*` tags. It builds the sdist and wheel, creates a GitHub release with the artifacts attached, and publishes to PyPI via OIDC trusted publishing (no API tokens). Beta/rc/dev tags are published as GitHub pre-releases.

**Release a version:**

```bash
uvx hatch version beta          # bump, e.g. 0.2.1 -> 0.2.1b0
uv lock                         # sync uv.lock
git add pyproject.toml uv.lock
git commit -m "chore: bump version to 0.2.1b0"
git tag v0.2.1b0
git push origin v0.2.1b0
```

The workflow fails if the tag does not match the `version` in `pyproject.toml`. Other bump rules: `uvx hatch version patch|minor|major`, or an explicit version such as `uvx hatch version 0.3.0b1`. Use `uvx hatch version release` to drop a pre-release suffix.
