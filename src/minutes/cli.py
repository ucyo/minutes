from __future__ import annotations

from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .add import parse_line
from .browse import run_logs_interactive
from .store import (
    DEFAULT_PATH,
    append_entry,
    filter_entries,
    get_projects,
    load_entries,
    parse_since,
)

app = typer.Typer(
    help="minutes — project-centric meeting notes and task tracker",
    no_args_is_help=True,
)
console = Console()


def _complete_project(incomplete: str) -> list[str]:
    try:
        return [p for p in get_projects() if incomplete.lower() in p.lower()]
    except Exception:
        return []


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
    add_text: Optional[str] = typer.Option(
        None, "--add",
        help="Add an entry inline (requires --project) and exit",
    ),
    file: Optional[Path] = typer.Option(None, "--file"),
    web: bool = typer.Option(False, "--web", help="Serve entries in a local web UI instead of the TUI"),
    port: int = typer.Option(8123, "--port", help="Port for the web UI (only with --web)"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the browser when --web starts"),
) -> None:
    """Browse entries interactively, or add an entry inline with --web."""
    if web:
        from .web.server import run as run_web

        initial: dict[str, str] = {}
        if project:
            initial["project"] = project
        if since:
            initial["since"] = since
        if open_only:
            initial["open"] = "1"
        if show_all:
            initial["all"] = "1"
        try:
            run_web(store=file, port=port, open_browser=not no_open, initial=initial)
        except OSError as exc:
            console.print(f"[red]Could not start web server: {exc}[/red]")
            raise typer.Exit(1)
        return

    if add_text is not None:
        if project is None:
            console.print("[red]Inline add requires --project.[/red]")
            raise typer.Exit(1)
        entry = parse_line(add_text)
        if entry is None:
            console.print("[red]Could not parse entry.[/red]")
            raise typer.Exit(1)
        entry.project = project
        append_entry(entry, file)
        console.print("[green]Saved.[/green]")
        return

    since_date = parse_since(since) if since else None
    entries = load_entries(file)
    filtered = filter_entries(entries, since=since_date, project=project, open_only=open_only)
    run_logs_interactive(filtered, file, since=since_date, project=project, show_all=show_all)


@app.command()
def info(
    file: Optional[Path] = typer.Option(None, "--file"),
) -> None:
    """Show store location and entry count."""
    path = file or DEFAULT_PATH
    console.print(f"[dim]version[/dim]  {pkg_version('minutes-cli')}")
    if path.exists():
        count = len(load_entries(file))
        console.print(f"[dim]store  [/dim]  {path}")
        console.print(f"[dim]entries[/dim]  {count}")
    else:
        console.print(f"[dim]store  [/dim]  {path}")
        console.print(f"[dim]entries[/dim]  [dim]store not initialised yet[/dim]")


def main() -> None:
    app()
