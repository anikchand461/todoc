from typing import List, Optional, Dict
from datetime import datetime

from todoc.core.models import Task
from todoc.storage.repository import TaskRepository
from todoc.exceptions import TaskNotFoundError


class TodoService:
    def __init__(self):
        self.repo = TaskRepository()

    # ── internals ─────────────────────────────────────────────

    def _next_id(self, tasks: List[Task]) -> int:
        return 1 if not tasks else max(t.id for t in tasks) + 1

    def _get_or_raise(self, task_id: int) -> Task:
        target = next((t for t in self.repo.get_all() if t.id == task_id), None)
        if not target:
            raise TaskNotFoundError(f"Task #{task_id} not found.")
        return target

    # ── create ────────────────────────────────────────────────

    def create_task(
        self,
        description: str,
        priority:    str = "medium",
        tags:        str = "",
    ) -> Task:
        tasks    = self.repo.get_all()
        new_task = Task(
            id          = self._next_id(tasks),
            description = description,
            priority    = priority,
            tags        = tags,
            created_at  = datetime.now().strftime("%Y-%m-%d %H:%M"),
            status      = "todo",
        )
        self.repo.add(new_task)
        return new_task

    def add_subtask(self, parent_id: int, description: str, priority: str = "medium") -> Task:
        """Create a subtask under an existing task."""
        parent   = self._get_or_raise(parent_id)
        tasks    = self.repo.get_all()
        subtask  = Task(
            id          = self._next_id(tasks),
            description = description,
            priority    = priority,
            created_at  = datetime.now().strftime("%Y-%m-%d %H:%M"),
            parent_id   = parent_id,
            status      = "todo",
        )
        self.repo.add(subtask)

        # Register child on parent
        ids = parent.subtask_id_list
        ids.append(subtask.id)
        parent.subtask_ids = ",".join(str(i) for i in ids)
        self.repo.update(parent)
        return subtask

    # ── read ──────────────────────────────────────────────────

    def get_tasks(self, include_subtasks: bool = True) -> List[Task]:
        tasks = self.repo.get_all()
        if not include_subtasks:
            tasks = [t for t in tasks if not t.is_subtask]
        return tasks

    def get_task(self, task_id: int) -> Task:
        return self._get_or_raise(task_id)

    def get_subtasks(self, parent_id: int) -> List[Task]:
        return [t for t in self.repo.get_all() if t.parent_id == parent_id]

    def get_kanban_board(self) -> Dict[str, List[Task]]:
        """Return tasks bucketed into todo / doing / done columns."""
        tasks = [t for t in self.repo.get_all() if not t.is_subtask]
        board: Dict[str, List[Task]] = {"todo": [], "doing": [], "done": []}
        for t in tasks:
            col = t.status if t.status in board else ("done" if t.done else "todo")
            board[col].append(t)
        return board

    # ── fuzzy search ──────────────────────────────────────────

    @staticmethod
    def _fuzzy_score(needle: str, haystack: str) -> int:
        """
        Returns a score > 0 if needle characters appear in order in haystack.
        Higher score = better match (fewer gaps between chars).
        """
        needle    = needle.lower()
        haystack  = haystack.lower()
        if needle in haystack:
            return 1000 - haystack.index(needle)  # exact substring wins

        n, h  = 0, 0
        score = 0
        prev  = -1
        while n < len(needle) and h < len(haystack):
            if needle[n] == haystack[h]:
                gap    = h - prev - 1
                score += max(10 - gap, 1)
                prev   = h
                n     += 1
            h += 1

        if n < len(needle):
            return 0   # not all chars found
        return score

    def fuzzy_search(self, query: str) -> List[Task]:
        """Return tasks sorted by fuzzy match score (desc)."""
        results = []
        for task in self.repo.get_all():
            combined = f"{task.description} {task.tags}"
            score    = self._fuzzy_score(query, combined)
            if score > 0:
                results.append((score, task))
        results.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in results]

    def search(self, query: str, fuzzy: bool = False) -> List[Task]:
        if fuzzy:
            return self.fuzzy_search(query)
        q = query.lower()
        return [t for t in self.repo.get_all()
                if q in t.description.lower() or q in t.tags.lower()]

    def sorted_tasks(self, by: str = "id", reverse: bool = False) -> List[Task]:
        _rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        key_fns = {
            "id":       lambda t: t.id,
            "priority": lambda t: _rank.get(t.priority, 2),
            "created":  lambda t: t.created_at or "",
        }
        fn = key_fns.get(by, key_fns["id"])
        return sorted(self.repo.get_all(), key=fn, reverse=reverse)

    # ── notifications ─────────────────────────────────────────

    # ── auto-notify thresholds ───────────────────────────────────
    #   HIGH     tasks pending > 6 hours  → notify
    #   CRITICAL tasks pending > 6 hours  → notify
    #   Any task pending > 24 hours       → notify
    #   Re-notify every 6 hours max (cooldown) to avoid spam

    _NOTIFY_THRESHOLD_HOURS = {
        "critical": 4,
        "high":     12,
        "medium":   24,
        "low":      48,
    }
    _NOTIFY_COOLDOWN_HOURS = 4   # don't re-notify same task within 6 hours

    def _hours_since(self, ts: str) -> float:
        """Return hours since an ISO datetime string, or infinity if empty."""
        if not ts:
            return float("inf")
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M")
            return (datetime.now() - dt).total_seconds() / 3600
        except ValueError:
            return float("inf")

    def get_notify_tasks(self) -> List[Task]:
        """
        Return tasks that should trigger a notification right now.
        Rules:
          - Task is pending (not done)
          - Task has been pending longer than its priority threshold
          - Task has not been notified in the last COOLDOWN hours
        """
        due = []
        for t in self.repo.get_all():
            if t.done:
                continue
            threshold = self._NOTIFY_THRESHOLD_HOURS.get(t.priority, 24)
            age_hrs   = self._hours_since(t.created_at)
            cooldown  = self._hours_since(t.notified_at)

            if age_hrs >= threshold and cooldown >= self._NOTIFY_COOLDOWN_HOURS:
                due.append(t)
        return due

    def notify_check(self) -> List[Task]:
        """
        Auto-fire desktop notifications for overdue pending tasks.
        Called automatically on `todoc list` — no manual trigger needed.
        Updates notified_at on each task to prevent spam.
        Returns the list of tasks that triggered notifications.
        """
        tasks = self.get_notify_tasks()
        if not tasks:
            return []

        # Group by urgency for the notification message
        critical = [t for t in tasks if t.priority == "critical"]
        high     = [t for t in tasks if t.priority == "high"]
        others   = [t for t in tasks if t.priority not in ("critical", "high")]

        # Build notification body
        lines = []
        for t in (critical + high + others)[:6]:
            age_hrs = self._hours_since(t.created_at)
            age_str = f"{int(age_hrs)}h" if age_hrs < 24 else f"{int(age_hrs/24)}d"
            lines.append(f"[{t.priority.upper()}] {t.description}  ({age_str} pending)")
        if len(tasks) > 6:
            lines.append(f"…and {len(tasks) - 6} more")

        summary = f"todoc · {len(tasks)} task(s) still pending"
        body    = "\n".join(lines)

        _send_notification(summary, body)

        # Stamp notified_at so we respect the cooldown
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for t in tasks:
            t.notified_at = now
            self.repo.update(t)

        return tasks

    # ── status (Kanban column) ─────────────────────────────────

    def set_status(self, task_id: int, status: str) -> Task:
        """Set status: todo | doing | done"""
        valid = {"todo", "doing", "done"}
        if status not in valid:
            raise ValueError(f"Status must be one of {valid}")
        task        = self._get_or_raise(task_id)
        task.status = status
        task.done   = (status == "done")
        self.repo.update(task)
        return task

    # ── update ────────────────────────────────────────────────

    def complete_task(self, task_id: int) -> Task:
        return self.set_status(task_id, "done")

    def uncomplete_task(self, task_id: int) -> Task:
        return self.set_status(task_id, "todo")

    def edit_task(
        self,
        task_id:     int,
        description: Optional[str] = None,
        priority:    Optional[str] = None,
        tags:        Optional[str] = None,
        status:      Optional[str] = None,
    ) -> Task:
        task = self._get_or_raise(task_id)
        if description is not None: task.description = description
        if priority    is not None: task.priority    = priority
        if tags        is not None: task.tags        = tags
        if status      is not None:
            task.status = status
            task.done   = (status == "done")
        self.repo.update(task)
        return task

    def bulk_complete(self, task_ids: List[int]) -> List[Task]:
        done = []
        for tid in task_ids:
            try:
                done.append(self.complete_task(tid))
            except TaskNotFoundError:
                pass
        return done

    # ── delete ────────────────────────────────────────────────

    def remove_task(self, task_id: int) -> None:
        # Also remove any subtasks
        task = self._get_or_raise(task_id)
        for sub_id in task.subtask_id_list:
            try:
                self.repo.delete(sub_id)
            except Exception:
                pass
        self.repo.delete(task_id)

    def remove_all_done(self) -> int:
        tasks = [t for t in self.repo.get_all() if t.done]
        for t in tasks:
            self.repo.delete(t.id)
        return len(tasks)

    def remove_all_tasks(self) -> int:
        tasks = self.repo.get_all()
        for t in tasks:
            self.repo.delete(t.id)
        return len(tasks)

    # ── export / import ───────────────────────────────────────

    def export_json(self) -> str:
        import json
        return json.dumps([t.to_dict() for t in self.repo.get_all()], indent=2)

    def export_csv(self) -> str:
        import csv, io
        tasks = self.repo.get_all()
        if not tasks:
            return ""
        fieldnames = list(tasks[0].to_dict().keys())
        buf    = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames,
                                quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writeheader()
        for t in tasks:
            row         = t.to_dict()
            row["done"] = "true" if row["done"] else "false"
            writer.writerow(row)
        return buf.getvalue()

    def import_json(self, json_str: str) -> int:
        import json
        data   = json.loads(json_str)
        max_id = max((t.id for t in self.repo.get_all()), default=0)
        for item in data:
            max_id    += 1
            item["id"] = max_id
            self.repo.add(Task.from_dict(item))
        return len(data)


