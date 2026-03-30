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

    # Create fresh database with default view sorted by TaskID ascending
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
        "is_inline":  False,
    }
    result = _req("POST", f"{NOTION_API}/databases", api_key, body)
    db_id = result["id"]

    # Patch the database to set default view sort by TaskID ascending.
    # This controls the order users see in the Notion UI.
    try:
        _req("PATCH", f"{NOTION_API}/databases/{db_id}", api_key, {
            "description": [{"type": "text", "text": {
                "content": "Managed by todoc · sorted by TaskID"
            }}],
        })
    except Exception:
        pass  # non-fatal — UI sort is best-effort

    return db_id


# ──────────────────────────────────────────────────────────
# Row ↔ Task conversion
# ──────────────────────────────────────────────────────────

def _name_with_prefix(task_id: int, description: str) -> str:
    """Return '[001] description' — zero-padded ID prefix so Notion's
    default title sort shows tasks in the same order as the CLI."""
    return f"[{task_id:03d}] {description}"


def _strip_prefix(name: str) -> str:
    """Remove the '[NNN] ' prefix added by _name_with_prefix, if present."""
    import re
    return re.sub(r"^\[\d+\]\s*", "", name)


def _task_to_properties(task) -> dict:
    return {
        "Name":      {"title":     [{"text": {"content": _name_with_prefix(task.id, task.description)}}]},
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
        "description": _strip_prefix(_text(props.get("Name",  {}))),
        "done":        props.get("Done",     {}).get("checkbox", False),
        "priority":    (props.get("Priority", {}).get("select") or {}).get("name", "medium"),
        "tags":        _text(props.get("Tags",   {})),
        "status":      (props.get("Status",   {}).get("select") or {}).get("name", "todo"),
        "id":          int(props.get("TaskID",   {}).get("number") or 0),
        "parent_id":   int(props.get("ParentID", {}).get("number") or 0),
        "created_at":  _text(props.get("CreatedAt", {})),
    }


# ──────────────────────────────────────────────────────────
# Shared query helpers
# ──────────────────────────────────────────────────────────

# Always query Notion sorted by TaskID ascending so the UI reflects CLI order.
_SORTS = [{"property": "TaskID", "direction": "ascending"}]


