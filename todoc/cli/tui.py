"""
todoc · tui.py
Interactive TUI dashboard powered by Textual.
Launch with:  todoc tui
"""
from __future__ import annotations

from textual.app            import App, ComposeResult
from textual.widgets        import (
    Header, Footer, DataTable, Label, Input, Button,
    Static, Select
)
from textual.containers     import Horizontal, Vertical, Container
from textual.screen         import ModalScreen
from textual.binding        import Binding
from textual.reactive       import reactive
from rich.text              import Text
from typing                 import List

from todoc.core.service     import TodoService
from todoc.core.models      import Task


# ── Colour helpers ────────────────────────────────────────────

_CHIP_STYLE = {
    "critical": ("bold white", "red"),
    "high":     ("bold",       "dark_red"),
    "medium":   ("bold",       "dark_goldenrod"),
    "low":      ("bold",       "dark_green"),
}

def _priority_text(priority: str) -> Text:
    fg, bg  = _CHIP_STYLE.get(priority.lower(), ("bold", "dark_goldenrod"))
    labels  = {"critical": " CRIT ", "high": " HIGH ", "medium": " MED  ", "low": " LOW  "}
    label   = labels.get(priority.lower(), " MED  ")
    t       = Text(label, style=f"{fg} on {bg}")
    return t

def _status_text(status: str) -> Text:
    s = {"todo": ("○", "red"), "doing": ("◎", "yellow"), "done": ("✓", "green")}
    ch, col = s.get(status, ("○", "red"))
    return Text(ch, style=f"bold {col}")


# ── Add / Edit Modal ──────────────────────────────────────────

