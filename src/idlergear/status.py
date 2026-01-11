"""Project status dashboard - unified view of tasks, notes, runs, and git."""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


from idlergear.backends.registry import get_backend
from idlergear.schema import IdlerGearSchema


@dataclass
class ProjectStatus:
    """Complete project status snapshot."""

    # Task counts
    tasks_open: int
    tasks_high_priority: int
    tasks_recent: list[dict[str, Any]]

    # Notes
    notes_total: int
    notes_recent: list[dict[str, Any]]

    # Runs
    runs_active: int
    runs_details: list[dict[str, Any]]

    # Git status
    git_uncommitted: int
    git_files: list[dict[str, str]]  # {status: 'M', path: 'file.py'}
    git_branch: str | None
    git_last_commit: str | None

    # Project info
    project_name: str | None
    last_release: str | None

    # Daemon/Agents
    daemon_running: bool = False
    daemon_pid: int | None = None
    agents_count: int = 0
    agents_list: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "tasks": {
                "open": self.tasks_open,
                "high_priority": self.tasks_high_priority,
                "recent": self.tasks_recent,
            },
            "notes": {"total": self.notes_total, "recent": self.notes_recent},
            "runs": {"active": self.runs_active, "details": self.runs_details},
            "git": {
                "uncommitted": self.git_uncommitted,
                "files": self.git_files,
                "branch": self.git_branch,
                "last_commit": self.git_last_commit,
            },
            "project": {"name": self.project_name, "last_release": self.last_release},
            "daemon": {
                "running": self.daemon_running,
                "pid": self.daemon_pid,
                "agents": self.agents_count,
                "agents_list": self.agents_list,
            },
        }

    def summary(self) -> str:
        """One-line summary."""
        parts = []

        if self.tasks_open > 0:
            parts.append(f"{self.tasks_open} open tasks")
        if self.notes_total > 0:
            parts.append(f"{self.notes_total} notes")
        if self.runs_active > 0:
            parts.append(f"{self.runs_active} runs active")
        if self.git_uncommitted > 0:
            parts.append(f"{self.git_uncommitted} uncommitted files")
        if self.agents_count > 0:
            parts.append(f"{self.agents_count} agents")

        if not parts:
            return "All clear"

        return ", ".join(parts)


def get_project_status() -> ProjectStatus:
    """Gather complete project status."""
    schema = IdlerGearSchema(root=Path.cwd())

    # Tasks
    task_backend = get_backend("task")
    tasks = task_backend.list()
    open_tasks = [t for t in tasks if t.get("state") == "open"]
    high_priority_tasks = [
        t for t in open_tasks if t.get("priority") in ["high", "critical"]
    ]

    # Sort by priority, then created date
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, None: 4}

    def task_sort_key(t: dict[str, Any]) -> tuple[int, str]:
        priority = t.get("priority", "").strip() if t.get("priority") else None
        return (priority_order.get(priority, 4), t.get("created", ""))

    open_tasks.sort(key=task_sort_key)
    recent_tasks = open_tasks[:5]  # Top 5 tasks

    # Notes
    note_backend = get_backend("note")
    notes = note_backend.list()

    # Sort by created date (newest first)
    notes.sort(key=lambda n: n.get("created", ""), reverse=True)
    recent_notes = notes[:5]  # Most recent 5 notes

    # Runs (if backend exists)
    try:
        run_backend = get_backend("run")
        runs = run_backend.list()
        active_runs = [r for r in runs if r.get("status") == "running"]
    except ValueError:
        # Run backend not configured yet
        runs = []
        active_runs = []

    # Git status
    git_files, git_branch, git_last_commit = get_git_status()

    # Project info
    project_name = schema.root.name if schema.root else None
    last_release = get_last_release()

    # Daemon/Agent status
    daemon_running, daemon_pid, agents_list = get_daemon_status(schema)

    return ProjectStatus(
        tasks_open=len(open_tasks),
        tasks_high_priority=len(high_priority_tasks),
        tasks_recent=recent_tasks,
        notes_total=len(notes),
        notes_recent=recent_notes,
        runs_active=len(active_runs),
        runs_details=active_runs,
        git_uncommitted=len(git_files),
        git_files=git_files,
        git_branch=git_branch,
        git_last_commit=git_last_commit,
        project_name=project_name,
        last_release=last_release,
        daemon_running=daemon_running,
        daemon_pid=daemon_pid,
        agents_count=len(agents_list) if agents_list else 0,
        agents_list=agents_list,
    )


def get_daemon_status(
    schema: IdlerGearSchema,
) -> tuple[bool, int | None, list[dict[str, Any]] | None]:
    """Get daemon status and agent list.

    Returns: (daemon_running, daemon_pid, agents_list)
    """
    idlergear_dir = schema.root / ".idlergear" if schema.root else None
    if not idlergear_dir or not idlergear_dir.exists():
        return False, None, None

    # Check daemon PID file
    pid_file = idlergear_dir / "daemon.pid"
    daemon_running = False
    daemon_pid = None

    if pid_file.exists():
        try:
            import os

            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            daemon_running = True
            daemon_pid = pid
        except (ValueError, ProcessLookupError, PermissionError):
            pass

    # Read agent presence files
    agents_dir = idlergear_dir / "agents"
    agents_list = []

    if agents_dir.exists():
        for presence_file in agents_dir.glob("*.json"):
            # Skip the daemon's internal registry file
            if presence_file.name == "agents.json":
                continue
            try:
                data = json.loads(presence_file.read_text())
                agents_list.append(data)
            except (json.JSONDecodeError, OSError):
                continue

    return daemon_running, daemon_pid, agents_list if agents_list else None


