"""todoc · main.py — CLI entry point."""
import typer
from rich.console import Console
from rich.text import Text
from typing import List, Optional

from todoc.core.service import TodoService
from todoc.exceptions import TaskNotFoundError, TodocError
from todoc.cli.formatter import (
    render_task_list, render_task_detail, render_search_results,
    render_stats_panel, render_help, render_summary,
    print_success, print_error, print_info, print_warning,
    panel_success, panel_error, panel_warning, panel_info,
)

console = Console()

# ─────────────────────────────────────────────────────────────
# Override --help at the app level to show our rich help page
# ─────────────────────────────────────────────────────────────

def _show_help(value: bool):
    if value:
        render_help()
        raise typer.Exit()

def _show_summary(value: bool):
    if value:
        render_summary()
        raise typer.Exit()

app = typer.Typer(
    name             = "todoc",
    add_completion   = False,
    rich_markup_mode = "rich",
    # suppress Typer's own help flag — we replace it below
    add_help_option  = False,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Root callback — bare `todoc` shows task list
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(invoke_without_command=True)
def main(
    ctx:     typer.Context,
    version: bool = typer.Option(False, "--version", "-v",       help="Show version and exit.",        is_eager=True),
    help_:   bool = typer.Option(False, "--help",    "-h",       help="Show the full command reference.", is_eager=True,
                                 callback=_show_help, expose_value=False),
    summary: bool = typer.Option(False, "--summary", "-s",       help="Show compact command list.",     is_eager=True,
                                 callback=_show_summary, expose_value=False),
):
    """todoc — terminal task manager."""
    if version:
        from todoc import __version__
        console.print(Text.assemble(
            Text("  todoc  ", style="bold black on cyan"),
            Text(f"  v{__version__}", style="bold cyan"),
        ))
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        svc   = TodoService()
        tasks = svc.get_tasks()
        render_task_list(tasks)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# help
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def help(
    summary: bool = typer.Option(False, "--summary", "-s", help="Compact command list only"),
):
    """Show the full command reference."""
    if summary:
        render_summary()
    else:
        render_help()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# add
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def add(
    description: str = typer.Argument(..., help="Task description"),
    priority: str = typer.Option(
        "medium", "--priority", "-p",
        help="critical · high · medium · low",
        case_sensitive=False,
    ),
    tags: str = typer.Option("", "--tags", help='Free-form info: "#bug due:fri @alice"'),
):
    """Add a new task."""
    _CHIP = {
        "critical": "[bold white on bright_red] CRIT [/]",
        "high":     "[bold white on red] HIGH [/]",
        "medium":   "[bold black on yellow] MED  [/]",
        "low":      "[bold black on green] LOW  [/]",
    }
    chip = _CHIP.get(priority.lower(), _CHIP["medium"])

    try:
        svc  = TodoService()
        task = svc.create_task(description, priority=priority, tags=tags)

        body = (
            f"[dim]id[/dim]          [bold cyan]{task.id}[/bold cyan]\n"
            f"[dim]task[/dim]        [bold white]{task.description}[/bold white]\n"
            f"[dim]priority[/dim]    {chip}"
        )
        if tags:
            body += f"\n[dim]tags[/dim]        [cyan]{tags}[/cyan]"

        panel_success("Task added", body)
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# list
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command(name="list")
def list_tasks(
    pending:   bool = typer.Option(False, "--pending",          help="Only pending tasks"),
    completed: bool = typer.Option(False, "--completed",        help="Only completed tasks"),
    priority:  str  = typer.Option("",   "--priority", "-p",   help="Filter by priority level"),
    by:        str  = typer.Option("id", "--by",               help="Sort: id · priority · created"),
    desc:      bool = typer.Option(False, "--desc",             help="Reverse sort order"),
):
    """List tasks — done tasks show with strikethrough."""
    try:
        svc   = TodoService()
        tasks = svc.sorted_tasks(by=by, reverse=desc)

        if pending:
            tasks = [t for t in tasks if not t.done]
        elif completed:
            tasks = [t for t in tasks if t.done]

        if priority:
            tasks = [t for t in tasks if t.priority.lower() == priority.lower()]

        render_task_list(tasks, sort_by=by)
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# show
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def show(task_id: int = typer.Argument(..., help="Task ID")):
    """Show full detail for a single task."""
    try:
        render_task_detail(TodoService().get_task(task_id))
    except TaskNotFoundError:
        panel_error("Not found",
            f"[bold]Task #{task_id}[/bold] doesn't exist.\n\n"
            "[dim]Run [bold]todoc list[/bold] to see valid IDs.[/dim]")
        raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# done  (bulk)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def done(task_ids: List[int] = typer.Argument(..., help="One or more task IDs")):
    """Mark task(s) as done.  todoc done 1 2 5"""
    try:
        svc       = TodoService()
        completed = svc.bulk_complete(task_ids)
        missing   = set(task_ids) - {t.id for t in completed}

        if completed:
            descs = "\n".join(
                f"[dim]  #{t.id}[/dim]  [strike grey50]{t.description}[/strike grey50]"
                for t in completed
            )
            label = "Task" if len(completed) == 1 else f"{len(completed)} tasks"
            panel_success(f"{label} completed  🎉",
                f"{descs}\n\n[dim]nice work — keep going![/dim]")
        for mid in missing:
            print_warning(f"Task #{mid} not found — skipped.")
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# undone
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def undone(task_id: int = typer.Argument(..., help="Task ID to reopen")):
    """Reopen a completed task."""
    try:
        task = TodoService().uncomplete_task(task_id)
        panel_warning("Task reopened",
            f"[dim]#{task.id}[/dim]  [bold white]{task.description}[/bold white]\n\n"
            "[dim]moved back to pending.[/dim]")
    except TaskNotFoundError:
        panel_error("Not found",
            f"[bold]Task #{task_id}[/bold] doesn't exist.\n\n"
            "[dim]Run [bold]todoc list[/bold] to see valid IDs.[/dim]")
        raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# edit
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def edit(
    task_id:     int           = typer.Argument(..., help="Task ID to edit"),
    description: Optional[str] = typer.Option(None, "--desc",     "-d", help="New description"),
    priority:    Optional[str] = typer.Option(None, "--priority",  "-p", help="New priority"),
    tags:        Optional[str] = typer.Option(None, "--tags",           help="New tags / info"),
):
    """Edit any field of a task. Only passed flags are changed."""
    try:
        task = TodoService().edit_task(task_id,
            description=description, priority=priority, tags=tags)
        render_task_detail(task)
        print_success(f"Task #{task_id} updated.")
    except TaskNotFoundError:
        panel_error("Not found",
            f"[bold]Task #{task_id}[/bold] doesn't exist.\n\n"
            "[dim]Run [bold]todoc list[/bold] to see valid IDs.[/dim]")
        raise typer.Exit(code=1)
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# delete
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def delete(
    task_id: int  = typer.Argument(..., help="Task ID to delete"),
    force:   bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a task permanently."""
    try:
        svc    = TodoService()
        target = next((t for t in svc.get_tasks() if t.id == task_id), None)

        if not target:
            raise TaskNotFoundError(f"Task #{task_id} not found.")

        if not force:
            console.print(
                f"\n  [grey50]#{task_id}[/grey50]  [bold white]{target.description}[/bold white]\n")
            if not typer.confirm("  Delete this task?"):
                print_info("Cancelled — nothing changed.")
                raise typer.Exit()

        svc.remove_task(task_id)
        panel_warning("Task deleted",
            f"[dim]#{task_id}[/dim]  [strike]{target.description}[/strike]\n\n"
            "[dim]gone for good.[/dim]")
    except TaskNotFoundError:
        panel_error("Not found",
            f"[bold]Task #{task_id}[/bold] doesn't exist.\n\n"
            "[dim]Run [bold]todoc list[/bold] to see valid IDs.[/dim]")
        raise typer.Exit(code=1)
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# search
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def search(query: str = typer.Argument(..., help="Search term")):
    """Search tasks across description and tags."""
    try:
        render_search_results(TodoService().search(query), query)
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# sort
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def sort(
    by:   str  = typer.Option("priority", "--by",   help="id · priority · created"),
    desc: bool = typer.Option(False,      "--desc",  help="Reverse the order"),
):
    """Display tasks sorted by a field."""
    try:
        tasks = TodoService().sorted_tasks(by=by, reverse=desc)
        render_task_list(tasks, sort_by=by, title=f"◈  Sorted by {by}")
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# stats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def stats():
    """Completion statistics with priority breakdown."""
    try:
        from collections import Counter
        svc       = TodoService()
        tasks     = svc.get_tasks()
        total     = len(tasks)
        completed = sum(1 for t in tasks if t.done)
        pending   = total - completed
        rate      = (completed / total * 100) if total else 0.0
        by_pri    = dict(Counter(t.priority for t in tasks))

        render_stats_panel(total, completed, pending, rate, by_priority=by_pri)
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# clear
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def clear():
    """Remove all completed tasks."""
    try:
        svc       = TodoService()
        done_list = [t for t in svc.get_tasks() if t.done]

        if not done_list:
            panel_info("Nothing to clear", "[dim]No completed tasks found.[/dim]")
            raise typer.Exit()

        n = len(done_list)
        console.print(f"\n  [grey50]{n} completed task(s) will be removed.[/grey50]\n")
        if typer.confirm("  Proceed?"):
            panel_success("Cleared",
                f"[bold green]{svc.remove_all_done()}[/bold green] completed task(s) removed.\n\n"
                "[dim]your list is clean.[/dim]")
        else:
            print_info("Cancelled — nothing changed.")
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# reset
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def reset(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation — delete everything immediately"),
):
    """Wipe ALL tasks — complete reset. Cannot be undone."""
    try:
        svc   = TodoService()
        tasks = svc.get_tasks()
        total = len(tasks)

        if total == 0:
            panel_info("Already empty", "[dim]No tasks to delete.[/dim]")
            raise typer.Exit()

        if not force:
            console.print()
            console.print(f"  [bold red]⚠  This will permanently delete all {total} task(s).[/bold red]")
            console.print(f"  [dim]This cannot be undone. Use [bold]todoc export[/bold] first to make a backup.[/dim]\n")
            if not typer.confirm("  Delete everything?"):
                print_info("Cancelled — nothing changed.")
                raise typer.Exit()

        removed = svc.remove_all_tasks()
        panel_warning(
            "Reset complete",
            f"[bold red]{removed}[/bold red] task(s) deleted.\n\n"
            "[dim]todoc is now empty.[/dim]",
        )
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# export
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def export(
    fmt:    str = typer.Option("json", "--format", help="json or csv"),
    output: str = typer.Option("",    "--output", "-o", help="File path (default: stdout)"),
):
    """Export all tasks to JSON or CSV."""
    try:
        svc  = TodoService()
        data = svc.export_csv() if fmt.lower() == "csv" else svc.export_json()
        if output:
            with open(output, "w") as f:
                f.write(data)
            panel_success("Exported",
                f"[bold white]{len(svc.get_tasks())}[/bold white] task(s) → "
                f"[bold cyan]{output}[/bold cyan] [dim]({fmt})[/dim]")
        else:
            console.print(data)
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# import
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command(name="import")
def import_tasks(
    filepath: str = typer.Argument(..., help="Path to JSON file from todoc export"),
):
    """Import tasks from a JSON file."""
    try:
        with open(filepath) as f:
            data = f.read()
        count = TodoService().import_json(data)
        panel_success("Imported",
            f"[bold white]{count}[/bold white] task(s) imported from "
            f"[bold cyan]{filepath}[/bold cyan].")
    except FileNotFoundError:
        panel_error("File not found", f"[bold]{filepath}[/bold] does not exist.")
        raise typer.Exit(code=1)
    except Exception as e:
        print_error(f"Import failed: {e}"); raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