class TaskFormModal(ModalScreen):
    """Modal for adding or editing a task."""

    CSS = """
    TaskFormModal {
        align: center middle;
    }
    #modal-box {
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        width: 70;
        height: auto;
    }
    #modal-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    .form-label {
        color: $text-muted;
        margin-top: 1;
    }
    #modal-actions {
        margin-top: 2;
    }
    """

    def __init__(self, task: Task | None = None) -> None:
        super().__init__()
        self._task_data = task  # None = add mode, Task = edit mode

    def compose(self) -> ComposeResult:
        t = self._task_data
        with Container(id="modal-box"):
            yield Label("Edit Task" if t else "Add New Task", id="modal-title")
            yield Label("Description", classes="form-label")
            yield Input(value=t.description if t else "", placeholder="What needs to be done?", id="inp-desc")
            yield Label("Priority", classes="form-label")
            yield Select(
                [("critical", "critical"), ("high", "high"), ("medium", "medium"), ("low", "low")],
                value=t.priority if t else "medium",
                id="inp-priority",
            )
            yield Label("Tags  (free-form)", classes="form-label")
            yield Input(value=t.tags if t else "", placeholder="#bug @alice due:fri", id="inp-tags")
            if t:
                yield Label("Status", classes="form-label")
                yield Select(
                    [("todo", "todo"), ("doing", "doing"), ("done", "done")],
                    value=t.status if t else "todo",
                    id="inp-status",
                )
            with Horizontal(id="modal-actions"):
                yield Button("Save  [Enter]", variant="primary", id="btn-save")
                yield Button("Cancel  [Esc]", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save()
        else:
            self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "enter":
            self._save()
        elif event.key == "escape":
            self.dismiss(None)

    def _save(self) -> None:
        desc     = self.query_one("#inp-desc",     Input).value.strip()
        priority = self.query_one("#inp-priority",  Select).value or "medium"
        tags     = self.query_one("#inp-tags",      Input).value.strip()
        status   = "todo"
        if self._task_data:
            try:
                status = self.query_one("#inp-status", Select).value or "todo"
            except Exception:
                pass

        if not desc:
            return

        self.dismiss({
            "description": desc,
            "priority":    priority,
            "tags":        tags,
            "status":      status,
        })


# ── Confirm Modal ─────────────────────────────────────────────

class ConfirmModal(ModalScreen):
    CSS = """
    ConfirmModal { align: center middle; }
    #confirm-box {
        background: $surface; border: solid $error;
        padding: 1 2; width: 50; height: auto;
    }
    #confirm-msg { color: $text; margin-bottom: 1; }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-box"):
            yield Label(self.message, id="confirm-msg")
            with Horizontal():
                yield Button("Yes  [y]", variant="error",   id="btn-yes")
                yield Button("No   [n]", variant="default", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")

    def on_key(self, event) -> None:
        if event.key in ("y", "enter"):
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)


# ── Main TUI App ──────────────────────────────────────────────

class TodocApp(App):
    """Interactive todoc TUI dashboard."""

    CSS = """
    Screen {
        background: $background;
    }
    #layout {
        height: 1fr;
    }
    #sidebar {
        width: 22;
        border-right: solid $primary-darken-2;
        background: $surface-darken-1;
        padding: 1;
    }
    #sidebar-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
        text-align: center;
    }
    .filter-btn {
        width: 100%;
        margin-bottom: 0;
        background: transparent;
        border: none;
        color: $text-muted;
        text-align: left;
        padding: 0 1;
        height: 2;
    }
    .filter-btn:hover { background: $surface; color: $text; }
    .filter-btn.active { color: $primary; text-style: bold; background: $surface; }
    #main-area { padding: 0 1; }
    #status-bar {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
    }
    #task-table {
        height: 1fr;
    }
    DataTable { height: 1fr; }
    DataTable > .datatable--header { background: $surface; color: $primary; text-style: bold; }
    DataTable > .datatable--cursor { background: $primary-darken-2; }
    """

    BINDINGS = [
        Binding("a",      "add_task",    "Add",      show=True),
        Binding("e",      "edit_task",   "Edit",     show=True),
        Binding("space",  "toggle_done", "Done/Undo",show=True),
        Binding("d",      "delete_task", "Delete",   show=True),
        Binding("n",      "next_status", "→ Status", show=True),
        Binding("r",      "refresh",     "Refresh",  show=True),
        Binding("q",      "quit",        "Quit",     show=True),
        Binding("/",      "focus_search","Search",   show=True),
    ]

    filter_mode: reactive[str] = reactive("all")
    status_msg:  reactive[str] = reactive("  ◈ todoc  ·  ready")

    def __init__(self) -> None:
        super().__init__()
        self.svc    = TodoService()
        self._tasks : List[Task] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Label("◈ FILTERS", id="sidebar-title")
                yield Button("All tasks",    id="f-all",       classes="filter-btn active")
                yield Button("Pending",      id="f-todo",      classes="filter-btn")
                yield Button("In progress",  id="f-doing",     classes="filter-btn")
                yield Button("Done",         id="f-done",      classes="filter-btn")
                yield Button("Critical",     id="f-critical",  classes="filter-btn")
                yield Button("High",         id="f-high",      classes="filter-btn")
                yield Label("", id="sidebar-stats")
            with Vertical(id="main-area"):
                yield Input(placeholder="/ to search…", id="search-box")
                yield DataTable(id="task-table", cursor_type="row")
        yield Static(self.status_msg, id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._setup_table()
        self._refresh_data()

    def _setup_table(self) -> None:
        tbl = self.query_one("#task-table", DataTable)
        tbl.add_columns("#", "Priority", "St", "Description", "Tags")

    def _refresh_data(self, query: str = "") -> None:
        svc   = self.svc
        if query:
            tasks = svc.fuzzy_search(query) if len(query) >= 2 else svc.search(query)
        else:
            tasks = svc.get_tasks(include_subtasks=False)

        # Apply sidebar filter
        fm = self.filter_mode
        if fm == "todo":
            tasks = [t for t in tasks if t.status == "todo"]
        elif fm == "doing":
            tasks = [t for t in tasks if t.status == "doing"]
        elif fm == "done":
            tasks = [t for t in tasks if t.done]
        elif fm in ("critical", "high"):
            tasks = [t for t in tasks if t.priority == fm and not t.done]

        self._tasks = tasks
        tbl = self.query_one("#task-table", DataTable)
        tbl.clear()
        for t in tasks:
            subtask_flag = " ↳" if t.is_subtask else ""
            desc = Text(t.description + subtask_flag)
            if t.done:
                desc.stylize("strike dim")
            tbl.add_row(
                str(t.id),
                _priority_text(t.priority),
                _status_text(t.status),
                desc,
                Text(t.tags or "—", style="cyan" if t.tags else "dim"),
                key=str(t.id),
            )

        # sidebar stats
        total     = len(svc.get_tasks(include_subtasks=False))
        done_n    = sum(1 for t in svc.get_tasks() if t.done)
        pending_n = total - done_n
        pct       = int(done_n / total * 100) if total else 0
        stats_lbl = self.query_one("#sidebar-stats", Label)
        stats_lbl.update(
            f"\n [dim]{done_n}/{total} done[/]\n [yellow]{pending_n} pending[/]\n [cyan]{pct}%[/]"
        )
        self._set_status(f"  {len(tasks)} task(s) shown  ·  {done_n}/{total} done  ·  {pct}%")

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(msg)

    def _selected_task(self) -> Task | None:
        tbl = self.query_one("#task-table", DataTable)
        if tbl.cursor_row < 0 or tbl.cursor_row >= len(self._tasks):
            return None
        return self._tasks[tbl.cursor_row]

    # ── Actions ──────────────────────────────────────────────

    def action_add_task(self) -> None:
        def _on_close(result):
            if result:
                self.svc.create_task(**{k: v for k, v in result.items()
                                        if k in ("description", "priority", "tags")})
                self._refresh_data()
                self._set_status("  ✓ Task added")
        self.push_screen(TaskFormModal(), _on_close)

    def action_edit_task(self) -> None:
        task = self._selected_task()
        if not task:
            return
        def _on_close(result):
            if result:
                self.svc.edit_task(
                    task.id,
                    description = result["description"],
                    priority    = result["priority"],
                    tags        = result["tags"],
                    status      = result.get("status"),
                )
                self._refresh_data()
                self._set_status(f"  ✓ Task #{task.id} updated")
        self.push_screen(TaskFormModal(task=task), _on_close)

    def action_toggle_done(self) -> None:
        task = self._selected_task()
        if not task:
            return
        if task.done:
            self.svc.uncomplete_task(task.id)
            self._set_status(f"  ↩ Task #{task.id} reopened")
        else:
            self.svc.complete_task(task.id)
            self._set_status(f"  ✓ Task #{task.id} marked done")
        self._refresh_data()

    def action_next_status(self) -> None:
        """Cycle status: todo → doing → done → todo"""
        task = self._selected_task()
        if not task:
            return
        cycle   = ["todo", "doing", "done"]
        current = task.status if task.status in cycle else "todo"
        nxt     = cycle[(cycle.index(current) + 1) % len(cycle)]
        self.svc.set_status(task.id, nxt)
        self._refresh_data()
        self._set_status(f"  ◎ Task #{task.id} → {nxt}")

    def action_delete_task(self) -> None:
        task = self._selected_task()
        if not task:
            return
        def _on_close(confirmed):
            if confirmed:
                self.svc.remove_task(task.id)
                self._refresh_data()
                self._set_status(f"  🗑 Task #{task.id} deleted")
        self.push_screen(
            ConfirmModal(f"Delete #{task.id} \"{task.description[:40]}\"?"),
            _on_close,
        )

    def action_refresh(self) -> None:
        self._refresh_data()
        self._set_status("  ↺ Refreshed")

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    # ── Search input ─────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-box":
            self._refresh_data(query=event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-box":
            self.query_one("#task-table", DataTable).focus()

    # ── Sidebar filter buttons ────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        fmap = {
            "f-all":      "all",
            "f-todo":     "todo",
            "f-doing":    "doing",
            "f-done":     "done",
            "f-critical": "critical",
            "f-high":     "high",
        }
        if event.button.id in fmap:
            # toggle active class
            for btn in self.query(".filter-btn"):
                btn.remove_class("active")
            event.button.add_class("active")
            self.filter_mode = fmap[event.button.id]
            self._refresh_data()


def launch_tui() -> None:
    """Entry point called from main.py."""
    app = TodocApp()
    app.run()
