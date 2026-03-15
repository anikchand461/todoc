from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List


@dataclass
class Task:
    id:          int
    description: str
    done:        bool        = False
    priority:    str         = "medium"   # low | medium | high | critical
    tags:        str         = ""         # free-form info
    created_at:  str         = ""         # set automatically on creation
    notified_at: str         = ""         # last time a notification was sent for this task
    status:      str         = "todo"     # todo | doing | done  (for Kanban)
    parent_id:   int         = 0          # 0 = top-level; >0 = subtask of parent
    subtask_ids: str         = ""         # comma-separated child IDs e.g. "3,4,5"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Backward-compatible — drops unknown fields, fills missing ones."""
        known = {f for f in cls.__dataclass_fields__}      # type: ignore[attr-defined]
        data.setdefault("priority",    "medium")
        data.setdefault("tags",        "")
        data.setdefault("created_at",  "")
        data.setdefault("notified_at", "")
        data.setdefault("status",      "done" if data.get("done") else "todo")
        data.setdefault("parent_id",   0)
        data.setdefault("subtask_ids", "")
        return cls(**{k: v for k, v in data.items() if k in known})

    # ── helpers ──────────────────────────────────────────────

    @property
    def subtask_id_list(self) -> List[int]:
        if not self.subtask_ids:
            return []
        try:
            return [int(x) for x in self.subtask_ids.split(",") if x.strip()]
        except ValueError:
            return []

    @property
    def is_subtask(self) -> bool:
        return self.parent_id > 0