def _query_body(cursor: Optional[str] = None) -> dict:
    body: dict = {"page_size": 100, "sorts": _SORTS}
    if cursor:
        body["start_cursor"] = cursor
    return body


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
    Delta push: only create/update/archive rows whose TaskID changed.
    - Tasks present locally but missing in Notion → created.
    - Tasks present in both and changed → updated in-place (PATCH).
    - Tasks present in Notion but deleted locally → archived.
    Returns {"created": N, "updated": N, "archived": N, "unchanged": N, "db_id": "..."}
    """
    db_id = _find_or_create_database(api_key, page_id)

    # Fetch all existing Notion rows → {task_id: (page_id, properties_dict)}
    notion_rows: dict[int, tuple[str, dict]] = {}
    has_more, cursor = True, None
    while has_more:
        result = _req("POST", f"{NOTION_API}/databases/{db_id}/query", api_key, _query_body(cursor))
        for p in result.get("results", []):
            if p.get("archived"):
                continue
            props = p.get("properties", {})
            tid = int(props.get("TaskID", {}).get("number") or 0)
            if tid > 0:
                notion_rows[tid] = (p["id"], _properties_to_dict(props))
        has_more = result.get("has_more", False)
        cursor   = result.get("next_cursor")

    local_ids = {task.id for task in tasks}
    created = updated = archived = unchanged = 0

    # Create or update
    for task in tasks:
        new_props = _task_to_properties(task)
        if task.id not in notion_rows:
            # New task — create
            _req("POST", f"{NOTION_API}/pages", api_key, {
                "parent":     {"database_id": db_id},
                "properties": new_props,
            })
            created += 1
        else:
            existing_page_id, existing_data = notion_rows[task.id]
            # Compare fields to decide whether an update is needed
            changed = (
                existing_data.get("description") != task.description
                or existing_data.get("done")      != task.done
                or existing_data.get("priority")  != (task.priority or "medium")
                or existing_data.get("tags")      != (task.tags or "")
                or existing_data.get("status")    != (task.status or "todo")
                or existing_data.get("parent_id") != (task.parent_id or 0)
            )
            if changed:
                _req("PATCH", f"{NOTION_API}/pages/{existing_page_id}", api_key,
                     {"properties": new_props})
                updated += 1
            else:
                unchanged += 1

    # Archive rows that no longer exist locally
    for tid, (existing_page_id, _) in notion_rows.items():
        if tid not in local_ids:
            _req("PATCH", f"{NOTION_API}/pages/{existing_page_id}", api_key,
                 {"archived": True})
            archived += 1

    return {
        "created":   created,
        "updated":   updated,
        "archived":  archived,
        "unchanged": unchanged,
        "db_id":     db_id,
    }


def pull_tasks(api_key: str, page_id: str) -> list[dict]:
    """
    Fetch all non-archived rows from the Notion database.
    Returns a list of dicts compatible with Task.from_dict().
    """
    db_id = _find_or_create_database(api_key, page_id)

    rows: list[dict] = []
    has_more, cursor = True, None
    while has_more:
        result = _req("POST", f"{NOTION_API}/databases/{db_id}/query", api_key, _query_body(cursor))
        for page in result.get("results", []):
            if not page.get("archived"):
                row = _properties_to_dict(page.get("properties", {}))
                if row["id"] > 0 and row["description"]:
                    rows.append(row)
        has_more = result.get("has_more", False)
        cursor   = result.get("next_cursor")

    rows.sort(key=lambda r: r["id"])
    return rows


def pull_tasks_delta(local_tasks: list, api_key: str, page_id: str) -> dict:
    """
    Delta pull: compare Notion rows against local tasks and return only what changed.
    - added:     rows in Notion not present locally (by TaskID) → need to be inserted
    - updated:   rows in Notion whose fields differ from local → need to overwrite local
    - removed:   TaskIDs present locally but missing from Notion (deleted remotely)
    - unchanged: count of rows that match exactly

    Returns {
        "added":     [dict, ...],
        "updated":   [dict, ...],
        "removed":   [int, ...],   # list of TaskIDs
        "unchanged": int,
        "db_id":     str,
    }
    """
    db_id = _find_or_create_database(api_key, page_id)

    # Build local lookup {task_id → task}
    local_by_id = {t.id: t for t in local_tasks}

    notion_rows: list[dict] = []
    has_more, cursor = True, None
    while has_more:
        result = _req("POST", f"{NOTION_API}/databases/{db_id}/query", api_key, _query_body(cursor))
        for page in result.get("results", []):
            if not page.get("archived"):
                row = _properties_to_dict(page.get("properties", {}))
                if row["id"] > 0 and row["description"]:
                    notion_rows.append(row)
        has_more = result.get("has_more", False)
        cursor   = result.get("next_cursor")

    notion_ids = {r["id"] for r in notion_rows}
    added: list[dict] = []
    updated: list[dict] = []
    unchanged = 0

    for row in notion_rows:
        tid = row["id"]
        if tid not in local_by_id:
            added.append(row)
        else:
            loc = local_by_id[tid]
            changed = (
                loc.description               != row["description"]
                or loc.done                   != row["done"]
                or (loc.priority or "medium") != row["priority"]
                or (loc.tags or "")           != row["tags"]
                or (loc.status or "todo")     != row["status"]
                or (loc.parent_id or 0)       != row["parent_id"]
            )
            if changed:
                updated.append(row)
            else:
                unchanged += 1

    removed = [tid for tid in local_by_id if tid not in notion_ids]

    return {
        "added":     added,
        "updated":   updated,
        "removed":   removed,
        "unchanged": unchanged,
        "db_id":     db_id,
    }