def get_git_status() -> tuple[list[dict[str, str]], str | None, str | None]:
    """Get git status: (files, branch, last_commit)."""
    try:
        # Check if in a git repo
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            check=True,
            text=True,
        )

        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

        # Get last commit
        commit_result = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            capture_output=True,
            text=True,
        )
        last_commit = (
            commit_result.stdout.strip() if commit_result.returncode == 0 else None
        )

        # Get status
        status_result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
        )

        if status_result.returncode != 0:
            return [], branch, last_commit

        files = []
        for line in status_result.stdout.rstrip("\n").split("\n"):
            if not line:
                continue
            # Format: "XY filename" where X is staged, Y is unstaged
            # Examples: " M file.txt", "?? new.txt", "A  added.txt"
            # XY is always 2 chars, then space, then filename
            if len(line) < 4:
                continue
            status = line[:2]
            filename = line[3:]  # Skip "XY " to get filename
            files.append({"status": status, "path": filename})

        return files, branch, last_commit

    except (subprocess.CalledProcessError, FileNotFoundError):
        return [], None, None


def get_last_release() -> str | None:
    """Get the last git tag (release)."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None


def format_detailed_status(status: ProjectStatus) -> str:
    """Format detailed status dashboard."""
    lines = []

    # Header
    project_title = status.project_name or "Project"
    lines.append(f"=== Status: {project_title} ===")
    lines.append("")

    # Tasks
    if status.tasks_open > 0:
        lines.append(f"Tasks ({status.tasks_open} open)")
        for task in status.tasks_recent:
            priority = task.get("priority", "")
            priority_tag = f"[{priority}]" if priority else ""
            title = task.get("title", "Untitled")
            task_id = task.get("id", "?")
            lines.append(f"  #{task_id} {priority_tag} {title}")
        lines.append("")
    else:
        lines.append("Tasks: None open")
        lines.append("")

    # Notes
    if status.notes_total > 0:
        lines.append(f"Notes ({status.notes_total} total, showing recent)")
        for note in status.notes_recent:
            content = note.get("content", "")
            # Truncate to first line, max 60 chars
            first_line = content.split("\n")[0]
            if len(first_line) > 60:
                first_line = first_line[:57] + "..."

            tags = note.get("tags", [])
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f'  - "{first_line}"{tag_str}')
        lines.append("")
    else:
        lines.append("Notes: None")
        lines.append("")

    # Runs
    if status.runs_active > 0:
        lines.append(f"Runs ({status.runs_active} active)")
        for run in status.runs_details:
            name = run.get("name", "unnamed")
            # Calculate runtime if started time available
            started = run.get("started")
            runtime = ""
            if started:
                try:
                    start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    elapsed = datetime.now() - start_dt.replace(tzinfo=None)
                    minutes = int(elapsed.total_seconds() / 60)
                    runtime = f" (running {minutes}m)"
                except (ValueError, TypeError):
                    pass

            lines.append(f"  ● {name}{runtime}")
        lines.append("")
    else:
        lines.append("Runs: None active")
        lines.append("")

    # Daemon/Agents
    if status.daemon_running:
        agent_info = (
            f", {status.agents_count} agents" if status.agents_count > 0 else ""
        )
        lines.append(f"Daemon: Running (PID {status.daemon_pid}{agent_info})")
        if status.agents_list:
            for agent in status.agents_list[:5]:  # Show max 5 agents
                agent_id = agent.get("agent_id", "unknown")
                agent_type = agent.get("agent_type", "unknown")
                lines.append(f"  ● {agent_id} ({agent_type})")
            if len(status.agents_list) > 5:
                lines.append(f"  ... and {len(status.agents_list) - 5} more")
        lines.append("")
    else:
        lines.append("Daemon: Not running")
        lines.append("")

    # Git
    if status.git_uncommitted > 0:
        lines.append(f"Git ({status.git_uncommitted} uncommitted)")
        for file in status.git_files[:10]:  # Show max 10 files
            git_status = file["status"]
            path = file["path"]
            lines.append(f"  {git_status} {path}")
        if len(status.git_files) > 10:
            lines.append(f"  ... and {len(status.git_files) - 10} more")
        lines.append("")
    else:
        lines.append("Git: Working tree clean")
        lines.append("")

    # Footer
    if status.git_branch:
        lines.append(f"Branch: {status.git_branch}")
    if status.git_last_commit:
        lines.append(f"Last commit: {status.git_last_commit}")
    if status.last_release:
        lines.append(f"Last release: {status.last_release}")

    return "\n".join(lines)
