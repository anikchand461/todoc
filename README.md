# ◈ todoc

**The most powerful terminal task manager.**  
Fast, beautiful, and built entirely in your shell.

```
╭─────────────────────────────────────────────────────────╮
│                   ◈  T O D O C                          │
│          the most powerful terminal task manager        │
╰─────────────────────────────────────────────────────────╯

  #   Priority     Task                    Tags
 ─────────────────────────────────────────────────────────
  1  ┃ HIGH ┃  ○  Fix login bug           #bug #backend
  2  ┃ MED  ┃  ○  Write unit tests        #dev
  3  ┃ LOW  ┃  ✓  Update README           #docs

  2/3  done  ·  1 pending  ·  67%  ████████████░░░░░░░░
```

---

## Installation

```bash
pip install todoc
```

Requires Python 3.10+.

---

## Quick Start

```bash
# Add your first task
todoc add "Fix login bug" -p high --tags "#bug #backend"

# See everything
todoc list

# Mark it done
todoc done 1

# Get help
todoc help
todoc --summary        # compact one-screen command list
```

---

## All Commands

| Command  | What it does               |
| -------- | -------------------------- |
| `add`    | Create a new task          |
| `list`   | Show all tasks             |
| `done`   | Mark task(s) complete      |
| `undone` | Reopen a completed task    |
| `delete` | Remove a task forever      |
| `edit`   | Change any field           |
| `show`   | Full detail for one task   |
| `search` | Find tasks by keyword      |
| `sort`   | List sorted by a field     |
| `stats`  | Completion statistics      |
| `clear`  | Remove all done tasks      |
| `reset`  | Wipe ALL tasks permanently |
| `export` | Save tasks to JSON or CSV  |
| `import` | Load tasks from JSON file  |
| `help`   | Full command reference     |

---

## Usage

### Adding tasks

```bash
# Minimal
todoc add "Buy groceries"

# With priority
todoc add "Ship v2" -p critical

# With tags — the Tags column is free-form, put anything there
todoc add "Fix auth" -p high --tags "#bug due:fri @alice"
todoc add "Research" --tags "see notion.so/abc #reading"
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
todoc list                        # all tasks (done + pending)
todoc list --pending              # only unfinished tasks
todoc list --completed            # only finished tasks
todoc list -p high                # filter by priority
todoc list --by priority          # sort: critical → low
todoc list --by priority --desc   # sort: low → critical
```

### Viewing a single task

```bash
todoc show 3        # full detail panel — all fields visible
```

### Completing tasks

```bash
todoc done 3          # mark task #3 done
todoc done 1 4 7      # bulk-complete three tasks at once
todoc undone 3        # reopen task #3
```

### Editing tasks

Only the flags you pass are updated — everything else stays as-is.

```bash
todoc edit 3 -p critical                         # escalate priority
todoc edit 3 --tags "#done waiting-for-review"   # update tags
todoc edit 3 -d "New description" -p high        # two fields at once
todoc edit 3 --tags ""                           # clear the tags field
```

### Searching

```bash
todoc search "auth"       # matches description and tags
todoc search "#bug"       # find all tasks tagged #bug
```

### Sorting

```bash
todoc sort --by priority        # critical tasks first
todoc sort --by created         # oldest first
todoc sort --by priority --desc # lowest priority first
```

### Statistics

```bash
todoc stats     # total / done / pending + breakdown by priority
```

### Removing tasks

```bash
todoc delete 5             # delete task #5 (asks for confirmation)
todoc delete 5 --force     # delete immediately, no prompt

todoc clear                # remove all completed tasks
todoc reset                # ⚠ wipe EVERYTHING — done and pending
todoc reset --force        # wipe immediately, no prompt
```

> **Tip:** Run `todoc export -o backup.json` before `reset` to keep a copy.

### Export & Import

```bash
# Export
todoc export                          # print JSON to stdout
todoc export > backup.json            # redirect to file
todoc export -o backup.json           # same, explicit flag
todoc export --format csv -o tasks.csv  # export as CSV

# Import
todoc import backup.json              # restore from backup
```

The JSON export preserves every field and is ideal for backups.  
The CSV export opens directly in Excel / Google Sheets.

---

## Help

```bash
todoc --help          # full command reference (same as todoc help)
todoc -h              # shorthand
todoc --summary       # compact one-screen command + example list
todoc -s              # shorthand

todoc help            # full reference
todoc help --summary  # compact list

todoc <command> --help  # raw flag list for any single command
```

---

## Data Storage

Tasks are stored locally as a JSON file at:

```
~/.todoc/tasks.json
```

No accounts, no sync, no cloud — your data stays on your machine.

---

## License

MIT

---

_Built with [Typer](https://typer.tiangolo.com/) and [Rich](https://github.com/Textualize/rich)._