# ── notification helper (cross-platform) ──────────────────────

def _find_terminal_notifier() -> str | None:
    """Find terminal-notifier binary — checks common Homebrew paths."""
    import shutil
    # Check PATH first
    found = shutil.which("terminal-notifier")
    if found:
        return found
    # Common Homebrew locations (Apple Silicon and Intel Mac)
    for path in [
        "/opt/homebrew/bin/terminal-notifier",   # Apple Silicon (M1/M2/M3)
        "/usr/local/bin/terminal-notifier",       # Intel Mac
        "/opt/local/bin/terminal-notifier",       # MacPorts
    ]:
        import os
        if os.path.isfile(path):
            return path
    return None


def _send_notification(title: str, body: str) -> None:
    """
    Send a native desktop notification.

    macOS   — terminal-notifier directly (most reliable)
              fallback → osascript
    Linux   — notify-send
    Windows — plyer
    """
    import sys, subprocess
    try:
        if sys.platform == "darwin":
            tn = _find_terminal_notifier()
            if tn:
                # Call terminal-notifier directly — same as running it in terminal
                # Use a single-line body (terminal-notifier doesn't support \n well)
                safe_body = body.replace("\n", "  |  ")
                result = subprocess.run(
                    [
                        tn,
                        "-title",   title,
                        "-message", safe_body,
                        "-sound",   "default",
                        "-sender",  "com.apple.Terminal",
                        "-group",   "todoc",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return
                # If it failed, fall through to osascript

            # ── Fallback: osascript ───────────────────────────────
            safe_body  = body.replace('"', ' ').replace("\n", " | ")
            safe_title = title.replace('"', ' ')
            script = (
                f'display notification "{safe_body}" '
                f'with title "{safe_title}" '
                f'sound name "default"'
            )
            subprocess.run(
                ["osascript", "-e", script],
                check=False, capture_output=True,
            )

        elif sys.platform.startswith("linux"):
            subprocess.run(
                ["notify-send", "--urgency=critical", "--app-name=todoc", title, body],
                check=False, capture_output=True,
            )

        elif sys.platform == "win32":
            try:
                from plyer import notification
                notification.notify(
                    title=title, message=body, app_name="todoc", timeout=8,
                )
            except ImportError:
                pass

    except Exception:
        pass   # never crash the CLI due to a notification failure
