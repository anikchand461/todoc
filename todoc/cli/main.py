"""todoc · main.py — CLI entry point."""
import typer
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich.live import Live
from rich.align import Align
from rich import box
from typing import List, Optional
import time

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
# Animated header shown on --help / todoc help
# ─────────────────────────────────────────────────────────────

def _render_help_header() -> None:
    """Animated branded header: logo reveal → typewriter → panel fade → shimmer rule."""
    from todoc import __version__

    # ── 1. Big ASCII logo — left-to-right block reveal ────────
    LOGO = [
        "  ████████╗ ██████╗ ██████╗  ██████╗  ██████╗ ",
        "     ██╔══╝██╔═══██╗██╔══██╗██╔═══██╗██╔════╝ ",
        "     ██║   ██║   ██║██║  ██║██║   ██║██║      ",
        "     ██║   ██║   ██║██║  ██║██║   ██║██║      ",
        "     ██║   ╚██████╔╝██████╔╝╚██████╔╝╚██████╗ ",
        "     ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝ ",
    ]
    COLORS = ["#00e5ff", "#00cfeb", "#00b9d6", "#00a3c2", "#008dae", "#00779a"]
    DIM    = "#1c2333"
    width  = max(len(l) for l in LOGO)

    console.print()
    with Live(console=console, refresh_per_second=40, transient=False) as live:
        for step in range(width + 1):
            frame = Text()
            for row, line in enumerate(LOGO):
                shown = line[:step].ljust(step)
                hidden = line[step:]
                frame.append(shown,  style=f"bold {COLORS[row]}")
                frame.append(hidden, style=f"{DIM} on default")
                frame.append("\n")
            live.update(frame)
            time.sleep(0.010)

    # ── 2. Version badge ── appears right after logo ───────────
    console.print()
    badge = Text.assemble(
        Text("  todoc  ", style="bold black on cyan"),
        Text(f"  v{__version__}  ", style="bold cyan"),
    )
    # Slide-in badge character by character
    raw = f"  todoc    v{__version__}  "
    with Live(console=console, refresh_per_second=40, transient=False) as live:
        for i in range(1, len(raw) + 1):
            live.update(Text(raw[:i], style="bold cyan"))
            time.sleep(0.022)
    # Overwrite with properly styled version
    console.file.write("\r")
    console.print(badge)
    console.print()

    # ── 3. Tagline — typewriter char by char ──────────────────
    lines = [
        ("  A beautiful, fast terminal task manager", "bold white"),
        ("  Stay organised without ever leaving your shell.", "dim"),
    ]
    for text, style in lines:
        with Live(console=console, refresh_per_second=40, transient=False) as live:
            built = Text()
            for ch in text:
                built.append(ch, style=style)
                live.update(built)
                time.sleep(0.016)
        console.print()
    console.print()

    # ── 4. Link panels — fade in one by one ───────────────────
    def _panel(label, display, url, lit=True):
        t = Text.assemble(
            Text(label + "\n", style="dim"),
            Text(display, style="bold cyan" if lit else "grey42"),
        )
        if lit:
            t.stylize(f"link {url}", len(label) + 1, len(label) + 1 + len(display))
        return Panel(
            t,
            border_style="cyan" if lit else "grey23",
            padding=(0, 2),
            box=box.ROUNDED,
        )

    LINKS = [
        ("website", "todocpy.vercel.app",           "https://todocpy.vercel.app"),
        ("pypi",    "pypi.org/project/todoc",        "https://pypi.org/project/todoc/"),
        ("github",  "github.com/anikchand461/todoc", "https://github.com/anikchand461/todoc"),
    ]

    with Live(console=console, refresh_per_second=20, transient=False) as live:
        for reveal in range(len(LINKS) + 1):
            panels = [
                _panel(lbl, disp, url, lit=(i < reveal))
                for i, (lbl, disp, url) in enumerate(LINKS)
            ]
            live.update(Columns(panels, padding=(0, 1)))
            time.sleep(0.22)

    console.print()

    # ── 5. Author — shimmer sweep ──────────────────────────────
    SHIMMER_STYLES = [
        "dim", "grey70", "white", "bold white",
        "bold cyan", "bold white", "white", "grey70", "dim",
    ]
    with Live(console=console, refresh_per_second=15, transient=False) as live:
        for style in SHIMMER_STYLES:
            live.update(Text.assemble(
                Text("  author  ", style="dim"),
                Text("Anik Chand", style=style),
            ))
            time.sleep(0.08)
    console.print()

    # ── 6. Animated cyan rule sweeps across ───────────────────
    term_width = console.width or 80
    with Live(console=console, refresh_per_second=60, transient=False) as live:
        for i in range(term_width + 1):
            live.update(Text("─" * i, style="dim cyan"))
            time.sleep(0.003)
    console.print()

