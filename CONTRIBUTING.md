# Contributing to todoc

Thanks for your interest in contributing! `todoc` is a solo-built open-source project and every bit of help — bug reports, new ideas, code, or docs — genuinely matters. 🙌

---

## Table of Contents

- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Ways to Contribute](#ways-to-contribute)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Code Style](#code-style)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

---

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your change
4. **Make your changes** and test them
5. **Open a Pull Request**

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
    │   ├── main.py        # CLI entry point (Typer)
    │   ├── formatter.py   # Rich display layer
    │   ├── tui.py         # Textual TUI dashboard
    │   ├── board.py       # Kanban board renderer
    │   └── daemon.py      # Background notification daemon
    ├── core/
    │   ├── models.py      # Task dataclass
    │   └── service.py     # Business logic + fuzzy search
    └── storage/
        └── repository.py  # JSON read/write
```

Understanding this structure before diving in will save you a lot of time. Most feature work touches `cli/` and `core/`. Storage changes go through `repository.py`.

---

## Ways to Contribute

You don't need to write code to contribute. Here's what's always welcome:

- 🐛 **Bug reports** — something broken? Open an issue
- 💡 **Feature requests** — have an idea? Let's discuss it
- 📖 **Documentation** — fix typos, clarify examples, improve the README
- ✅ **Tests** — more coverage is always better
- 🔧 **Bug fixes** — pick up an open issue and fix it
- 🎨 **TUI / display improvements** — formatting, colors, layout tweaks via Rich or Textual
- 🖥️ **Platform-specific fixes** — daemon behavior on macOS, Linux, or Windows

---

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Install from source

```bash
git clone https://github.com/anikchand461/todoc
cd todoc
pip install -e .
```

### Install optional extras

```bash
pip install todoc[dev]        # pytest + dev tools
pip install todoc[macos]      # macOS notifications (if on Mac)
pip install todoc[windows]    # Windows notifications (if on Windows)
```

### Verify the install

```bash
todoc --version
todoc help
todoc add "Test task" -p high
todoc list
```

---

## Making Changes

### 1. Create a branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-you-are-fixing
```

### 2. Know where to make changes

| What you're changing            | Where to look                 |
| ------------------------------- | ----------------------------- |
| A CLI command                   | `todoc/cli/main.py`           |
| How tasks are displayed         | `todoc/cli/formatter.py`      |
| TUI dashboard                   | `todoc/cli/tui.py`            |
| Kanban board                    | `todoc/cli/board.py`          |
| Daemon / notifications          | `todoc/cli/daemon.py`         |
| Task model / data structure     | `todoc/core/models.py`        |
| Business logic, search, sorting | `todoc/core/service.py`       |
| Reading / writing tasks.json    | `todoc/storage/repository.py` |

### 3. Test manually

```bash
todoc add "Test task" -p critical --tags "#test"
todoc list
todoc done 1
todoc stats
todoc board
todoc tui        # if you changed TUI
todoc search "test" --fuzzy
```

Make sure existing commands still work as expected after your change.

### 4. Commit with a clear message

```bash
git commit -m "feat: add due date sorting to todoc list"
git commit -m "fix: daemon fails silently on Linux systemd"
git commit -m "docs: add Windows notification setup steps"
git commit -m "refactor: simplify fuzzy search scoring in service.py"
```

---

## Submitting a Pull Request

1. Push your branch to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a PR against the `main` branch of the original repo

3. In your PR description, include:
   - **What** you changed
   - **Why** (link to an issue if there is one)
   - **How to test** it manually
   - Any platform-specific notes (macOS / Linux / Windows) if relevant

4. Be responsive to review feedback — small follow-up commits are totally fine

---

## Code Style

- Follow the patterns already in the file you're editing
- Use descriptive variable names — clarity over cleverness
- Keep functions focused — one job per function
- If something isn't obvious, add a short comment
- Don't break existing command behavior without a good reason

No strict formatter enforced yet, but keeping things consistent makes reviews faster.

---

## Reporting Bugs

Open an issue and include:

- Your OS and Python version
- The exact command you ran
- What you expected to happen
- What actually happened
- Full error output or traceback if applicable
- Contents of `~/.todoc/daemon.log` if it's a daemon/notification issue

---

## Suggesting Features

Open an issue with an `enhancement` label and describe:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you considered

For bigger changes (new commands, TUI overhauls, storage format changes), please open an issue first before coding — so we can align before effort is spent.

---

## Data & Storage Notes

Tasks are stored locally at `~/.todoc/tasks.json`. If you're working on anything that touches the storage layer, make sure to test with both empty and populated task files, and verify that `todoc export` and `todoc import` still round-trip cleanly.

---

## Questions?

Open an issue or reach out directly on GitHub. Happy to help you get started. 🚀
