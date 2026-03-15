"""
todoc · daemon.py
Cross-platform background notification daemon.

Automatically sends desktop notifications for pending tasks at:
  4h, 6h, 9h, 12h, 18h, 24h after a task is created and still pending.

Usage:
  todoc daemon start    ← install & start background daemon
  todoc daemon stop     ← stop and uninstall daemon
  todoc daemon status   ← check if running
  todoc daemon run      ← (internal) actually runs the check loop

Works on:
  macOS   → launchd  (~/.todoc/com.todoc.notify.plist)
  Windows → Task Scheduler (schtasks)
  Linux   → systemd user service  OR  cron fallback
"""
from __future__ import annotations

import os
import sys
import subprocess
import platform
from pathlib import Path


# ── Constants ────────────────────────────────────────────────

TODOC_DIR    = Path.home() / ".todoc"
LABEL        = "com.todoc.notify"
LOG_OUT      = str(TODOC_DIR / "daemon.log")
LOG_ERR      = str(TODOC_DIR / "daemon-error.log")

# Notification schedule: check every 30 minutes.
# The service.py threshold logic decides WHICH tasks to notify based on age.
CHECK_INTERVAL_MINUTES = 30


# ── Helpers ──────────────────────────────────────────────────

def _todoc_exe() -> str:
    """Return the absolute path to the todoc executable."""
    import shutil
    # Try shutil.which first (works if todoc is in PATH)
    found = shutil.which("todoc")
    if found:
        return found
    # Fallback: same directory as current Python executable
    candidate = Path(sys.executable).parent / "todoc"
    if candidate.exists():
        return str(candidate)
    # Windows: .exe extension
    candidate_exe = Path(sys.executable).parent / "todoc.exe"
    if candidate_exe.exists():
        return str(candidate_exe)
    raise RuntimeError(
        "Cannot find todoc executable. Make sure `pip install -e .` was run "
        "and todoc is in your PATH."
    )


def _print(msg: str, ok: bool = True) -> None:
    icon = "✓" if ok else "✗"
    print(f"  {icon}  {msg}")


# ── macOS — launchd ──────────────────────────────────────────

PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"

def _macos_plist(todoc: str) -> str:
    interval = CHECK_INTERVAL_MINUTES * 60  # launchd uses seconds
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{todoc}</string>
        <string>daemon</string>
        <string>run</string>
    </array>

    <!-- Run every {CHECK_INTERVAL_MINUTES} minutes -->
    <key>StartInterval</key>
    <integer>{interval}</integer>

    <!-- Also run immediately when loaded -->
    <key>RunAtLoad</key>
    <true/>

    <!-- Keep alive — relaunch if it crashes -->
    <key>KeepAlive</key>
    <false/>

    <key>StandardOutPath</key>
    <string>{LOG_OUT}</string>
    <key>StandardErrorPath</key>
    <string>{LOG_ERR}</string>
</dict>
</plist>
"""

def macos_start() -> None:
    todoc = _todoc_exe()
    TODOC_DIR.mkdir(exist_ok=True)

    # Write plist
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(_macos_plist(todoc))
    _print(f"Plist written → {PLIST_PATH}")

    # Unload first (ignore errors if not loaded)
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)],
                   capture_output=True)

    # Load
    result = subprocess.run(["launchctl", "load", str(PLIST_PATH)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        _print(f"launchctl load failed: {result.stderr.strip()}", ok=False)
        return

    _print(f"Daemon loaded — runs every {CHECK_INTERVAL_MINUTES} min")
    _print(f"Logs → {LOG_OUT}")
    _print("Notifications will fire at 4h, 6h, 9h, 12h, 18h, 24h for pending tasks")


def macos_stop() -> None:
    if not PLIST_PATH.exists():
        _print("Daemon is not installed", ok=False)
        return
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
    PLIST_PATH.unlink(missing_ok=True)
    _print("Daemon stopped and removed")


def macos_status() -> None:
    result = subprocess.run(
        ["launchctl", "list", LABEL],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        _print(f"Daemon is RUNNING  (label: {LABEL})")
        # Show last exit code from list output
        for line in result.stdout.splitlines():
            if "LastExitStatus" in line or "PID" in line:
                print(f"      {line.strip()}")
    else:
        _print("Daemon is NOT running", ok=False)
    print(f"\n  Logs:  {LOG_OUT}")
    print(f"  Errors: {LOG_ERR}")


# ── Linux — systemd user service (cron fallback) ─────────────

SYSTEMD_DIR     = Path.home() / ".config" / "systemd" / "user"
SERVICE_FILE    = SYSTEMD_DIR / "todoc-notify.service"
TIMER_FILE      = SYSTEMD_DIR / "todoc-notify.timer"

def _linux_service(todoc: str) -> str:
    return f"""[Unit]
