from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Task:
    id:          int
    description: str
    done:        bool = False
    priority:    str  = "medium"   # low | medium | high | critical
    tags:        str  = ""         # free-form info — user puts whatever they want here
    created_at:  str  = ""         # set automatically on creation

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Backward-compatible — drops legacy fields, fills missing ones."""
        known = {f for f in cls.__dataclass_fields__}      # type: ignore[attr-defined]
        data.setdefault("priority",   "medium")
        data.setdefault("tags",       "")
        data.setdefault("created_at", "")
        return cls(**{k: v for k, v in data.items() if k in known})
