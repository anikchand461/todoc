"""todoc · sync/notion.py — Notion sync (push / pull) with local API key storage."""

from __future__ import annotations

import json
import stat
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────

_TODOC_DIR  = Path.home() / ".todoc"
_CREDS_FILE = _TODOC_DIR / "notion_creds.json"

NOTION_VERSION = "2022-06-28"
NOTION_API     = "https://api.notion.com/v1"


# ──────────────────────────────────────────────────────────
# Credential helpers
# ──────────────────────────────────────────────────────────

def _ensure_dir() -> None:
    _TODOC_DIR.mkdir(parents=True, exist_ok=True)


def load_credentials() -> Optional[dict]:
    """Return stored {api_key, page_id} or None if not set."""
    if not _CREDS_FILE.exists():
        return None
    try:
        with open(_CREDS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("api_key") and data.get("page_id"):
            return data
    except Exception:
        pass
    return None


def save_credentials(api_key: str, page_id: str) -> None:
    """Persist credentials to ~/.todoc/notion_creds.json (owner-read-only)."""
    _ensure_dir()
    payload = {"api_key": api_key, "page_id": page_id}
    with open(_CREDS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    _CREDS_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)


def clear_credentials() -> None:
    """Remove saved credentials."""
    if _CREDS_FILE.exists():
        _CREDS_FILE.unlink()


# ──────────────────────────────────────────────────────────
# Low-level API helpers (stdlib only, no requests needed)
# ──────────────────────────────────────────────────────────

def _headers(api_key: str) -> dict:
    return {
        "Authorization":  f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type":   "application/json",
    }


def _req(method: str, url: str, api_key: str, body: Optional[dict] = None) -> dict:
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=_headers(api_key), method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(raw).get("message", raw)
        except Exception:
            msg = raw
        raise NotionError(f"HTTP {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise NotionError(f"Network error: {e.reason}") from e


class NotionError(Exception):
    """Raised on Notion API failures."""


# ──────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────

_DB_TITLE = "todoc tasks"


def _find_or_create_database(api_key: str, page_id: str) -> str:
    """Search for existing todoc database in the page; create if missing. Returns DB ID."""
    body = {
        "filter": {"value": "database", "property": "object"},
        "query": _DB_TITLE,
    }
    result = _req("POST", f"{NOTION_API}/search", api_key, body)
    for obj in result.get("results", []):
        if obj.get("object") == "database":
            title_parts = obj.get("title", [])
            title = "".join(p.get("plain_text", "") for p in title_parts)
            if title.lower() == _DB_TITLE.lower():
                parent = obj.get("parent", {})
                if parent.get("page_id", "").replace("-", "") == page_id.replace("-", ""):
                    return obj["id"]

    # Create fresh database
    schema = {
        "Name":      {"title": {}},
        "Done":      {"checkbox": {}},
        "Priority":  {"select": {"options": [
            {"name": "critical", "color": "red"},
            {"name": "high",     "color": "orange"},
            {"name": "medium",   "color": "yellow"},
            {"name": "low",      "color": "green"},
        ]}},
        "Tags":      {"rich_text": {}},
        "Status":    {"select": {"options": [
            {"name": "todo",  "color": "gray"},
            {"name": "doing", "color": "blue"},
            {"name": "done",  "color": "green"},
        ]}},
        "TaskID":    {"number": {}},
        "ParentID":  {"number": {}},
        "CreatedAt": {"rich_text": {}},
    }
    body = {
        "parent":     {"type": "page_id", "page_id": page_id},
        "title":      [{"type": "text", "text": {"content": _DB_TITLE}}],
        "properties": schema,
    }
    result = _req("POST", f"{NOTION_API}/databases", api_key, body)
    return result["id"]


# ──────────────────────────────────────────────────────────
# Row ↔ Task conversion
# ──────────────────────────────────────────────────────────

def _task_to_properties(task) -> dict:
    return {
        "Name":      {"title":     [{"text": {"content": task.description}}]},
        "Done":      {"checkbox":  task.done},
        "Priority":  {"select":    {"name": task.priority or "medium"}},
        "Tags":      {"rich_text": [{"text": {"content": task.tags or ""}}]},
        "Status":    {"select":    {"name": task.status or "todo"}},
        "TaskID":    {"number":    task.id},
        "ParentID":  {"number":    task.parent_id or 0},
        "CreatedAt": {"rich_text": [{"text": {"content": task.created_at or ""}}]},
    }


def _properties_to_dict(props: dict) -> dict:
    def _text(p):
        parts = p.get("rich_text") or p.get("title") or []
        return "".join(x.get("plain_text", "") for x in parts)

    return {
        "description": _text(props.get("Name",  {})),
        "done":        props.get("Done",     {}).get("checkbox", False),
        "priority":    (props.get("Priority", {}).get("select") or {}).get("name", "medium"),
        "tags":        _text(props.get("Tags",   {})),
        "status":      (props.get("Status",   {}).get("select") or {}).get("name", "todo"),
        "id":          int(props.get("TaskID",   {}).get("number") or 0),
        "parent_id":   int(props.get("ParentID", {}).get("number") or 0),
        "created_at":  _text(props.get("CreatedAt", {})),
    }


# ──────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────

def verify_api_key(api_key: str) -> bool:
    """Return True if the key authenticates successfully."""
    try:
        _req("GET", f"{NOTION_API}/users/me", api_key)
        return True
    except NotionError:
        return False


def push_tasks(tasks: list, api_key: str, page_id: str) -> dict:
    """
    Full-replace sync: archive all existing Notion rows, then upload all local tasks.
    Returns {"pushed": N, "db_id": "..."}
    """
    db_id = _find_or_create_database(api_key, page_id)

    # Collect existing page IDs
    existing: list[str] = []
    has_more, cursor = True, None
    while has_more:
        body: dict = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        result   = _req("POST", f"{NOTION_API}/databases/{db_id}/query", api_key, body)
        existing += [p["id"] for p in result.get("results", [])]
        has_more  = result.get("has_more", False)
        cursor    = result.get("next_cursor")

    # Archive them
    for pid in existing:
        _req("PATCH", f"{NOTION_API}/pages/{pid}", api_key, {"archived": True})

    # Upload fresh
    for task in tasks:
        _req("POST", f"{NOTION_API}/pages", api_key, {
            "parent":     {"database_id": db_id},
            "properties": _task_to_properties(task),
        })

    return {"pushed": len(tasks), "db_id": db_id}


def pull_tasks(api_key: str, page_id: str) -> list[dict]:
    """
    Fetch all non-archived rows from the Notion database.
    Returns a list of dicts compatible with Task.from_dict().
    """
    db_id = _find_or_create_database(api_key, page_id)

    rows: list[dict] = []
    has_more, cursor = True, None
    while has_more:
        body: dict = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        result = _req("POST", f"{NOTION_API}/databases/{db_id}/query", api_key, body)
        for page in result.get("results", []):
            if not page.get("archived"):
                row = _properties_to_dict(page.get("properties", {}))
                if row["id"] > 0 and row["description"]:
                    rows.append(row)
        has_more = result.get("has_more", False)
        cursor   = result.get("next_cursor")

    rows.sort(key=lambda r: r["id"])
    return rows