Description=todoc notification daemon
After=default.target

[Service]
Type=oneshot
ExecStart={todoc} daemon run
StandardOutput=append:{LOG_OUT}
StandardError=append:{LOG_ERR}

[Install]
WantedBy=default.target
"""

def _linux_timer() -> str:
    return f"""[Unit]
Description=todoc notification timer — runs every {CHECK_INTERVAL_MINUTES} minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec={CHECK_INTERVAL_MINUTES}min
Persistent=true

[Install]
WantedBy=timers.target
"""

def linux_start() -> None:
    todoc = _todoc_exe()
    TODOC_DIR.mkdir(exist_ok=True)

    # Try systemd first
    if shutil.which("systemctl"):
        SYSTEMD_DIR.mkdir(parents=True, exist_ok=True)
        SERVICE_FILE.write_text(_linux_service(todoc))
        TIMER_FILE.write_text(_linux_timer())
        _print(f"Service written → {SERVICE_FILE}")

        cmds = [
            ["systemctl", "--user", "daemon-reload"],
            ["systemctl", "--user", "enable", "--now", "todoc-notify.timer"],
        ]
        for cmd in cmds:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                _print(f"{' '.join(cmd)} failed: {r.stderr.strip()}", ok=False)
                _linux_cron_fallback(todoc)
                return
        _print(f"systemd timer active — runs every {CHECK_INTERVAL_MINUTES} min")
    else:
        _linux_cron_fallback(todoc)


def _linux_cron_fallback(todoc: str) -> None:
    """Add a crontab entry as fallback when systemd is unavailable."""
    import shutil
    if not shutil.which("crontab"):
        _print("Neither systemd nor crontab found — cannot install daemon", ok=False)
        return
    cron_line = f"*/{CHECK_INTERVAL_MINUTES} * * * * {todoc} daemon run >> {LOG_OUT} 2>> {LOG_ERR}"
    # Read existing crontab
    existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing_cron = existing.stdout if existing.returncode == 0 else ""
    if cron_line in existing_cron:
        _print("Cron entry already exists")
        return
    # Remove old todoc entry if present
    lines = [l for l in existing_cron.splitlines() if "todoc daemon run" not in l]
    lines.append(cron_line)
    new_cron = "\n".join(lines) + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True)
    if proc.returncode == 0:
        _print(f"Cron entry added — runs every {CHECK_INTERVAL_MINUTES} min")
    else:
        _print(f"Cron install failed: {proc.stderr}", ok=False)


def linux_stop() -> None:
    import shutil
    if SERVICE_FILE.exists() or TIMER_FILE.exists():
        subprocess.run(["systemctl", "--user", "disable", "--now", "todoc-notify.timer"],
                       capture_output=True)
        SERVICE_FILE.unlink(missing_ok=True)
        TIMER_FILE.unlink(missing_ok=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        _print("systemd timer stopped and removed")
    else:
        # Remove cron entry
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if existing.returncode == 0:
            lines = [l for l in existing.stdout.splitlines()
                     if "todoc daemon run" not in l]
            subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n",
                           text=True, capture_output=True)
            _print("Cron entry removed")


def linux_status() -> None:
    import shutil
    if shutil.which("systemctl"):
        r = subprocess.run(["systemctl", "--user", "is-active", "todoc-notify.timer"],
                           capture_output=True, text=True)
        active = r.stdout.strip() == "active"
        _print(f"systemd timer: {'ACTIVE' if active else 'NOT active'}", ok=active)
    # Check cron
    existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    in_cron = "todoc daemon run" in existing.stdout
    if in_cron:
        _print("Cron entry: present")
    print(f"\n  Logs:  {LOG_OUT}")


# ── Windows — Task Scheduler ──────────────────────────────────

TASK_NAME = "todoc_notify"

def windows_start() -> None:
    todoc = _todoc_exe()
    TODOC_DIR.mkdir(exist_ok=True)

    # Delete existing task (ignore error)
    subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True,
    )

    # Create new task — runs every CHECK_INTERVAL_MINUTES minutes
    result = subprocess.run(
        [
            "schtasks", "/create",
            "/tn",  TASK_NAME,
            "/tr",  f'"{todoc}" daemon run',
            "/sc",  "minute",
            "/mo",  str(CHECK_INTERVAL_MINUTES),
            "/rl",  "HIGHEST",          # run with elevated rights
            "/f",                        # force overwrite
        ],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        _print(f"Task Scheduler entry created — runs every {CHECK_INTERVAL_MINUTES} min")
        _print("Notifications will fire at 4h, 6h, 9h, 12h, 18h, 24h for pending tasks")
    else:
        _print(f"Task Scheduler failed: {result.stderr.strip()}", ok=False)
        _print("Try running as Administrator", ok=False)


def windows_stop() -> None:
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        _print("Task Scheduler entry removed")
    else:
        _print("Task not found or already removed", ok=False)


def windows_status() -> None:
    result = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        _print(f"Task '{TASK_NAME}' is REGISTERED")
        for line in result.stdout.splitlines():
            if any(k in line for k in ("Status", "Next Run", "Last Run", "Last Result")):
                print(f"      {line.strip()}")
    else:
        _print(f"Task '{TASK_NAME}' is NOT registered", ok=False)


# ── Notification check logic (called by daemon run) ──────────

# Thresholds: notify if task has been pending for these many hours
NOTIFY_HOURS = [4, 9, 12, 18, 24]

def run_check() -> None:
    """
    The actual check — called every CHECK_INTERVAL_MINUTES by the OS scheduler.
    Fires notifications for tasks pending at 4h, 6h, 9h, 12h, 18h, 24h milestones.
    """
    from datetime import datetime
    TODOC_DIR.mkdir(exist_ok=True)

    # Import here to avoid circular imports
    from todoc.core.service     import _send_notification
    from todoc.storage.repository import TaskRepository
    from todoc.core.models      import Task

    repo  = TaskRepository()
    tasks = repo.get_all()
    now   = datetime.now()

    to_notify: list[tuple[Task, int]] = []   # (task, milestone_hours)

    for task in tasks:
        if task.done:
            continue
        if not task.created_at:
            continue

        try:
            created = datetime.strptime(task.created_at, "%Y-%m-%d %H:%M")
        except ValueError:
            continue

        age_hours = (now - created).total_seconds() / 3600

        # Find which milestone we're at (within a 30-min window)
        for milestone in NOTIFY_HOURS:
            if milestone <= age_hours < milestone + (CHECK_INTERVAL_MINUTES / 60):
                to_notify.append((task, milestone))
                break

    if not to_notify:
        return

    # Group into one notification
    lines = []
    for task, milestone in to_notify[:6]:
        pri   = task.priority.upper()
        lines.append(f"[{pri}] {task.description}  ({milestone}h pending)")
    if len(to_notify) > 6:
        lines.append(f"…and {len(to_notify) - 6} more")

    title = f"todoc · {len(to_notify)} task(s) still pending"
    body  = "\n".join(lines)

    _send_notification(title, body)

    # Log it
    ts = now.strftime("%Y-%m-%d %H:%M")
    with open(LOG_OUT, "a") as f:
        f.write(f"[{ts}] Notified {len(to_notify)} task(s)\n")
        for task, milestone in to_notify:
            f.write(f"  #{task.id} [{task.priority}] {task.description} ({milestone}h)\n")


# ── Public dispatch ───────────────────────────────────────────

import shutil   # needed by linux functions above

def start() -> None:
    p = platform.system()
    print()
    if p == "Darwin":
        macos_start()
    elif p == "Linux":
        linux_start()
    elif p == "Windows":
        windows_start()
    else:
        _print(f"Unsupported platform: {p}", ok=False)
    print()


def stop() -> None:
    p = platform.system()
    print()
    if p == "Darwin":
        macos_stop()
    elif p == "Linux":
        linux_stop()
    elif p == "Windows":
        windows_stop()
    else:
        _print(f"Unsupported platform: {p}", ok=False)
    print()


def status() -> None:
    p = platform.system()
    print()
    _print(f"Platform: {p}  ·  Check interval: every {CHECK_INTERVAL_MINUTES} min")
    _print(f"Notify milestones: {NOTIFY_HOURS} hours")
    print()
    if p == "Darwin":
        macos_status()
    elif p == "Linux":
        linux_status()
    elif p == "Windows":
        windows_status()
    else:
        _print(f"Unsupported platform: {p}", ok=False)
    print()
