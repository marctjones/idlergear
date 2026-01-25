"""Process management MCP server for IdlerGear.

Provides process listing, management, and monitoring capabilities.
Integrates with IdlerGear's existing run system for background task management.
"""

import platform
import shutil
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

    def quick_start(
        self, executable: str, args: list[str] | None = None
    ) -> dict[str, Any]:
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

    # ==== Tmux Session Management ====

    def _tmux_available(self) -> bool:
        """Check if tmux is installed."""
        return shutil.which("tmux") is not None

    def _get_tmux_server(self):
        """Get tmux server instance.

        Returns None if tmux not available or import fails.
        """
        if not self._tmux_available():
            return None

        try:
            import libtmux
            return libtmux.Server()
        except ImportError:
            return None

    def create_tmux_session(
        self,
        name: str,
        command: str | None = None,
        window_name: str | None = None,
        start_directory: str | None = None,
    ) -> dict[str, Any]:
        """Create a new tmux session.

        Args:
            name: Session name
            command: Optional command to run in the session
            window_name: Optional window name (defaults to session name)
            start_directory: Optional starting directory

        Returns:
            Session info dict

        Raises:
            RuntimeError: If tmux not available
        """
        server = self._get_tmux_server()
        if server is None:
            raise RuntimeError(
                "tmux not available. Install tmux and libtmux: "
                "apt install tmux && pip install libtmux"
            )

        # Check if session already exists
        existing = server.find_where({"session_name": name})
        if existing:
            raise ValueError(f"Tmux session '{name}' already exists")

        # Create session
        session = server.new_session(
            session_name=name,
            window_name=window_name or name,
            start_directory=start_directory or str(self.project_path),
        )

        # Run command if provided
        if command:
            window = session.attached_window
            pane = window.attached_pane
            pane.send_keys(command)

        return {
            "name": session.name,
            "id": session.id,
            "windows": len(session.windows),
            "attached": session.attached,
        }

    def list_tmux_sessions(self) -> list[dict[str, Any]]:
        """List all tmux sessions.

        Returns:
            List of session info dicts
        """
        server = self._get_tmux_server()
        if server is None:
            return []

        sessions = []
        for session in server.sessions:
            sessions.append({
                "name": session.name,
                "id": session.id,
                "windows": len(session.windows),
                "attached": session.attached,
                "created": session.created,
            })

        return sessions

    def get_tmux_session(self, name: str) -> dict[str, Any] | None:
        """Get information about a specific tmux session.

        Args:
            name: Session name

        Returns:
            Session info dict or None if not found
        """
        server = self._get_tmux_server()
        if server is None:
            return None

        session = server.find_where({"session_name": name})
        if not session:
            return None

        windows = []
        for window in session.windows:
            panes = []
            for pane in window.panes:
                panes.append({
                    "id": pane.id,
                    "width": pane.width,
                    "height": pane.height,
                    "active": pane.pane_active,
                })
            windows.append({
                "id": window.id,
                "name": window.name,
                "panes": panes,
            })

        return {
            "name": session.name,
            "id": session.id,
            "windows": windows,
            "attached": session.attached,
            "created": session.created,
        }

    def kill_tmux_session(self, name: str) -> bool:
        """Kill a tmux session.

        Args:
            name: Session name

        Returns:
            True if session was killed, False if not found
        """
        server = self._get_tmux_server()
        if server is None:
            return False

        session = server.find_where({"session_name": name})
        if not session:
            return False

        session.kill_session()
        return True

    def send_keys_to_tmux(
        self, session_name: str, keys: str, window_index: int = 0, pane_index: int = 0
    ) -> bool:
        """Send keys to a specific pane in a tmux session.

        Args:
            session_name: Session name
            keys: Keys to send
            window_index: Window index (default: 0)
            pane_index: Pane index within window (default: 0)

        Returns:
            True if successful, False otherwise
        """
        server = self._get_tmux_server()
        if server is None:
            return False

        session = server.find_where({"session_name": session_name})
        if not session:
            return False

        if window_index >= len(session.windows):
            return False

        window = session.windows[window_index]
        if pane_index >= len(window.panes):
            return False

        pane = window.panes[pane_index]
        pane.send_keys(keys)
        return True

    def split_tmux_window(
        self,
        session_name: str,
        command: str | None = None,
        vertical: bool = True,
        window_index: int = 0,
    ) -> dict[str, Any] | None:
        """Split a window in a tmux session.

        Args:
            session_name: Session name
            command: Optional command to run in the new pane
            vertical: If True, split vertically; if False, split horizontally
            window_index: Window index to split (default: 0)

        Returns:
            New pane info dict or None if failed
        """
        server = self._get_tmux_server()
        if server is None:
            return None

        session = server.find_where({"session_name": session_name})
        if not session or window_index >= len(session.windows):
            return None

        window = session.windows[window_index]
        new_pane = window.split_window(vertical=vertical)

        if command:
            new_pane.send_keys(command)

        return {
            "id": new_pane.id,
            "width": new_pane.width,
            "height": new_pane.height,
            "active": new_pane.pane_active,
        }

    # ==== Container Management (Podman/Docker) ====

    def _get_container_runtime(self) -> str | None:
        """Get available container runtime (podman or docker).

        Returns:
            'podman', 'docker', or None if neither available
        """
        if shutil.which("podman"):
            return "podman"
        elif shutil.which("docker"):
            return "docker"
        return None

    def list_containers(
        self, all_containers: bool = False
    ) -> list[dict[str, Any]]:
        """List running containers.

        Args:
            all_containers: Include stopped containers

        Returns:
            List of container info dicts
        """
        runtime = self._get_container_runtime()
        if not runtime:
            return []

        cmd = [runtime, "ps", "--format", "json"]
        if all_containers:
            cmd.append("-a")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=10
            )

            # Parse JSON output
            import json

            containers = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    container = json.loads(line)
                    containers.append(
                        {
                            "id": container.get("ID", container.get("Id", ""))[:12],
                            "name": (
                                container.get("Names", [""])[0]
                                if isinstance(container.get("Names"), list)
                                else container.get("Names", "")
                            ),
                            "image": container.get("Image", ""),
                            "status": container.get("Status", container.get("State", "")),
                            "created": container.get("CreatedAt", ""),
                        }
                    )
            return containers
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return []

    def start_container(
        self,
        image: str,
        name: str | None = None,
        command: str | None = None,
        env: dict[str, str] | None = None,
        volumes: dict[str, str] | None = None,
        ports: dict[str, str] | None = None,
        memory: str | None = None,
        cpus: str | None = None,
        detach: bool = True,
    ) -> dict[str, Any]:
        """Start a container.

        Args:
            image: Container image (e.g., "python:3.11")
            name: Container name
            command: Command to run in container
            env: Environment variables {key: value}
            volumes: Volume mounts {host_path: container_path}
            ports: Port mappings {host_port: container_port}
            memory: Memory limit (e.g., "512m", "2g")
            cpus: CPU limit (e.g., "1.5")
            detach: Run in background

        Returns:
            Container info dict with id and name

        Raises:
            RuntimeError: If no container runtime available
        """
        runtime = self._get_container_runtime()
        if not runtime:
            raise RuntimeError(
                "No container runtime available. Install podman or docker."
            )

        cmd = [runtime, "run"]

        if detach:
            cmd.append("-d")

        if name:
            cmd.extend(["--name", name])

        if env:
            for key, value in env.items():
                cmd.extend(["-e", f"{key}={value}"])

        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["-v", f"{host_path}:{container_path}"])

        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])

        if memory:
            cmd.extend(["--memory", memory])

        if cpus:
            cmd.extend(["--cpus", cpus])

        cmd.append(image)

        if command:
            cmd.extend(command.split())

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=60
            )
            container_id = result.stdout.strip()[:12]

            return {
                "id": container_id,
                "name": name or container_id,
                "image": image,
                "runtime": runtime,
            }
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to start container: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Container start timed out")

    def stop_container(self, container_id: str, force: bool = False) -> bool:
        """Stop a container.

        Args:
            container_id: Container ID or name
            force: Force stop (kill instead of graceful shutdown)

        Returns:
            True if stopped successfully
        """
        runtime = self._get_container_runtime()
        if not runtime:
            return False

        cmd = [runtime, "kill" if force else "stop", container_id]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container.

        Args:
            container_id: Container ID or name
            force: Force removal even if running

        Returns:
            True if removed successfully
        """
        runtime = self._get_container_runtime()
        if not runtime:
            return False

        cmd = [runtime, "rm"]
        if force:
            cmd.append("-f")
        cmd.append(container_id)

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def get_container_logs(
        self, container_id: str, tail: int | None = None, follow: bool = False
    ) -> str | None:
        """Get logs from a container.

        Args:
            container_id: Container ID or name
            tail: Number of lines from end (None for all)
            follow: Stream logs (blocking)

        Returns:
            Log content or None if container not found
        """
        runtime = self._get_container_runtime()
        if not runtime:
            return None

        cmd = [runtime, "logs"]
        if tail:
            cmd.extend(["--tail", str(tail)])
        if follow:
            cmd.append("-f")
        cmd.append(container_id)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=10
            )
            return result.stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    def get_container_stats(self, container_id: str) -> dict[str, Any] | None:
        """Get resource usage stats for a container.

        Args:
            container_id: Container ID or name

        Returns:
            Stats dict with CPU, memory usage or None if not found
        """
        runtime = self._get_container_runtime()
        if not runtime:
            return None

        cmd = [runtime, "stats", "--no-stream", "--format", "json", container_id]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=10
            )

            import json

            stats = json.loads(result.stdout.strip())

            return {
                "cpu_percent": stats.get("CPUPerc", stats.get("CPU", "0%")).rstrip("%"),
                "memory_usage": stats.get("MemUsage", stats.get("MemoryUsage", "")),
                "memory_percent": stats.get("MemPerc", stats.get("Memory", "0%")).rstrip("%"),
                "network_io": stats.get("NetIO", ""),
                "block_io": stats.get("BlockIO", ""),
            }
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None
