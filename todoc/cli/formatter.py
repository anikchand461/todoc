"""todoc · formatter.py — all Rich display logic."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.align import Align
from rich.padding import Padding
from rich import box
from rich.box import ROUNDED, DOUBLE
from typing import List

console = Console()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Design tokens
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DIM   = "grey50"
MUTED = "grey35"

_CHIPS: dict[str, tuple[str, str]] = {
    "critical": ("bold white on bright_red",   " CRIT "),
    "high":     ("bold white on red",           " HIGH "),
    "medium":   ("bold black on yellow",        " MED  "),
    "low":      ("bold black on green",         " LOW  "),
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Primitives
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _badge(label: str, bg: str, fg: str = "black") -> Text:
    return Text(f" {label} ", style=f"bold {fg} on {bg}")

def _rule(title: str = "", style: str = MUTED) -> None:
    console.print(Rule(title=title, style=style))

def _spacer() -> None:
    console.print()

def _priority_chip(priority: str) -> Text:
    style, label = _CHIPS.get(priority.lower(), _CHIPS["medium"])
    return Text(label, style=style)

def _progress_bar(pct: int, width: int = 28) -> Text:
    filled = max(0, min(width, int(pct / 100 * width)))
    bar    = Text()
    bar.append("█" * filled,            style="bold green")
    bar.append("░" * (width - filled),  style=f"dim {MUTED}")
    return bar

def _tags_cell(tags: str) -> Text:
    if not tags:
        return Text("—", style=MUTED)
    return Text(tags, style="cyan")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Notification badges
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def print_success(message: str) -> None:
    console.print(Padding(Text.assemble(
        _badge("✓ OK",   "green"),        Text(f"  {message}", style="bold green")),  (0,0,0,1)))

def print_error(message: str) -> None:
    console.print(Padding(Text.assemble(
        _badge("✗ ERR",  "red", "white"), Text(f"  {message}", style="bold red")),    (0,0,0,1)))

def print_info(message: str) -> None:
    console.print(Padding(Text.assemble(
        _badge("· INFO", "cyan"),         Text(f"  {message}", style="cyan")),         (0,0,0,1)))

def print_warning(message: str) -> None:
    console.print(Padding(Text.assemble(
        _badge("⚠ WARN", "yellow"),       Text(f"  {message}", style="bold yellow")), (0,0,0,1)))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Feedback panels
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _panel(title: str, body: str, border: str) -> None:
    _spacer()
    console.print(Panel(Text.from_markup(body),
        title=f"[bold {border}]{title}[/bold {border}]",
        border_style=border, box=ROUNDED, padding=(1, 3)))
    _spacer()

def panel_success(title: str, body: str) -> None: _panel(title, body, "green")
def panel_error  (title: str, body: str) -> None: _panel(title, body, "red")
def panel_warning(title: str, body: str) -> None: _panel(title, body, "yellow")
def panel_info   (title: str, body: str) -> None: _panel(title, body, "cyan")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stats strip
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _render_stats(total: int, completed: int, pending: int) -> None:
    pct  = int(completed / total * 100) if total else 0
    line = Text()
    line.append("  ")
    line.append(f"{completed}", style="bold green")
    line.append(f"/{total}",   style=DIM)
    line.append("  done  ·  ", style=DIM)
    line.append(f"{pending}",  style="bold yellow")
    line.append("  pending  · ", style=DIM)
    line.append(f"{pct}%  ",   style="bold cyan")
    line.append(_progress_bar(pct))
    console.print(Padding(line, (0, 0, 0, 1)))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task table
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_table(tasks: List, highlight_ids: List[int] | None = None) -> Table:
    tbl = Table(
        show_header  = True,
        header_style = "bold white on grey19",
        box          = box.SIMPLE_HEAD,
        border_style = MUTED,
        show_lines   = True,
        expand       = False,
        padding      = (0, 1),
    )
    tbl.add_column(" # ",      justify="right",  style="bold cyan", width=5)
    tbl.add_column("Priority", justify="center",                    width=9)
    tbl.add_column(" ",        justify="center",                    width=3)
    tbl.add_column("Task",     justify="left",   style="white",     ratio=1, min_width=24)
    tbl.add_column("Tags",     justify="left",                      ratio=1, min_width=18)

    for task in tasks:
        hi   = highlight_ids and task.id in highlight_ids
        chip = _priority_chip(getattr(task, "priority", "medium"))

        if task.done:
            id_cell = Text(str(task.id),     style=DIM)
            status  = Text("✓",              style="bold green", justify="center")
            desc    = Text(task.description, style=f"strike {DIM}")
            tags    = Text(task.tags,        style=f"strike {DIM}") if task.tags else Text("—", style=MUTED)
        else:
            id_cell = Text(str(task.id),     style="bold bright_cyan underline" if hi else "bold cyan")
            status  = Text("○",              style="bold red",   justify="center")
            desc    = Text(task.description, style="bold white")
            tags    = _tags_cell(task.tags)

        tbl.add_row(id_cell, chip, status, desc, tags)

    return tbl

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Empty state
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _render_empty() -> None:
    body = Text(justify="center")
    body.append("\n  nothing here yet\n\n",       style=f"bold {DIM}")
    body.append("  kick things off:\n",           style="dim white")
    body.append('  todoc add "your task"',        style="bold white")
    body.append(" [-p high] [--tags \"info\"]\n", style="dim cyan")
    _spacer()
    console.print(Panel(Align.center(body),
        title="[bold cyan]◈  T O D O C[/bold cyan]",
        subtitle=f"[{DIM}]0 tasks[/{DIM}]",
        border_style="cyan", box=DOUBLE, padding=(1, 6)))
    _spacer()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main task list
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_task_list(tasks: List, sort_by: str = "id",
                     title: str = "◈  T O D O C") -> None:
    if not tasks:
        _render_empty()
        return

    total     = len(tasks)
    completed = sum(1 for t in tasks if t.done)
    pending   = total - completed

    _spacer()
    _rule(title=f"[bold cyan]{title}[/bold cyan]", style="cyan")
    _spacer()
    console.print(Padding(_build_table(tasks), (0, 1)))
    _spacer()
    _render_stats(total, completed, pending)
    _spacer()
    _rule(title=f"[{DIM}]{pending} pending · {completed} done · {total} total · sorted by {sort_by}[/{DIM}]",
          style=MUTED)
    _spacer()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Single task detail
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_task_detail(task) -> None:
    def row(label: str, value) -> Text:
        t = Text()
        t.append(f"  {label:<12}", style=DIM)
        if isinstance(value, Text): t.append_text(value)
        else: t.append(str(value) if value else "—", style="white" if value else DIM)
        return t

    status = Text("✓ done",    style="bold green") if task.done \
        else Text("○ pending", style="bold red")

    lines = [
        Text(""),
        row("id",          Text(str(task.id),      style="bold cyan")),
        row("status",      status),
        row("priority",    _priority_chip(getattr(task, "priority", "medium"))),
        row("tags",        Text(task.tags, style="cyan") if task.tags else Text("—", style=DIM)),
        row("created",     getattr(task, "created_at", "")),
        Text(""),
        row("description", Text(task.description,  style="bold white")),
        Text(""),
    ]

    _spacer()
    console.print(Panel(Text("\n").join(lines),
        title=f"[bold cyan]◈  Task #{task.id}[/bold cyan]",
        border_style="cyan", box=ROUNDED, padding=(0, 2)))
    _spacer()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Search results
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_search_results(tasks: List, query: str) -> None:
    if not tasks:
        panel_info("No results",
            f"Nothing matched [bold]\"{query}\"[/bold].\n\n"
            "[dim]Search checks description and tags.[/dim]")
        return
    _spacer()
    _rule(title=(
        f"[bold cyan]◈  Search ·[/bold cyan] [dim]\"{query}\"[/dim]"
        f"[bold cyan] · {len(tasks)} result(s)[/bold cyan]"
    ), style="cyan")
    _spacer()
    console.print(Padding(_build_table(tasks, highlight_ids=[t.id for t in tasks]), (0, 1)))
    _spacer()
    _rule(title=f"[{DIM}]{len(tasks)} match(es) for \"{query}\"[/{DIM}]", style=MUTED)
    _spacer()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stats panel
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_stats_panel(
    total:       int,
    completed:   int,
    pending:     int,
    rate:        float,
    by_priority: dict | None = None,
    tasks:       list | None = None,   # full task list for deeper breakdowns
) -> None:
    """Redesigned stats — full dashboard layout."""
    from rich.columns import Columns
    from rich.table   import Table as RTable
    import math

    pct     = int(rate)
    bar_w   = 36
    filled  = int(pct / 100 * bar_w)
    bar     = Text()
    bar.append("█" * filled,            style="bold green")
    bar.append("░" * (bar_w - filled),  style=f"dim {MUTED}")

    _spacer()
    _rule(title="[bold cyan]◈  S T A T I S T I C S[/bold cyan]", style="cyan")
    _spacer()

    # ── Row 1: 4 big metric cards ─────────────────────────────
    def _metric_card(value: str, label: str, color: str, sub: str = "") -> Panel:
        body = Text(justify="center")
        body.append(f"\n  {value}  \n", style=f"bold {color}")
        body.append(f"  {label}  \n",   style=f"bold {DIM}")
        if sub:
            body.append(f"  {sub}  \n", style=f"dim {MUTED}")
        else:
            body.append("\n")
        return Panel(Align.center(body),
                     border_style=color, box=ROUNDED, padding=(0, 2))

    streak = 0
    if tasks:
        # count consecutive done tasks from the end (completion streak)
        for t in reversed(sorted(tasks, key=lambda x: x.created_at or "")):
            if t.done: streak += 1
            else:      break

    cards = [
        _metric_card(str(total),     "Total Tasks",  "cyan",   "all time"),
        _metric_card(str(completed), "Completed",    "green",  f"streak: {streak}"),
        _metric_card(str(pending),   "Pending",      "yellow", "to do"),
        _metric_card(f"{pct}%",      "Done Rate",    "cyan" if pct >= 50 else "yellow", "completion"),
    ]
    console.print(Padding(Columns(cards, equal=True, expand=True), (0, 1)))
    _spacer()

    # ── Row 2: Progress bar (full width) ─────────────────────
    prog_body = Text()
    prog_body.append("\n  Progress  ", style=f"bold {DIM}")
    prog_body.append_text(bar)
    prog_body.append(f"  {pct}%", style="bold cyan")
    if pct == 100:
        prog_body.append("  🎉 All done!", style="bold green")
    prog_body.append("\n")
    console.print(Padding(Panel(prog_body,
        border_style="grey35", box=box.SIMPLE, padding=(0, 1)), (0, 1)))

    # ── Row 3: Priority breakdown + Status breakdown side by side
    left_tbl = RTable(
        title       = "[bold white]By Priority[/bold white]",
        box         = box.SIMPLE_HEAD,
        border_style= MUTED,
        show_lines  = True,
        padding     = (0, 2),
        expand      = True,
    )
    left_tbl.add_column("Priority",  justify="left",   width=10)
    left_tbl.add_column("Count",     justify="right",  style="bold white", width=7)
    left_tbl.add_column("Bar",       justify="left",   ratio=1)
    left_tbl.add_column("%",         justify="right",  style="dim cyan",   width=6)

    for lvl in ("critical", "high", "medium", "low"):
        count = (by_priority or {}).get(lvl, 0)
        if count == 0:
            continue
        frac    = count / total if total else 0
        bar_len = max(1, int(frac * 20))
        col     = {"critical": "bright_red", "high": "red",
                   "medium": "yellow", "low": "green"}.get(lvl, "white")
        mini_bar = Text("█" * bar_len, style=f"bold {col}")
        left_tbl.add_row(
            _priority_chip(lvl),
            str(count),
            mini_bar,
            f"{int(frac*100)}%",
        )

    right_tbl = RTable(
        title       = "[bold white]By Status[/bold white]",
        box         = box.SIMPLE_HEAD,
        border_style= MUTED,
        show_lines  = True,
        padding     = (0, 2),
        expand      = True,
    )
    right_tbl.add_column("Status",  justify="left",   width=14)
    right_tbl.add_column("Count",   justify="right",  style="bold white", width=7)
    right_tbl.add_column("Bar",     justify="left",   ratio=1)

    if tasks:
        status_counts = {}
        for t in tasks:
            s = t.status if hasattr(t, "status") else ("done" if t.done else "todo")
            status_counts[s] = status_counts.get(s, 0) + 1

        status_styles = {
            "todo":  ("○  todo",  "red"),
            "doing": ("◎  doing", "yellow"),
            "done":  ("✓  done",  "green"),
        }
        for st, (label, col) in status_styles.items():
            count = status_counts.get(st, 0)
            frac  = count / total if total else 0
            mini  = Text("█" * max(1, int(frac * 20)) if count else "", style=f"bold {col}")
            right_tbl.add_row(
                Text(label, style=f"bold {col}"),
                str(count),
                mini,
            )
    else:
        done_bar  = Text("█" * max(1, int((completed/total if total else 0) * 20)), style="bold green")
        pend_bar  = Text("█" * max(1, int((pending/total  if total else 0) * 20)), style="bold yellow")
        right_tbl.add_row(Text("✓  done",    style="bold green"),  str(completed), done_bar)
        right_tbl.add_row(Text("○  pending", style="bold yellow"), str(pending),   pend_bar)

    console.print(Padding(Columns([left_tbl, right_tbl], equal=True, expand=True), (0, 1)))

    # ── Footer ────────────────────────────────────────────────
    _spacer()
    mood = (
        "🎉 everything done — you crushed it!"   if pct == 100 else
        "🔥 almost there — keep going!"          if pct >= 75  else
        "⚡ good progress — stay focused!"       if pct >= 50  else
        "📋 plenty to do — one task at a time."  if pct >= 25  else
        "🚀 just getting started — let's go!"
    )
    _rule(title=f"[{DIM}]{mood}[/{DIM}]", style=MUTED)
    _spacer()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Help — full per-command reference
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _h_rule(label: str) -> None:
    _spacer()
    _rule(title=f"[bold white]{label}[/bold white]", style=MUTED)
    _spacer()

def _cmd(icon: str, name: str, syntax: str, summary: str) -> None:
    console.print(
        Text.assemble(
            Text(f"  {icon}  ", style=""),
            Text(f"{name}", style="bold cyan"),
            Text(f"  {syntax}", style="dim white"),
        )
    )
    console.print(f"  [white]{summary}[/white]")

def _flag(flag: str, typ: str, desc: str, default: str = "") -> None:
    t = Text()
    t.append(f"    {flag:<24}", style="bold yellow")
    t.append(f"{typ:<14}",      style=DIM)
    t.append(desc,              style="white")
    if default:
        t.append(f"  (default: {default})", style=DIM)
    console.print(t)

def _ex(cmd: str, note: str) -> None:
    console.print(f"    [bold white]{cmd}[/bold white]")
    console.print(f"    [dim]→ {note}[/dim]")

def _note(text: str) -> None:
    console.print(f"  [dim italic]ℹ  {text}[/dim italic]")

def _sub(label: str) -> None:
    console.print(f"\n  [bold grey62]{label}[/bold grey62]")


_IDX = [
    # ── Core task operations ──────────────────────────────────
    ("add",           "Create a new task",              'todoc add "Fix bug" -p high --tags "#backend"'),
    ("list",          "Show all tasks",                 "todoc list --pending --by priority"),
    ("done",          "Mark task(s) complete",          "todoc done 1   or   todoc done 1 2 5"),
    ("undone",        "Reopen a completed task",        "todoc undone 3"),
    ("edit",          "Change any field",               'todoc edit 2 -p critical --tags "urgent"'),
    ("delete",        "Remove a task forever",          "todoc delete 4 --force"),
    # ── Viewing & search ─────────────────────────────────────
    ("show",          "Full detail for one task",       "todoc show 3"),
    ("search",        "Find tasks by keyword",          'todoc search "#bug" --fuzzy'),
    ("sort",          "List sorted by a field",         "todoc sort --by priority"),
    ("stats",         "Completion statistics",          "todoc stats"),
    # ── Kanban & subtasks ────────────────────────────────────
    ("board",         "Kanban board: Todo/Doing/Done",  "todoc board"),
    ("status",        "Move task to a Kanban column",   "todoc status 3 doing"),
    ("subtask",       "Add a subtask to a task",        'todoc subtask 1 "Write tests" -p low'),
    # ── Interfaces ───────────────────────────────────────────
    ("tui",           "Interactive TUI dashboard",      "todoc tui"),
    # ── Housekeeping ─────────────────────────────────────────
    ("clear",         "Remove all done tasks",          "todoc clear"),
    ("reset",         "Wipe ALL tasks permanently",     "todoc reset --force"),
    ("notify",        "Desktop alert for urgent tasks", "todoc notify"),
    ("daemon",        "Background notification daemon", "todoc daemon start"),
    # ── Import / Export ──────────────────────────────────────
    ("export",        "Save tasks to file",             "todoc export -o backup.json"),
    ("import",        "Load tasks from file",           "todoc import backup.json"),
    # ── Notion sync ──────────────────────────────────────────
    ("push",          "Sync local tasks → Notion",      "todoc push"),
    ("pull",          "Sync Notion tasks → local",      "todoc pull"),
    ("notion-logout", "Remove saved Notion credentials","todoc notion-logout"),
    # ── Help ─────────────────────────────────────────────────
    ("help",          "Full command reference",         "todoc help --full"),
]


def render_summary() -> None:
    """Compact one-screen command list — todoc help --summary."""
    _spacer()
    brand = Text()
    brand.append("  ◈ todoc", style="bold cyan")
    brand.append("  —  command summary", style=DIM)
    console.print(brand)
    _spacer()

    tbl = Table(
        show_header  = True,
        header_style = "bold white on grey19",
        box          = box.SIMPLE_HEAD,
        border_style = MUTED,
        show_lines   = False,
        expand       = False,
        padding      = (0, 1),
    )
    tbl.add_column("Command",      style="bold cyan", width=14)
    tbl.add_column("What it does", style="white",     width=30)
    tbl.add_column("Example",      style="dim white", ratio=1, min_width=36)

    for cmd, desc, example in _IDX:
        tbl.add_row(cmd, desc, example)

    console.print(Padding(tbl, (0, 1)))
    _spacer()
    console.print(
        f"  [{DIM}]Run [bold]todoc help[/bold] for full details  ·  "
        f"[bold]todoc <cmd> --help[/bold] for per-command flags[/{DIM}]\n"
    )


def render_help() -> None:
    # ── Brand ──────────────────────────────────────────────────
    _spacer()
    h = Text(justify="center")
    h.append("\n  ◈  T O D O C\n",              style="bold cyan")
    h.append("  the most powerful terminal task manager\n", style=DIM)
    console.print(Panel(Align.center(h),
        border_style="cyan", box=DOUBLE, padding=(0, 8)))

    # ── Quick index ────────────────────────────────────────────
    _h_rule("Command Index")

    idx = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    idx.add_column(style="bold cyan",  width=12)
    idx.add_column(style="dim white",  width=34)
    idx.add_column(style="bold cyan",  width=12)
    idx.add_column(style="dim white",  width=34)

    for i in range(0, len(_IDX), 2):
        l = _IDX[i]; r = _IDX[i+1] if i+1 < len(_IDX) else ("", "", "")
        idx.add_row(l[0], l[1], r[0], r[1])
    console.print(Padding(idx, (0, 1)))

    # ══════════════════════════════════════════════════════════
    # CREATING TASKS
    # ══════════════════════════════════════════════════════════
    _h_rule("Creating Tasks")

    _cmd("➕", "add", '"description" [options]',
         'Create a new task. Description is the only required argument.')
    _sub("Flags")
    _flag("-p / --priority", "LEVEL",   "Set urgency level", "medium")
    _flag("--tags",          '"text"',  'Free-form info column — put anything here: #tags, dates, links, notes')
    _sub("Priority levels")
    console.print(f"    [bold white on bright_red] CRIT [/]  critical  [dim]— drop everything[/dim]")
    console.print(f"    [bold white on red] HIGH [/]  high      [dim]— needs to be done soon[/dim]")
    console.print(f"    [bold black on yellow] MED  [/]  medium    [dim]— normal tasks  (default)[/dim]")
    console.print(f"    [bold black on green] LOW  [/]  low       [dim]— someday / nice to have[/dim]")
    _sub("The Tags column")
    _note('Tags is a free-form text field — there is no fixed format.')
    _note('You can store hashtags, a due date, a link, a person\'s name, anything.')
    _note('Examples:  "#bug #backend"  |  "due:fri"  |  "ask @alice"  |  "see notion.so/abc"')
    _sub("Examples")
    _ex('todoc add "Buy groceries"',                             'Minimal task, medium priority')
    _ex('todoc add "Fix login bug" -p high',                     'High priority')
    _ex('todoc add "Ship v2" -p critical --tags "due:Mon #release"', 'Critical with tags')
    _ex('todoc add "Research AI" --tags "#reading notion.so/xyz"',   'Tags as link + hashtag')

    # ══════════════════════════════════════════════════════════
    # VIEWING TASKS
    # ══════════════════════════════════════════════════════════
    _h_rule("Viewing Tasks")

    _cmd("📋", "list", "[options]",
         'Show your task list. Done tasks appear with strikethrough and a green ✓.')
    _sub("Flags")
    _flag("--pending",       "flag",  'Show only tasks not yet done')
    _flag("--completed",     "flag",  'Show only finished tasks')
    _flag("-p / --priority", "LEVEL", 'Filter to one priority level')
    _flag("--by",            "FIELD", 'Sort order: id · priority · created', 'id')
    _flag("--desc",          "flag",  'Reverse the sort order')
    _sub("Notes")
    _note("By default all tasks are shown — done and pending together.")
    _note("Combine flags freely:  todoc list --pending --by priority")
    _sub("Examples")
    _ex("todoc list",                   'All tasks, sorted by id')
    _ex("todoc list --pending",         'Only tasks still to do')
    _ex("todoc list --completed",       'Only finished tasks')
    _ex("todoc list --by priority",     'Critical → high → medium → low')
    _ex("todoc list -p high",           'Only high-priority tasks')
    _spacer()

    _cmd("🔍", "show", "<id>",
         'Full detail panel for a single task — shows every field.')
    _sub("Examples")
    _ex("todoc show 3", 'All details for task #3')
    _spacer()

    _cmd("🔎", "search", '"query"',
         'Case-insensitive full-text search across description and tags.')
    _sub("Notes")
    _note("Matches partial words — searching 'bug' finds 'debug' too.")
    _note('Search for a tag with:  todoc search "#bug"')
    _sub("Examples")
    _ex('todoc search "auth"',   'Tasks mentioning auth anywhere')
    _ex('todoc search "#bug"',   'All tasks tagged #bug in their tags')
    _spacer()

    _cmd("↕", "sort", "--by FIELD [--desc]",
         'Display the full task list sorted by a specific field.')
    _sub("Sort fields")
    console.print(f"    [bold yellow]id        [/bold yellow][dim]Order tasks were created (default)[/dim]")
    console.print(f"    [bold yellow]priority  [/bold yellow][dim]Critical first, then high → medium → low[/dim]")
    console.print(f"    [bold yellow]created   [/bold yellow][dim]Oldest task first[/dim]")
    _sub("Flags")
    _flag("--desc", "flag", "Reverse the order — lowest priority first, newest first, etc.")
    _sub("Examples")
    _ex("todoc sort --by priority",      'Critical tasks at the top')
    _ex("todoc sort --by priority --desc",'Low priority tasks at the top')
    _spacer()

    _cmd("📊", "stats", "",
         'Summary: total / done / pending counts, visual progress bar, breakdown by priority.')
    _sub("Examples")
    _ex("todoc stats", 'Full statistics view')

    # ══════════════════════════════════════════════════════════
    # UPDATING TASKS
    # ══════════════════════════════════════════════════════════
    _h_rule("Updating Tasks")

    _cmd("✅", "done", "<id> [id id …]",
         'Mark one or more tasks complete. Tasks stay in the list with strikethrough.')
    _sub("Notes")
    _note("Pass multiple IDs at once to bulk-complete.")
    _note("Changed your mind?  todoc undone <id>  reopens a task.")
    _sub("Examples")
    _ex("todoc done 3",       'Complete task #3')
    _ex("todoc done 1 4 7",   'Complete tasks #1, #4, and #7 at once')
    _spacer()

    _cmd("↩", "undone", "<id>",
         'Reopen a completed task — moves it back to pending.')
    _sub("Examples")
    _ex("todoc undone 3", 'Reopen task #3')
    _spacer()

    _cmd("✏️", "edit", "<id> [options]",
         'Update one or more fields on an existing task. Only the flags you pass are changed.')
    _sub("Flags")
    _flag("-d / --desc",     "TEXT",   'Replace the task description')
    _flag("-p / --priority", "LEVEL",  'Change priority level')
    _flag("--tags",          '"text"', 'Replace the tags / info field')
    _sub("Notes")
    _note("Any flag you don't pass is left exactly as it was.")
    _note('To clear a field, pass an empty string:  todoc edit 3 --tags ""')
    _sub("Examples")
    _ex('todoc edit 3 -p critical',                       'Escalate to critical')
    _ex('todoc edit 3 --tags "#done waiting-for-review"', 'Update the tags field')
    _ex('todoc edit 3 -d "New description" -p high',      'Change two fields at once')

    # ══════════════════════════════════════════════════════════
    # REMOVING TASKS
    # ══════════════════════════════════════════════════════════
    _h_rule("Removing Tasks")

    _cmd("🗑️", "delete", "<id> [--force]",
         'Permanently delete one task. Shows a confirmation prompt unless --force is passed.')
    _sub("Flags")
    _flag("--force / -f", "flag", 'Delete immediately, skip the confirmation prompt')
    _sub("Notes")
    _note("Cannot be undone. If the task is just finished, use  todoc done  instead.")
    _note("To remove all finished tasks at once, use  todoc clear.")
    _sub("Examples")
    _ex("todoc delete 5",         'Delete task #5 — asks for confirmation')
    _ex("todoc delete 5 --force", 'Delete immediately, no prompt')
    _spacer()

    _cmd("🧹", "clear", "",
         'Remove all completed tasks in one shot. Asks for confirmation first.')
    _sub("Notes")
    _note("Only tasks marked ✓ done are removed — pending tasks are never touched.")
    _sub("Examples")
    _ex("todoc clear", 'Wipe all done tasks (with confirmation)')

    _spacer()

    _cmd("💥", "reset", "[--force]",
         'Permanently delete EVERY task — full wipe. Asks for confirmation unless --force is passed.')
    _sub("Flags")
    _flag("--force / -f", "flag", 'Skip confirmation and wipe immediately')
    _sub("Notes")
    _note("This deletes ALL tasks — done and pending. It cannot be undone.")
    _note("Run  todoc export -o backup.json  first if you want to keep a copy.")
    _sub("Examples")
    _ex("todoc reset",         'Full wipe — asks for confirmation')
    _ex("todoc reset --force", 'Full wipe immediately, no prompt')

    # ══════════════════════════════════════════════════════════
    # IMPORT / EXPORT
    # ══════════════════════════════════════════════════════════
    _h_rule("Import & Export")

    _cmd("📤", "export", "[--format json|csv] [-o FILE]",
         'Export all tasks. Prints to stdout by default so you can pipe it.')
    _sub("Flags")
    _flag("--format",      "FMT",  'json (default, full fidelity) or csv (spreadsheet-friendly)')
    _flag("-o / --output", "FILE", 'Write to a file path instead of printing to stdout')
    _sub("Notes")
    _note("JSON preserves every field and is ideal for backups.")
    _note("CSV is flat and opens directly in Excel / Google Sheets.")
    _sub("Examples")
    _ex("todoc export",                           'Print JSON to terminal')
    _ex("todoc export > backup.json",             'Redirect to a file')
    _ex("todoc export -o backup.json",            'Same — explicit flag')
    _ex("todoc export --format csv -o tasks.csv", 'Export as CSV')
    _spacer()

    _cmd("📥", "import", "<file.json>",
         'Import tasks from a JSON file created by  todoc export. IDs are reassigned automatically.')
    _sub("Notes")
    _note("IDs in the file are ignored — tasks get new IDs after your current highest.")
    _note("Only JSON format is supported for import.")
    _sub("Examples")
    _ex("todoc import backup.json", 'Restore from a backup')

    # ══════════════════════════════════════════════════════════
    # KANBAN & SUBTASKS
    # ══════════════════════════════════════════════════════════
    _h_rule("Kanban Board & Subtasks")

    _cmd("🗂️", "board", "",
         'Visualise your tasks as a three-column Kanban board: To Do | In Progress | Done.')
    _sub("Notes")
    _note("Use  todoc status <id> <todo|doing|done>  to move cards between columns.")
    _sub("Examples")
    _ex("todoc board", 'Open the full Kanban view')
    _spacer()

    _cmd("⇄", "status", "<id> <todo|doing|done>",
         'Move a task to a specific Kanban column without opening the board.')
    _sub("Status values")
    console.print(f"    [bold cyan]todo    [/bold cyan][dim]Backlog / not started yet[/dim]")
    console.print(f"    [bold cyan]doing   [/bold cyan][dim]In progress — actively being worked on[/dim]")
    console.print(f"    [bold cyan]done    [/bold cyan][dim]Completed[/dim]")
    _sub("Examples")
    _ex("todoc status 3 doing",   'Start working on task #3')
    _ex("todoc status 3 done",    'Mark task #3 as complete')
    _ex("todoc status 3 todo",    'Move task #3 back to the backlog')
    _spacer()

    _cmd("➕", "subtask", "<parent-id> \"description\" [options]",
         'Add a subtask nested under an existing task. Appears indented in  todoc show <id>.')
    _sub("Flags")
    _flag("-p / --priority", "LEVEL", "Priority of the subtask", "medium")
    _sub("Notes")
    _note("Run  todoc show <parent-id>  to see all subtasks under a task.")
    _sub("Examples")
    _ex('todoc subtask 1 "Write unit tests"',          'Add a subtask to task #1')
    _ex('todoc subtask 1 "Update changelog" -p low',   'Subtask with low priority')

    # ══════════════════════════════════════════════════════════
    # INTERACTIVE TUI
    # ══════════════════════════════════════════════════════════
    _h_rule("Interactive TUI")

    _cmd("🖥️", "tui", "",
         'Launch a full interactive terminal dashboard — browse, edit, and manage tasks without typing commands.')
    _sub("Keyboard shortcuts")
    console.print(f"    [bold cyan]a[/bold cyan]          [dim]Add a new task[/dim]")
    console.print(f"    [bold cyan]e[/bold cyan]          [dim]Edit selected task[/dim]")
    console.print(f"    [bold cyan]Space[/bold cyan]      [dim]Toggle done / pending[/dim]")
    console.print(f"    [bold cyan]n[/bold cyan]          [dim]Cycle status: todo → doing → done[/dim]")
    console.print(f"    [bold cyan]d[/bold cyan]          [dim]Delete selected task[/dim]")
    console.print(f"    [bold cyan]/[/bold cyan]          [dim]Focus fuzzy search bar[/dim]")
    console.print(f"    [bold cyan]r[/bold cyan]          [dim]Refresh list[/dim]")
    console.print(f"    [bold cyan]q[/bold cyan]          [dim]Quit[/dim]")
    _sub("Requirements")
    _note("Requires the  textual  package:  pip install textual")
    _sub("Examples")
    _ex("todoc tui", 'Launch the interactive dashboard')

    # ══════════════════════════════════════════════════════════
    # NOTIFICATIONS & DAEMON
    # ══════════════════════════════════════════════════════════
    _h_rule("Notifications & Daemon")

    _cmd("🔔", "notify", "",
         'Send an immediate desktop notification listing all HIGH and CRITICAL pending tasks.')
    _sub("Platform support")
    _note("macOS — native Notification Center")
    _note("Linux — notify-send  (install  libnotify-bin  if missing)")
    _note("Windows — plyer  (pip install plyer)")
    _sub("Examples")
    _ex("todoc notify",                          'Fire a notification right now')
    _ex("*/30 * * * * todoc notify",             'Crontab entry for alerts every 30 min')
    _spacer()

    _cmd("⚙️", "daemon", "<start|stop|status|run>",
         'Manage the background notification daemon. Sends desktop alerts at 4h, 6h, 9h, 12h, 18h, 24h for pending tasks.')
    _sub("Actions")
    console.print(f"    [bold cyan]start   [/bold cyan][dim]Install and start the daemon[/dim]")
    console.print(f"    [bold cyan]stop    [/bold cyan][dim]Uninstall the daemon[/dim]")
    console.print(f"    [bold cyan]status  [/bold cyan][dim]Check whether the daemon is currently running[/dim]")
    console.print(f"    [bold cyan]run     [/bold cyan][dim]Run a single notification check right now (used internally)[/dim]")
    _sub("Platform support")
    _note("macOS → launchd   |   Linux → systemd user timer (cron fallback)   |   Windows → Task Scheduler")
    _sub("Examples")
    _ex("todoc daemon start",  'Install and start the background daemon')
    _ex("todoc daemon stop",   'Remove the daemon entirely')
    _ex("todoc daemon status", 'See if it is currently running')

    # ══════════════════════════════════════════════════════════
    # NOTION SYNC
    # ══════════════════════════════════════════════════════════
    _h_rule("Notion Sync")

    _cmd("↑", "push", "[--reset]",
         'Upload all local tasks to Notion (local → Notion, full sync). Credentials are saved on first run.')
    _sub("Flags")
    _flag("--reset", "flag", "Forget saved credentials and re-enter them")
    _sub("First-time setup")
    _note("1. Create an integration at  https://www.notion.so/my-integrations")
    _note("2. Copy the Internal Integration Token")
    _note("3. Share your target Notion page with the integration")
    _note("4. Copy the 32-char Page ID from the page URL")
    _note("Credentials are saved to  ~/.todoc/notion_creds.json  for all future syncs.")
    _sub("Examples")
    _ex("todoc push",          'Sync local tasks to Notion')
    _ex("todoc push --reset",  'Update saved credentials, then sync')
    _spacer()

    _cmd("↓", "pull", "[--reset]",
         'Download tasks from Notion and replace local tasks (Notion → local, full sync). Auto-backs up local tasks first.')
    _sub("Flags")
    _flag("--reset", "flag", "Forget saved credentials and re-enter them")
    _sub("Notes")
    _note("Local tasks are backed up to  ~/.todoc/tasks_before_pull.json  before overwriting.")
    _note("Credentials are shared with  todoc push — set up once, works for both.")
    _sub("Examples")
    _ex("todoc pull",          'Sync Notion tasks to local')
    _ex("todoc pull --reset",  'Update saved credentials, then pull')
    _spacer()

    _cmd("🔓", "notion-logout", "",
         'Delete saved Notion credentials from this machine. The next push or pull will prompt again.')
    _sub("Examples")
    _ex("todoc notion-logout", 'Remove stored Notion credentials')

    # ── Footer ─────────────────────────────────────────────────
    _spacer()
    _rule(style=MUTED)
    console.print(
        f"\n  [{DIM}]Run [bold]todoc <command> --help[/bold] for the raw Typer flag list of any command.[/{DIM}]"
        f"\n  [{DIM}]To get a summary of all commands, type [bold]todoc -s[/bold][/{DIM}]\n")
