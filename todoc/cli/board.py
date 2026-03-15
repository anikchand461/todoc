"""
todoc · board.py
Kanban board renderer — todoc board
"""
from __future__ import annotations

from rich.console   import Console
from rich.table     import Table
from rich.text      import Text
from rich.panel     import Panel
from rich.rule      import Rule
from rich.padding   import Padding
from rich           import box
from typing         import Dict, List

from todoc.core.models import Task

console = Console()

DIM   = "grey50"
MUTED = "grey35"

_CHIPS = {
    "critical": ("bold white on bright_red",  " CRIT "),
    "high":     ("bold white on red",          " HIGH "),
    "medium":   ("bold black on yellow",       " MED  "),
    "low":      ("bold black on green",        " LOW  "),
}

def _chip(priority: str) -> Text:
    style, label = _CHIPS.get(priority.lower(), _CHIPS["medium"])
    return Text(label, style=style)


def _task_card(task: Task, width: int = 26) -> Table:
    """Render a single task as a mini card inside the board column."""
    card = Table(
        box            = box.ROUNDED,
        border_style   = "dim grey30" if task.done else ("red" if task.priority == "critical" else "grey35"),
        show_header    = False,
        expand         = True,
        padding        = (0, 1),
        width          = width,
    )
    card.add_column(ratio=1)

    # ID + priority chip
    header = Text()
    header.append(f"#{task.id} ", style="bold cyan" if not task.done else DIM)
    header.append_text(_chip(task.priority))

    # Description
    desc_style = f"strike {DIM}" if task.done else "bold white"
    desc       = Text(task.description[:32] + ("…" if len(task.description) > 32 else ""),
                      style=desc_style)

    # Tags (optional)
    rows = [header, desc]
    if task.tags:
        rows.append(Text(task.tags[:28], style="dim cyan"))

    # Subtask indicator
    if task.subtask_id_list:
        n = len(task.subtask_id_list)
        rows.append(Text(f"  ↳ {n} subtask(s)", style=DIM))

    for r in rows:
        card.add_row(r)

    return card


def _column_panel(title: str, icon: str, color: str,
                  tasks: List[Task], col_width: int) -> Table:
    """Render a full Kanban column as a nested table of cards."""
    outer = Table(
        box          = None,
        show_header  = False,
        expand       = False,
        padding      = (0, 0),
        width        = col_width,
    )
    outer.add_column(width=col_width)

    # Column header
    header = Text()
    header.append(f"  {icon}  ", style="")
    header.append(title.upper(), style=f"bold {color}")
    header.append(f"  ({len(tasks)})", style=DIM)
    outer.add_row(header)

    sep_style = f"bold {color}"
    outer.add_row(Text("─" * (col_width - 2), style=MUTED))

    if not tasks:
        empty = Text("  nothing here", style=DIM)
        outer.add_row(empty)
    else:
        for task in tasks:
            outer.add_row(_task_card(task, width=col_width - 2))
            outer.add_row(Text(""))   # spacing between cards

    return outer


def render_board(board: Dict[str, List[Task]], col_width: int = 30) -> None:
    """Render a 3-column Kanban board: To Do | Doing | Done."""
    console.print()
    console.print(Rule(title="[bold cyan]◈  K A N B A N  B O A R D[/bold cyan]", style="cyan"))
    console.print()

    todo_col  = _column_panel("To Do",       "○",  "red",    board.get("todo",  []), col_width)
    doing_col = _column_panel("In Progress", "◎",  "yellow", board.get("doing", []), col_width)
    done_col  = _column_panel("Done",        "✓",  "green",  board.get("done",  []), col_width)

    # Side-by-side layout
    layout = Table(
        box        = None,
        show_header= False,
        padding    = (0, 1),
        expand     = True,
    )
    layout.add_column(width=col_width, ratio=1)
    layout.add_column(width=col_width, ratio=1)
    layout.add_column(width=col_width, ratio=1)
    layout.add_row(todo_col, doing_col, done_col)

    console.print(Padding(layout, (0, 1)))

    # Footer counts
    todo_n  = len(board.get("todo",  []))
    doing_n = len(board.get("doing", []))
    done_n  = len(board.get("done",  []))
    total   = todo_n + doing_n + done_n

    footer_line = Text()
    footer_line.append("  ")
    footer_line.append(f"{todo_n}",  style="bold red")
    footer_line.append(" to do  ·  ", style=DIM)
    footer_line.append(f"{doing_n}", style="bold yellow")
    footer_line.append(" in progress  ·  ", style=DIM)
    footer_line.append(f"{done_n}",  style="bold green")
    footer_line.append(" done  ·  ", style=DIM)
    footer_line.append(f"{total} total", style="bold white")

    console.print()
    console.print(Padding(footer_line, (0, 0, 0, 1)))
    console.print()
    console.print(Rule(
        title=f"[{DIM}]use [bold]todoc status <id> doing[/bold] to move tasks · [bold]todoc board[/bold] to refresh[/{DIM}]",
        style=MUTED,
    ))
    console.print()
