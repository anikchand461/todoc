import json
from pathlib import Path
from typing import List

from todoc.config.settings import DATA_FILE_PATH
from todoc.core.models import Task
from todoc.exceptions import StorageError

class TaskRepository:
    def __init__(self, path: Path = DATA_FILE_PATH):
        self.path = path

    def _ensure_file_exists(self):
        if not self.path.exists():
            self.path.touch()
            self._write_data([])

    def _read_data(self) -> List[dict]:
        try:
            self._ensure_file_exists()
            with open(self.path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except json.JSONDecodeError as e:
            raise StorageError(f"Corrupted data file: {e}")
        except IOError as e:
            raise StorageError(f"Cannot read file: {e}")

    def _write_data(self, data: List[dict]):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            raise StorageError(f"Cannot write file: {e}")

    def get_all(self) -> List[Task]:
        raw_data = self._read_data()
        return [Task.from_dict(item) for item in raw_data]

    def save_all(self, tasks: List[Task]):
        raw_data = [task.to_dict() for task in tasks]
        self._write_data(raw_data)

    def add(self, task: Task):
        tasks = self.get_all()
        tasks.append(task)
        self.save_all(tasks)

    def update(self, updated_task: Task):
        tasks = self.get_all()
        found = False
        for i, t in enumerate(tasks):
            if t.id == updated_task.id:
                tasks[i] = updated_task
                found = True
                break
        if not found:
            from todoc.exceptions import TaskNotFoundError
            raise TaskNotFoundError(f"Task with ID {updated_task.id} not found.")
        self.save_all(tasks)

    def delete(self, task_id: int):
        tasks = self.get_all()
        original_len = len(tasks)
        tasks = [t for t in tasks if t.id != task_id]
        
        if len(tasks) == original_len:
            from todoc.exceptions import TaskNotFoundError
            raise TaskNotFoundError(f"Task with ID {task_id} not found.")
            
        self.save_all(tasks)
