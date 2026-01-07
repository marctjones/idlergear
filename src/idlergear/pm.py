"""Process management MCP server for IdlerGear.

Provides process listing, management, and monitoring capabilities.
Integrates with IdlerGear's existing run system for background task management.
"""

import os
import platform
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any

import psutil

from idlergear import runs
from idlergear.config import find_idlergear_root


class ProcessManager:
    """Process management server for IdlerGear."""

    def __init__(self, project_path: Path | None = None):
        """Initialize process manager.

        Args:
            project_path: Project root path (defaults to current IdlerGear project)
        """
        self.project_path = project_path or find_idlergear_root()

    # ==== Process Listing ====

    def list_processes(
        self,
        filter_name: str | None = None,
        filter_user: str | None = None,
        sort_by: str = "cpu",
    ) -> list[dict[str, Any]]:
        """List running processes with optional filtering.

        Args:
            filter_name: Filter by process name (substring match)
            filter_user: Filter by username
            sort_by: Sort by 'cpu', 'memory', 'pid', or 'name'

        Returns:
            List of process info dicts
        """
        processes = []

        for proc in psutil.process_iter(
            ["pid", "name", "username", "cpu_percent", "memory_percent", "status"]
        ):
            try:
                info = proc.info
                # Apply filters
                if filter_name and filter_name.lower() not in info["name"].lower():
                    continue
                if filter_user and info["username"] != filter_user:
                    continue

                processes.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"],
                        "user": info["username"],
                        "cpu": round(info["cpu_percent"], 1),
                        "memory": round(info["memory_percent"], 1),
                        "status": info["status"],
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort
        sort_key = {
            "cpu": lambda p: p["cpu"],
            "memory": lambda p: p["memory"],
            "pid": lambda p: p["pid"],
            "name": lambda p: p["name"],
        }.get(sort_by, lambda p: p["cpu"])

        processes.sort(key=sort_key, reverse=True)
        return processes

    def get_process(self, pid: int) -> dict[str, Any] | None:
        """Get detailed information about a specific process.

        Args:
            pid: Process ID

        Returns:
            Process info dict or None if not found
        """
        try:
            proc = psutil.Process(pid)
            return {
                "pid": proc.pid,
                "name": proc.name(),
                "exe": proc.exe(),
                "cwd": proc.cwd(),
                "cmdline": proc.cmdline(),
                "user": proc.username(),
                "status": proc.status(),
                "cpu_percent": round(proc.cpu_percent(interval=0.1), 1),
                "memory_percent": round(proc.memory_percent(), 1),
                "memory_info": {
                    "rss": proc.memory_info().rss,
                    "vms": proc.memory_info().vms,
                },
                "num_threads": proc.num_threads(),
                "create_time": proc.create_time(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """Kill a process.

        Args:
            pid: Process ID
            force: Use SIGKILL instead of SIGTERM

        Returns:
            True if killed successfully
        """
        try:
            proc = psutil.Process(pid)
            if force:
                proc.kill()  # SIGKILL
            else:
                proc.terminate()  # SIGTERM
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    # ==== System Information ====

    def system_info(self) -> dict[str, Any]:
        """Get system information.

        Returns:
            System info dict with CPU, memory, disk usage
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(logical=False),
                "count_logical": psutil.cpu_count(logical=True),
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
            },
        }

    # ==== IdlerGear Run Integration ====

    def start_run(
        self, command: str, name: str | None = None, task_id: int | None = None
    ) -> dict[str, Any]:
        """Start a background run.

        Args:
            command: Command to execute
            name: Run name (auto-generated if not provided)
            task_id: Optional task ID to associate with run

        Returns:
            Run info dict
        """
        run_data = runs.start_run(command, name, self.project_path)

        # If task_id provided, store it in run metadata
        if task_id is not None:
            run_dir = Path(run_data["path"])
            task_file = run_dir / "task_id.txt"
            task_file.write_text(str(task_id))
            run_data["task_id"] = task_id

        return run_data

    def list_runs(self) -> list[dict[str, Any]]:
        """List all IdlerGear runs.

        Returns:
            List of run info dicts
        """
        run_list = runs.list_runs(self.project_path)

        # Add task_id if present
        for run in run_list:
            run_dir = Path(run["path"])
            task_file = run_dir / "task_id.txt"
            if task_file.exists():
                try:
                    run["task_id"] = int(task_file.read_text().strip())
                except ValueError:
                    pass

        return run_list

    def get_run_status(self, name: str) -> dict[str, Any] | None:
        """Get status of a run.

        Args:
            name: Run name

        Returns:
            Run status dict or None if not found
        """
        status = runs.get_run_status(name, self.project_path)

        if status:
            # Add task_id if present
            run_dir = Path(status["path"])
            task_file = run_dir / "task_id.txt"
            if task_file.exists():
                try:
                    status["task_id"] = int(task_file.read_text().strip())
                except ValueError:
                    pass

        return status

    def get_run_logs(
        self, name: str, tail: int | None = None, stream: str = "stdout"
    ) -> str | None:
        """Get logs from a run.

        Args:
            name: Run name
            tail: Number of lines from end (None for all)
            stream: 'stdout' or 'stderr'

        Returns:
            Log content or None if not found
        """
        return runs.get_run_logs(name, tail, stream, self.project_path)

    def stop_run(self, name: str) -> bool:
        """Stop a running process.

        Args:
            name: Run name

        Returns:
            True if stopped successfully
        """
        return runs.stop_run(name, self.project_path)

    def task_runs(self, task_id: int) -> list[dict[str, Any]]:
        """Get all runs associated with a task.

        Args:
            task_id: Task ID

        Returns:
            List of run info dicts
        """
        all_runs = self.list_runs()
        return [r for r in all_runs if r.get("task_id") == task_id]

    # ==== Quick Start ====

    def quick_start(self, executable: str, args: list[str] | None = None) -> dict[str, Any]:
        """Start a process in the foreground (not as a run).

        Args:
            executable: Path to executable or command name
            args: Command arguments

        Returns:
            Process info dict with PID
        """
        cmd = [executable]
        if args:
            cmd.extend(args)

        # Check if executable exists
        if not shutil.which(executable) and not Path(executable).exists():
            raise FileNotFoundError(f"Executable not found: {executable}")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.project_path,
        )

        return {
            "pid": proc.pid,
            "command": " ".join(cmd),
            "status": "running",
        }
