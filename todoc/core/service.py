from typing import List, Optional
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
        )
        self.repo.add(new_task)
        return new_task

    # ── read ──────────────────────────────────────────────────

    def get_tasks(self) -> List[Task]:
        return self.repo.get_all()

    def get_task(self, task_id: int) -> Task:
        return self._get_or_raise(task_id)

    def search(self, query: str) -> List[Task]:
        """Case-insensitive search in description and tags."""
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

    # ── update ────────────────────────────────────────────────

    def complete_task(self, task_id: int) -> Task:
        task = self._get_or_raise(task_id)
        task.done = True
        self.repo.update(task)
        return task

    def uncomplete_task(self, task_id: int) -> Task:
        task = self._get_or_raise(task_id)
        task.done = False
        self.repo.update(task)
        return task

    def edit_task(
        self,
        task_id:     int,
        description: Optional[str] = None,
        priority:    Optional[str] = None,
        tags:        Optional[str] = None,
    ) -> Task:
        task = self._get_or_raise(task_id)
        if description is not None: task.description = description
        if priority    is not None: task.priority    = priority
        if tags        is not None: task.tags        = tags
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
        self.repo.delete(task_id)

    def remove_all_done(self) -> int:
        tasks = [t for t in self.repo.get_all() if t.done]
        for t in tasks:
            self.repo.delete(t.id)
        return len(tasks)

    # ── export / import ───────────────────────────────────────

    def remove_all_tasks(self) -> int:
        """Delete every task — full reset."""
        tasks = self.repo.get_all()
        for t in tasks:
            self.repo.delete(t.id)
        return len(tasks)

    def export_json(self) -> str:
        import json
        return json.dumps([t.to_dict() for t in self.repo.get_all()], indent=2)

    def export_csv(self) -> str:
        import csv, io
        tasks = self.repo.get_all()
        if not tasks:
            return ""

        fieldnames = list(tasks[0].to_dict().keys())
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames     = fieldnames,
            quoting        = csv.QUOTE_ALL,
            lineterminator = "\n",
        )
        writer.writeheader()
        for t in tasks:
            row = t.to_dict()
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
