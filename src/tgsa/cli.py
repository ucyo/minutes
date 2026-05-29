from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .add import parse_line, run_add
from .display import render_logs
from .store import (
    append_entry,
    filter_entries,
    get_projects,
    load_entries,
    parse_since,
)

app = typer.Typer(
    help="tgsa — project-centric meeting notes and task tracker",
    no_args_is_help=True,
)
console = Console()


def _complete_project(incomplete: str) -> list[str]:
    try:
        return [p for p in get_projects() if incomplete.lower() in p.lower()]
    except Exception:
        return []


@app.command()
def add(
    text: Optional[str] = typer.Argument(None, help="Inline entry (skips interactive mode)"),
    project: Optional[str] = typer.Option(
        None, "--project", "-p",
        help="Project slug",
        autocompletion=_complete_project,
    ),
    file: Optional[Path] = typer.Option(None, "--file", help="Override store path"),
) -> None:
    """Add entries for a project interactively, or inline with --project."""
    if text is not None and project is not None:
        entry = parse_line(text)
        if entry is None:
            console.print("[red]Could not parse entry.[/red]")
            raise typer.Exit(1)
        entry.project = project
        append_entry(entry, file)
        console.print("[green]Saved.[/green]")
    else:
        if text is not None and project is None:
            console.print("[red]Inline mode requires --project.[/red]")
            raise typer.Exit(1)
        run_add(file)


@app.command()
def logs(
    project: Optional[str] = typer.Option(
        None, "--project", "-p",
        help="Scope to one project",
        autocompletion=_complete_project,
    ),
    since: Optional[str] = typer.Option(None, "--since", help="Restrict to entries since: 'mon', integer days back, or YYYY-MM-DD"),
    open_only: bool = typer.Option(False, "--open", help="Show only open actions and waiting entries"),
    show_all: bool = typer.Option(False, "--all", help="Show all fields: meeting, tags, done timestamp"),
    file: Optional[Path] = typer.Option(None, "--file"),
) -> None:
    """Show entries chronologically. All entries by default, restrict with --since."""
    since_date = parse_since(since) if since else None
    entries = load_entries(file)
    filtered = filter_entries(entries, since=since_date, project=project, open_only=open_only)
    render_logs(filtered, since_date, project=project, show_all=show_all)


def main() -> None:
    app()