def _show_help(value: bool):
    if value:
        _render_help_header()
        render_summary()          # compact command list (was render_help)
        raise typer.Exit()


def _show_summary(value: bool):
    if value:
        render_summary()
        raise typer.Exit()


app = typer.Typer(
    name             = "todoc",
    add_completion   = False,
    rich_markup_mode = "rich",
    add_help_option  = False,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Root callback
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(invoke_without_command=True)
def main(
    ctx:     typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit.", is_eager=True),
    help_:   bool = typer.Option(False, "--help",    "-h", help="Show the command reference.", is_eager=True,
                                 callback=_show_help, expose_value=False),
    summary: bool = typer.Option(False, "--summary", "-s", help="Show compact command list.", is_eager=True,
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
        try:
            notified = svc.notify_check()
            if notified:
                print_warning(
                    f"{len(notified)} overdue task(s) — desktop notification sent."
                )
        except Exception:
            pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# help
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def help(
    summary: bool = typer.Option(False, "--summary", "-s", help="Compact command list only"),
    full:    bool = typer.Option(False, "--full",    "-f", help="Show full verbose reference"),
):
    """Show the command reference with links and usage examples."""
    if full:
        _render_help_header()
        render_help()          # detailed reference (accessible via todoc help --full)
    elif summary:
        render_summary()       # bare compact list, no header
    else:
        _render_help_header()
        render_summary()       # default: header + compact list


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# tui
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def tui():
    """Launch the interactive TUI dashboard.

    [bold]Keyboard shortcuts inside the TUI:[/bold]
      [bold cyan]a[/bold cyan]          Add a new task
      [bold cyan]e[/bold cyan]          Edit selected task
      [bold cyan]Space[/bold cyan]      Toggle done / pending
      [bold cyan]n[/bold cyan]          Cycle status: todo → doing → done
      [bold cyan]d[/bold cyan]          Delete selected task
      [bold cyan]/[/bold cyan]          Focus search bar (fuzzy search)
      [bold cyan]r[/bold cyan]          Refresh list
      [bold cyan]q[/bold cyan]          Quit
    """
    try:
        from todoc.cli.tui import launch_tui
        launch_tui()
    except ImportError:
        panel_error(
            "Textual not installed",
            "The TUI requires the [bold]textual[/bold] package.\n\n"
            "Install it with:\n"
            "  [bold cyan]pip install textual[/bold cyan]",
        )
        raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# board
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def board():
    """Show a Kanban board: To Do | In Progress | Done.

    Move tasks between columns with [bold]todoc status <id> <todo|doing|done>[/bold].

    [bold]Examples[/bold]
      todoc board
      todoc status 3 doing
      todoc status 3 done
    """
    try:
        from todoc.cli.board import render_board
        svc = TodoService()
        render_board(svc.get_kanban_board())
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# status
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def status(
    task_id:    int = typer.Argument(..., help="Task ID"),
    new_status: str = typer.Argument(..., help="todo | doing | done"),
):
    """Move a task to a Kanban column.

    [bold]Examples[/bold]
      todoc status 3 doing    ← start working on it
      todoc status 3 done     ← mark complete
      todoc status 3 todo     ← move back to backlog
    """
    try:
        task = TodoService().set_status(task_id, new_status.lower())
        _ICONS = {"todo": "○", "doing": "◎", "done": "✓"}
        icon   = _ICONS.get(task.status, "○")
        panel_success(
            f"{icon} Status updated",
            f"[dim]#{task.id}[/dim]  [bold white]{task.description}[/bold white]\n\n"
            f"[dim]status[/dim]  →  [bold cyan]{task.status}[/bold cyan]",
        )
    except ValueError as e:
        print_error(str(e)); raise typer.Exit(code=1)
    except TaskNotFoundError:
        panel_error("Not found",
            f"[bold]Task #{task_id}[/bold] doesn't exist.\n\n"
            "[dim]Run [bold]todoc list[/bold] to see valid IDs.[/dim]")
        raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# subtask
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def subtask(
    parent_id:   int = typer.Argument(..., help="Parent task ID"),
    description: str = typer.Argument(..., help="Subtask description"),
    priority:    str = typer.Option("medium", "--priority", "-p", help="Priority level"),
):
    """Add a subtask under an existing task.

    Subtasks appear indented under their parent in [bold]todoc show <id>[/bold].

    [bold]Examples[/bold]
      todoc subtask 1 "Write unit tests"
      todoc subtask 1 "Update docs" -p low
    """
    try:
        svc  = TodoService()
        task = svc.add_subtask(parent_id, description, priority=priority)
        panel_success(
            "Subtask added",
            f"[dim]parent[/dim]   [bold cyan]#{parent_id}[/bold cyan]\n"
            f"[dim]subtask[/dim]  [bold cyan]#{task.id}[/bold cyan]  "
            f"[bold white]{task.description}[/bold white]",
        )
    except TaskNotFoundError:
        panel_error("Not found",
            f"[bold]Task #{parent_id}[/bold] doesn't exist.\n\n"
            "[dim]Run [bold]todoc list[/bold] to see valid IDs.[/dim]")
        raise typer.Exit(code=1)
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# notify
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def notify():
    """Send a desktop notification for urgent pending tasks.

    Fires a native system notification listing all HIGH and CRITICAL
    tasks that are not yet done.

    Supported platforms: macOS, Linux (notify-send), Windows (plyer).

    [bold]Examples[/bold]
      todoc notify
      # Add to crontab for auto alerts:
      # */30 * * * * todoc notify
    """
    try:
        svc   = TodoService()
        tasks = svc.notify_check()
        if not tasks:
            panel_info("All clear", "[dim]No urgent pending tasks — nothing to notify.[/dim]")
        else:
            descs = "\n".join(
                f"[dim]  [{t.priority.upper()}][/dim]  [bold white]{t.description}[/bold white]"
                for t in tasks
            )
            panel_warning(
                f"Notified — {len(tasks)} urgent task(s)",
                f"{descs}\n\n[dim]Desktop notification sent.[/dim]",
            )
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


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
        if priority.lower() == "critical":
            svc.notify_check()
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
    pending:   bool = typer.Option(False, "--pending",            help="Only pending tasks"),
    completed: bool = typer.Option(False, "--completed",          help="Only completed tasks"),
    priority:  str  = typer.Option("",   "--priority", "-p",     help="Filter by priority level"),
    by:        str  = typer.Option("id", "--by",                  help="Sort: id · priority · created"),
    desc:      bool = typer.Option(False, "--desc",               help="Reverse sort order"),
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
        try:
            notified = svc.notify_check()
            if notified:
                print_warning(
                    f"{len(notified)} overdue task(s) — desktop notification sent."
                )
        except Exception:
            pass
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# show
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def show(task_id: int = typer.Argument(..., help="Task ID")):
    """Show full detail for a task (including subtasks)."""
    try:
        svc  = TodoService()
        task = svc.get_task(task_id)
        render_task_detail(task)
        subtasks = svc.get_subtasks(task_id)
        if subtasks:
            console.print(f"  [dim]subtasks ({len(subtasks)}):[/dim]")
            for st in subtasks:
                done_style = "strike dim" if st.done else "white"
                console.print(
                    f"    [dim]#{st.id}[/dim]  "
                    f"[{done_style}]{st.description}[/{done_style}]  "
                    f"[dim]{st.priority}[/dim]"
                )
            console.print()
    except TaskNotFoundError:
        panel_error("Not found",
            f"[bold]Task #{task_id}[/bold] doesn't exist.\n\n"
            "[dim]Run [bold]todoc list[/bold] to see valid IDs.[/dim]")
        raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# done
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
            f"[bold]Task #{task_id}[/bold] doesn't exist.")
        raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# edit
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def edit(
    task_id:     int           = typer.Argument(..., help="Task ID to edit"),
    description: Optional[str] = typer.Option(None, "--desc",    "-d", help="New description"),
    priority:    Optional[str] = typer.Option(None, "--priority", "-p", help="New priority"),
    tags:        Optional[str] = typer.Option(None, "--tags",          help="New tags / info"),
    st:          Optional[str] = typer.Option(None, "--status",        help="New status: todo|doing|done"),
):
    """Edit any field of a task. Only passed flags are changed."""
    try:
        task = TodoService().edit_task(task_id,
            description=description, priority=priority, tags=tags, status=st)
        render_task_detail(task)
        print_success(f"Task #{task_id} updated.")
    except TaskNotFoundError:
        panel_error("Not found",
            f"[bold]Task #{task_id}[/bold] doesn't exist.")
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
    """Delete a task permanently (also removes its subtasks)."""
    try:
        svc    = TodoService()
        target = next((t for t in svc.get_tasks() if t.id == task_id), None)
        if not target:
            raise TaskNotFoundError(f"Task #{task_id} not found.")
        subtasks = svc.get_subtasks(task_id)
        if not force:
            console.print(
                f"\n  [grey50]#{task_id}[/grey50]  [bold white]{target.description}[/bold white]"
                + (f"  [dim]({len(subtasks)} subtask(s) will also be deleted)[/dim]" if subtasks else "")
                + "\n"
            )
            if not typer.confirm("  Delete this task?"):
                print_info("Cancelled — nothing changed.")
                raise typer.Exit()
        svc.remove_task(task_id)
        panel_warning("Task deleted",
            f"[dim]#{task_id}[/dim]  [strike]{target.description}[/strike]\n\n"
            "[dim]gone for good.[/dim]")
    except TaskNotFoundError:
        panel_error("Not found",
            f"[bold]Task #{task_id}[/bold] doesn't exist.")
        raise typer.Exit(code=1)
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# search
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def search(
    query: str  = typer.Argument(..., help="Search term"),
    fuzzy: bool = typer.Option(False, "--fuzzy", "-f",
                               help="Fuzzy match — typos OK (e.g. 'lgin' finds 'login')"),
):
    """Search tasks.  Use --fuzzy for typo-tolerant matching.

    [bold]Examples[/bold]
      todoc search "auth"
      todoc search "lgin" --fuzzy      ← finds "Fix login bug"
      todoc search "#bug"
    """
    try:
        results = TodoService().search(query, fuzzy=fuzzy)
        render_search_results(results, query)
        if fuzzy and results:
            print_info("Fuzzy search — results ranked by match quality.")
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
        render_stats_panel(total, completed, pending, rate,
                           by_priority=by_pri, tasks=tasks)
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
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Wipe ALL tasks — complete reset. Cannot be undone."""
    try:
        svc   = TodoService()
        total = len(svc.get_tasks())
        if total == 0:
            panel_info("Already empty", "[dim]No tasks to delete.[/dim]")
            raise typer.Exit()
        if not force:
            console.print()
            console.print(f"  [bold red]⚠  This will permanently delete all {total} task(s).[/bold red]")
            console.print(f"  [dim]Run [bold]todoc export[/bold] first to make a backup.[/dim]\n")
            if not typer.confirm("  Delete everything?"):
                print_info("Cancelled — nothing changed.")
                raise typer.Exit()
        removed = svc.remove_all_tasks()
        panel_warning("Reset complete",
            f"[bold red]{removed}[/bold red] task(s) deleted.\n\n[dim]todoc is now empty.[/dim]")
    except TodocError as e:
        print_error(str(e)); raise typer.Exit(code=1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# daemon
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command()
def daemon(
    action: str = typer.Argument(
        "status",
        help="start · stop · status · run",
    ),
):
    """Manage the background notification daemon.

    Automatically sends desktop notifications at [bold]4h, 6h, 9h, 12h, 18h, 24h[/bold]
    for every pending task — no terminal needed.

    [bold]Platform support:[/bold]
      macOS    →  launchd
      Linux    →  systemd user timer  (cron fallback)
      Windows  →  Task Scheduler

    [bold]Examples[/bold]
      todoc daemon start     ← install & start
      todoc daemon stop      ← uninstall the daemon
      todoc daemon status    ← check if it\'s running
    """
    try:
        from todoc.cli.daemon import start, stop, status, run_check
        acts = {
            "start":  start,
            "stop":   stop,
            "status": status,
            "run":    run_check,
        }
        fn = acts.get(action.lower())
        if not fn:
            print_error(f"Unknown action \"{action}\" — use start · stop · status")
            raise typer.Exit(code=1)
        fn()
    except Exception as e:
        print_error(f"Daemon error: {e}")
        raise typer.Exit(code=1)


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
