# ◈ todoc

**The most powerful terminal task manager.**  
Fast, beautiful, and built entirely in your shell.

```
╭──────────────────────────────────────────────────────────────╮
│                     ◈  T O D O C                             │
│           the most powerful terminal task manager            │
╰──────────────────────────────────────────────────────────────╯

  #   Priority     St   Task                    Tags
 ──────────────────────────────────────────────────────────────
  1  ┃ CRIT ┃  ○  Ship v2.0 release         due:Mon #release
  2  ┃ HIGH ┃  ○  Fix login bug              #bug #backend
  3  ┃ MED  ┃  ✓  Write unit tests           #dev
  4  ┃ LOW  ┃  ○  Update docs                #docs

  1/4  done  ·  3 pending  ·  25%  ████░░░░░░░░░░░░░░░░░░░░░░
```

[![PyPI version](https://img.shields.io/pypi/v/todoc)](https://pypi.org/project/todoc/)
[![Python](https://img.shields.io/pypi/pyversions/todoc)](https://pypi.org/project/todoc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-anikchand461%2Ftodoc-black?logo=github)](https://github.com/anikchand461/todoc)
[![Website](https://img.shields.io/badge/Website-todocpy.vercel.app-blue)](https://todocpy.vercel.app)

---

## Installation

```bash
pip install todoc
```

Requires Python 3.10+.

### Optional extras

```bash
pip install todoc[macos]      # rich macOS notifications
pip install todoc[windows]    # Windows desktop notifications
pip install todoc[dev]        # pytest + dev tools
```

> ⚠️ **macOS notification setup:** After `pip install todoc[macos]`:
>
> ```bash
> brew install terminal-notifier
> ```
>
> Then go to **System Settings → Notifications → terminal-notifier** and enable notifications.

---

## Quick Start

```bash
todoc add "Fix login bug" -p high --tags "#bug #backend"
todoc list
todoc done 1
todoc tui          # interactive dashboard
todoc help         # full reference
todoc -s           # compact command summary
```

---

## All Commands

| Command         | What it does                                   |
| --------------- | ---------------------------------------------- |
| `add`           | Create a new task                              |
| `list`          | Show all tasks (done + pending)                |
| `done`          | Mark one or more tasks complete                |
| `undone`        | Reopen a completed task                        |
| `delete`        | Remove a task permanently                      |
| `edit`          | Change any field of a task                     |
| `show`          | Full detail for one task (includes subtasks)   |
| `search`        | Full-text search — supports `--fuzzy` matching |
| `sort`          | Display list sorted by a field                 |
| `stats`         | Beautiful statistics dashboard                 |
| `clear`         | Remove all completed tasks                     |
| `reset`         | ⚠️ Wipe ALL tasks permanently                  |
| `export`        | Save tasks to JSON or CSV                      |
| `import`        | Load tasks from a JSON backup                  |
| `subtask`       | Add a subtask under an existing task           |
| `status`        | Move a task between Kanban columns             |
| `board`         | Kanban board — To Do / In Progress / Done      |
| `tui`           | Interactive TUI dashboard (keyboard-driven)    |
| `notify`        | Send desktop notification for urgent tasks     |
| `daemon`        | Background auto-notification scheduler         |
| `push`          | Sync local tasks → Notion                      |
| `pull`          | Sync Notion tasks → local                      |
| `notion-logout` | Remove saved Notion credentials                |
| `help`          | Full command reference                         |

---

## Usage

### Adding tasks

```bash
todoc add "Buy groceries"
todoc add "Ship v2" -p critical
todoc add "Fix auth" -p high --tags "#bug due:fri @alice"
```

**Priority levels:**

| Level      | Chip              | When to use              |
| ---------- | ----------------- | ------------------------ |
| `critical` | `[ CRIT ]` red    | Drop everything          |
| `high`     | `[ HIGH ]` red    | Needs to be done soon    |
| `medium`   | `[ MED  ]` yellow | Normal tasks _(default)_ |
| `low`      | `[ LOW  ]` green  | Someday / nice to have   |

### Listing & filtering

```bash
todoc list                        # all tasks
todoc list --pending              # only unfinished
todoc list --completed            # only finished
todoc list -p high                # filter by priority
todoc list --by priority          # sort: critical → low
todoc list --by priority --desc   # reverse sort
```

### Completing tasks

```bash
todoc done 3            # mark #3 done
todoc done 1 4 7        # bulk-complete three at once
todoc undone 3          # reopen #3
```

### Editing tasks

Only passed flags are updated — everything else stays as-is.

```bash
todoc edit 3 -p critical
todoc edit 3 --tags "#urgent waiting-for-review"
todoc edit 3 -d "New description" -p high
todoc edit 3 --status doing
todoc edit 3 --tags ""            # clear a field
```

### Subtasks

```bash
todoc subtask 1 "Write unit tests" -p medium
todoc subtask 1 "Update changelog" -p low
todoc show 1          # shows parent + all subtasks
```

Deleting a parent also removes all its subtasks.

### Fuzzy Search

```bash
todoc search "auth"               # exact match
todoc search "lgin" --fuzzy       # finds "Fix login bug"
todoc search "shp v2" --fuzzy     # finds "Ship v2.0 release"
```

### Kanban Board

```bash
todoc board                  # view all columns
todoc status 3 doing         # move #3 to In Progress
todoc status 3 done          # move #3 to Done
todoc status 3 todo          # move back to To Do
```

### Interactive TUI

```bash
todoc tui    # requires: pip install textual
```

| Key     | Action                        |
| ------- | ----------------------------- |
| `a`     | Add a new task                |
| `e`     | Edit selected task            |
| `Space` | Toggle done / pending         |
| `n`     | Cycle status: todo→doing→done |
| `d`     | Delete selected task          |
| `/`     | Fuzzy search                  |
| `r`     | Refresh                       |
| `q`     | Quit                          |

### Statistics

```bash
todoc stats    # counts, progress bar, priority & status breakdowns
```

### Removing tasks

```bash
todoc delete 5 --force     # delete immediately
todoc clear                # remove all completed tasks
todoc reset --force        # ⚠ wipe everything
```

> **Tip:** Run `todoc export -o backup.json` before `reset`.

### Export & Import

```bash
todoc export -o backup.json
todoc export --format csv -o tasks.csv
todoc import backup.json
```

---

## Desktop Notifications

Notifications fire automatically at **4h, 6h, 9h, 12h, 18h, 24h** for every pending task — no terminal needed.

```bash
todoc daemon start     # install & start (run once after install)
todoc daemon status    # check if running
todoc daemon stop      # uninstall
todoc notify           # fire manually right now
```

| Platform | Mechanism      | Requires                         |
| -------- | -------------- | -------------------------------- |
| macOS    | launchd        | `brew install terminal-notifier` |
| Linux    | systemd / cron | `notify-send` (usually built-in) |
| Windows  | Task Scheduler | Run as Administrator             |

Logs: `~/.todoc/daemon.log`

---

## Notion Sync

Sync your tasks to a Notion page with `todoc push` and pull them back with `todoc pull`. Credentials are saved once and reused forever.

### Setup (one time)

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration** → name it `todoc` → copy the **Internal Integration Token**
2. Open the Notion page you want to sync to → **"..." menu** → **Connect to** → select `todoc`
3. Copy the **Page ID** from the URL:
   ```
   notion.so/My-Page-abc123def456abc123def456abc12345
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 32 chars
   ```

### Usage

```bash
todoc push                 # sync local tasks → Notion
todoc pull                 # sync Notion tasks → local (backs up first)
todoc push --reset         # update saved credentials, then push
todoc notion-logout        # remove saved credentials
```

> **Note:** `todoc pull` automatically backs up your local tasks to `~/.todoc/tasks_before_pull.json` before overwriting.

Credentials are stored at `~/.todoc/notion_creds.json`.

---

## Help

```bash
todoc help              # full per-command reference with examples
todoc -s                # compact one-screen command summary
todoc <command> --help  # flag list for any single command
```

---

## Data Storage

```
~/.todoc/
├── tasks.json
├── notion_creds.json       # saved after first todoc push / pull
├── tasks_before_pull.json  # auto-backup created before todoc pull
├── daemon.log
└── daemon-error.log
```

No accounts required for local use. Notion sync is opt-in.

---

## Project Structure

```
todoc/
├── pyproject.toml
├── README.md
└── todoc/
    ├── __init__.py
    ├── __main__.py
    ├── exceptions.py
    ├── cli/
    │   ├── main.py        # CLI entry point
    │   ├── formatter.py   # Rich display layer
    │   ├── tui.py         # Textual TUI dashboard
    │   ├── board.py       # Kanban board renderer
    │   └── daemon.py      # background notification daemon
    ├── core/
    │   ├── models.py      # Task dataclass
    │   └── service.py     # business logic + fuzzy search
    ├── storage/
    │   └── repository.py  # JSON read/write
    └── sync/
        └── notion.py      # Notion API integration (push / pull)
```

---

## License

MIT — Built with [Typer](https://typer.tiangolo.com/), [Rich](https://github.com/Textualize/rich), and [Textual](https://textual.textualize.io/).
