"""
Log coordinator: Capture and manage logs from running processes.

Captures stdout/stderr from shell scripts and processes, stores them,
and makes them available for LLM analysis and debugging.
"""

import os
import subprocess
import time
import signal
import json
import socket
import select
import sys
from pathlib import Path
from typing import Optional, List, Dict, Callable
from datetime import datetime
import threading


class LogCoordinator:
    """Coordinate log collection from running processes."""

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.logs_dir = self.project_path / ".idlergear" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.logs_dir / "metadata.json"
        self._load_metadata()

    def _load_metadata(self):
        """Load log session metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {"sessions": {}, "last_session_id": 0}
            # Save initial metadata
            self._save_initial_metadata()

    def _save_initial_metadata(self):
        """Save initial metadata file."""
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def _save_metadata(self):
        """Save log session metadata."""
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def _next_session_id(self) -> int:
        """Get next session ID."""
        self.metadata["last_session_id"] += 1
        return self.metadata["last_session_id"]

    def attach_to_process(self, pid: int, name: Optional[str] = None) -> Dict:
        """
        Attach to an existing process and capture its output.
        Uses strace on Linux to capture stdout/stderr.
        """
        session_id = self._next_session_id()
        timestamp = datetime.now().isoformat()

        if name is None:
            # Try to get process name
            try:
                result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "comm="],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                name = result.stdout.strip()
            except (subprocess.SubprocessError, FileNotFoundError):
                name = f"process-{pid}"

        log_file = self.logs_dir / f"session-{session_id}-{name}.log"

        session_info = {
            "session_id": session_id,
            "pid": pid,
            "name": name,
            "log_file": str(log_file),
            "started": timestamp,
            "status": "capturing",
        }

        self.metadata["sessions"][str(session_id)] = session_info
        self._save_metadata()

        return session_info

    def capture_stdin(
        self, name: Optional[str] = None, source: Optional[str] = None
    ) -> Dict:
        """
        Capture input from stdin (piped data).
        Useful for: ./run.sh | idlergear logs pipe --name my-app

        Args:
            name: Session name
            source: Optional description of source (e.g., "run.sh")

        Returns:
            Session info dict
        """
        import sys

        session_id = self._next_session_id()
        timestamp = datetime.now().isoformat()

        if name is None:
            name = "piped-input"

        log_file = self.logs_dir / f"session-{session_id}-{name}.log"

        session_info = {
            "session_id": session_id,
            "source": source or "stdin",
            "name": name,
            "log_file": str(log_file),
            "started": timestamp,
            "status": "capturing",
            "cwd": str(self.project_path),
        }

        self.metadata["sessions"][str(session_id)] = session_info
        self._save_metadata()

        # Read from stdin and write to log file
        line_count = 0
        with open(log_file, "w") as f:
            # Write header
            f.write(f"# Log Session {session_id}\n")
            f.write(f"# Source: {session_info['source']}\n")
            f.write(f"# Started: {timestamp}\n")
            f.write(f"# CWD: {session_info['cwd']}\n")
            f.write("#" + "=" * 70 + "\n\n")
            f.flush()

            # Read from stdin
            try:
                for line in sys.stdin:
                    f.write(line)
                    f.flush()
                    line_count += 1

                # Completed successfully
                session_info["status"] = "completed"
                session_info["line_count"] = line_count

            except KeyboardInterrupt:
                # User interrupted
                session_info["status"] = "stopped"
                session_info["line_count"] = line_count

            except Exception as e:
                session_info["status"] = "failed"
                session_info["error"] = str(e)
                session_info["line_count"] = line_count

            finally:
                session_info["ended"] = datetime.now().isoformat()
                self._save_metadata()

                # Write footer
                f.write("\n#" + "=" * 70 + "\n")
                f.write(f"# Ended: {session_info['ended']}\n")
                f.write(f"# Lines captured: {line_count}\n")

        return session_info

    def run_with_capture(
        self, command: List[str], name: Optional[str] = None, cwd: Optional[str] = None
    ) -> Dict:
        """
        Run a command and capture all its output.
        Returns session info.
        """
        session_id = self._next_session_id()
        timestamp = datetime.now().isoformat()

        if name is None:
            name = command[0]

        log_file = self.logs_dir / f"session-{session_id}-{name}.log"

        session_info = {
            "session_id": session_id,
            "command": " ".join(command),
            "name": name,
            "log_file": str(log_file),
            "started": timestamp,
            "status": "running",
            "cwd": cwd or str(self.project_path),
        }

        self.metadata["sessions"][str(session_id)] = session_info
        self._save_metadata()

        # Start process in background thread
        def run_process():
            try:
                with open(log_file, "w") as f:
                    # Write header
                    f.write(f"# Log Session {session_id}\n")
                    f.write(f"# Command: {' '.join(command)}\n")
                    f.write(f"# Started: {timestamp}\n")
                    f.write(f"# CWD: {session_info['cwd']}\n")
                    f.write("#" + "=" * 70 + "\n\n")
                    f.flush()

                    # Run command and capture output
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        cwd=cwd or self.project_path,
                    )

                    # Store PID
                    session_info["pid"] = process.pid
                    self._save_metadata()

                    # Stream output to log file
                    for line in process.stdout:
                        f.write(line)
                        f.flush()

                    process.wait()

                    # Update session status
                    session_info["status"] = "completed"
                    session_info["exit_code"] = process.returncode
                    session_info["ended"] = datetime.now().isoformat()
                    self._save_metadata()

                    # Write footer
                    f.write("\n#" + "=" * 70 + "\n")
                    f.write(f"# Ended: {session_info['ended']}\n")
                    f.write(f"# Exit code: {process.returncode}\n")

            except Exception as e:
                session_info["status"] = "failed"
                session_info["error"] = str(e)
                session_info["ended"] = datetime.now().isoformat()
                self._save_metadata()

        thread = threading.Thread(target=run_process, daemon=True)
        thread.start()

        # Give it a moment to start
        time.sleep(0.1)

        return session_info

    def list_sessions(self) -> List[Dict]:
        """List all log sessions."""
        return list(self.metadata["sessions"].values())

    def get_session(self, session_id: int) -> Optional[Dict]:
        """Get session info by ID."""
        return self.metadata["sessions"].get(str(session_id))

    def read_log(self, session_id: int, tail: Optional[int] = None) -> str:
        """
        Read log for a session.
        If tail is specified, return last N lines.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        log_file = Path(session["log_file"])
        if not log_file.exists():
            return ""

        if tail:
            # Read last N lines
            try:
                result = subprocess.run(
                    ["tail", "-n", str(tail), str(log_file)],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return result.stdout
            except (subprocess.SubprocessError, FileNotFoundError):
                # Fallback to reading full file
                pass

        return log_file.read_text()

    def stop_session(self, session_id: int) -> Dict:
        """Stop a running session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session["status"] != "running":
            return session

        pid = session.get("pid")
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                session["status"] = "stopped"
                session["ended"] = datetime.now().isoformat()
                self._save_metadata()
            except ProcessLookupError:
                session["status"] = "completed"
                session["ended"] = datetime.now().isoformat()
                self._save_metadata()

        return session

    def cleanup_old_logs(self, days: int = 7) -> int:
        """Delete log files older than N days. Returns count deleted."""
        cutoff = time.time() - (days * 86400)
        deleted = 0

        sessions_to_remove = []
        for session_id, session in self.metadata["sessions"].items():
            log_file = Path(session["log_file"])
            if log_file.exists():
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
                    sessions_to_remove.append(session_id)
                    deleted += 1

        for session_id in sessions_to_remove:
            del self.metadata["sessions"][session_id]

        if sessions_to_remove:
            self._save_metadata()

        return deleted

    def export_session(self, session_id: int, output_file: str) -> str:
        """Export a session log to a file."""
        log_content = self.read_log(session_id)
        session = self.get_session(session_id)

        output_path = Path(output_file)
        with open(output_path, "w") as f:
            f.write("# IdlerGear Log Export\n")
            f.write(f"# Session: {session_id}\n")
            f.write(f"# Name: {session.get('name', 'unknown')}\n")
            f.write(f"# Command: {session.get('command', 'N/A')}\n")
            f.write(f"# Started: {session.get('started', 'unknown')}\n")
            f.write("#" + "=" * 70 + "\n\n")
            f.write(log_content)

        return str(output_path)

    def serve(
        self,
        name: str,
        port: Optional[int] = None,
        callback: Optional[Callable[[str], None]] = None,
    ) -> Dict:
        """
        Start a log server to receive streamed logs.

        Args:
            name: Session name
            port: TCP port (if None, use Unix socket)
            callback: Called with each log line received

        Returns:
            Session info dict
        """
        session_id = self._next_session_id()
        timestamp = datetime.now().isoformat()

        log_file = self.logs_dir / f"session-{session_id}-{name}.log"

        session_info = {
            "session_id": session_id,
            "name": name,
            "log_file": str(log_file),
            "started": timestamp,
            "status": "serving",
            "source": "network",
        }

        if port:
            session_info["port"] = port
            session_info["address"] = f"0.0.0.0:{port}"
        else:
            socket_path = f"/tmp/idlergear-logs-{name}.sock"
            session_info["socket"] = socket_path

        self.metadata["sessions"][str(session_id)] = session_info
        self._save_metadata()

        running = True
        line_count = 0

        def signal_handler(sig, frame):
            nonlocal running
            running = False

        original_sigint = signal.signal(signal.SIGINT, signal_handler)
        original_sigterm = signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Create socket
            if port:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("0.0.0.0", port))
            else:
                socket_path = session_info["socket"]
                # Remove old socket if exists
                if os.path.exists(socket_path):
                    os.unlink(socket_path)
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server.bind(socket_path)

            server.listen(5)
            server.settimeout(1.0)

            with open(log_file, "w") as f:
                # Write header
                f.write(f"# Log Session {session_id}\n")
                f.write(f"# Name: {name}\n")
                f.write(f"# Started: {timestamp}\n")
                if port:
                    f.write(f"# Listening on: 0.0.0.0:{port}\n")
                else:
                    f.write(f"# Socket: {session_info['socket']}\n")
                f.write("#" + "=" * 70 + "\n\n")
                f.flush()

                clients = []

                while running:
                    try:
                        # Accept new connections
                        try:
                            client, addr = server.accept()
                            client.setblocking(False)
                            clients.append(client)
                            if callback:
                                callback(f"Client connected from {addr}")
                        except socket.timeout:
                            pass

                        # Read from clients
                        if clients:
                            readable, _, errored = select.select(
                                clients, [], clients, 0.1
                            )

                            for client in errored:
                                clients.remove(client)
                                client.close()

                            for client in readable:
                                try:
                                    data = client.recv(4096)
                                    if data:
                                        text = data.decode("utf-8", errors="replace")
                                        for line in text.splitlines(keepends=True):
                                            f.write(line)
                                            f.flush()
                                            line_count += 1
                                            if callback:
                                                callback(line.rstrip())
                                    else:
                                        clients.remove(client)
                                        client.close()
                                except Exception:
                                    clients.remove(client)
                                    client.close()

                    except Exception as e:
                        if callback:
                            callback(f"Error: {e}")

                # Write footer
                f.write("\n#" + "=" * 70 + "\n")
                f.write(f"# Ended: {datetime.now().isoformat()}\n")
                f.write(f"# Lines received: {line_count}\n")

            # Close all clients
            for client in clients:
                client.close()
            server.close()

            # Clean up socket file
            if not port and os.path.exists(session_info["socket"]):
                os.unlink(session_info["socket"])

            session_info["status"] = "completed"
            session_info["ended"] = datetime.now().isoformat()
            session_info["line_count"] = line_count
            self._save_metadata()

        except Exception as e:
            session_info["status"] = "failed"
            session_info["error"] = str(e)
            session_info["ended"] = datetime.now().isoformat()
            self._save_metadata()
            raise

        finally:
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)

        return session_info

    def stream(
        self,
        target: str,
        callback: Optional[Callable[[str], None]] = None,
    ) -> Dict:
        """
        Stream stdin to a log server.

        Args:
            target: Either session name (Unix socket) or host:port
            callback: Called with status updates

        Returns:
            Result dict
        """
        result = {
            "status": "ok",
            "lines_sent": 0,
            "target": target,
        }

        try:
            # Determine connection type
            if ":" in target and target.split(":")[-1].isdigit():
                # TCP connection
                host, port = target.rsplit(":", 1)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, int(port)))
                if callback:
                    callback(f"Connected to {host}:{port}")
            else:
                # Unix socket
                socket_path = f"/tmp/idlergear-logs-{target}.sock"
                if not os.path.exists(socket_path):
                    raise FileNotFoundError(f"Socket not found: {socket_path}")
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(socket_path)
                if callback:
                    callback(f"Connected to {socket_path}")

            try:
                for line in sys.stdin:
                    sock.sendall(line.encode("utf-8"))
                    result["lines_sent"] += 1

                if callback:
                    callback(f"Sent {result['lines_sent']} lines")

            except KeyboardInterrupt:
                if callback:
                    callback(f"Interrupted after {result['lines_sent']} lines")

            finally:
                sock.close()

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def follow(
        self,
        session_id: int,
        callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Follow a log session in real-time (like tail -f).

        Args:
            session_id: Session to follow
            callback: Called with each new line
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        log_file = Path(session["log_file"])
        if not log_file.exists():
            raise FileNotFoundError(f"Log file not found: {log_file}")

        running = True

        def signal_handler(sig, frame):
            nonlocal running
            running = False

        original_sigint = signal.signal(signal.SIGINT, signal_handler)

        try:
            with open(log_file, "r") as f:
                # Go to end of file
                f.seek(0, 2)

                while running:
                    line = f.readline()
                    if line:
                        if callback:
                            callback(line.rstrip())
                        else:
                            print(line, end="")
                    else:
                        time.sleep(0.1)

        finally:
            signal.signal(signal.SIGINT, original_sigint)

    def pull_from_loki(
        self,
        url: str,
        query: str,
        since: str = "1h",
        name: Optional[str] = None,
        limit: int = 1000,
    ) -> Dict:
        """
        Pull logs from Grafana Loki.

        Args:
            url: Loki URL (e.g., http://loki:3100)
            query: LogQL query (e.g., '{app="myapp"}')
            since: Time range (e.g., "1h", "30m", "2d")
            name: Session name
            limit: Max number of log entries

        Returns:
            Session info dict
        """
        import urllib.request
        import urllib.parse

        session_id = self._next_session_id()
        timestamp = datetime.now().isoformat()

        if name is None:
            name = "loki-pull"

        log_file = self.logs_dir / f"session-{session_id}-{name}.log"

        session_info = {
            "session_id": session_id,
            "name": name,
            "log_file": str(log_file),
            "started": timestamp,
            "status": "pulling",
            "source": "loki",
            "loki_url": url,
            "query": query,
        }

        self.metadata["sessions"][str(session_id)] = session_info
        self._save_metadata()

        try:
            # Parse since into nanoseconds
            since_ns = self._parse_duration_to_ns(since)
            start_ns = int(time.time() * 1e9) - since_ns

            # Build query URL
            params = urllib.parse.urlencode(
                {
                    "query": query,
                    "start": str(start_ns),
                    "limit": str(limit),
                    "direction": "forward",
                }
            )
            query_url = f"{url.rstrip('/')}/loki/api/v1/query_range?{params}"

            # Fetch logs
            req = urllib.request.Request(query_url)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Write to log file
            line_count = 0
            with open(log_file, "w") as f:
                f.write(f"# Log Session {session_id}\n")
                f.write(f"# Source: Loki ({url})\n")
                f.write(f"# Query: {query}\n")
                f.write(f"# Since: {since}\n")
                f.write(f"# Pulled: {timestamp}\n")
                f.write("#" + "=" * 70 + "\n\n")

                if data.get("status") == "success":
                    for stream in data.get("data", {}).get("result", []):
                        for ts, line in stream.get("values", []):
                            f.write(f"{line}\n")
                            line_count += 1

                f.write("\n#" + "=" * 70 + "\n")
                f.write(f"# Lines pulled: {line_count}\n")

            session_info["status"] = "completed"
            session_info["ended"] = datetime.now().isoformat()
            session_info["line_count"] = line_count
            self._save_metadata()

        except Exception as e:
            session_info["status"] = "failed"
            session_info["error"] = str(e)
            session_info["ended"] = datetime.now().isoformat()
            self._save_metadata()
            raise

        return session_info

    def pull_from_otel(
        self,
        endpoint: str,
        query: str,
        since: str = "1h",
        name: Optional[str] = None,
    ) -> Dict:
        """
        Pull logs from OpenTelemetry collector.

        Args:
            endpoint: OTLP HTTP endpoint (e.g., http://collector:4318)
            query: Query filter (e.g., 'service.name=myapp')
            since: Time range
            name: Session name

        Returns:
            Session info dict
        """
        # Note: OTEL doesn't have a standard query API like Loki
        # This would need to query the backend (Jaeger, Tempo, etc.)
        # For now, return a placeholder

        session_id = self._next_session_id()
        timestamp = datetime.now().isoformat()

        if name is None:
            name = "otel-pull"

        log_file = self.logs_dir / f"session-{session_id}-{name}.log"

        session_info = {
            "session_id": session_id,
            "name": name,
            "log_file": str(log_file),
            "started": timestamp,
            "status": "completed",
            "source": "otel",
            "otel_endpoint": endpoint,
            "query": query,
        }

        with open(log_file, "w") as f:
            f.write(f"# Log Session {session_id}\n")
            f.write(f"# Source: OTEL ({endpoint})\n")
            f.write(f"# Query: {query}\n")
            f.write(f"# Since: {since}\n")
            f.write("#" + "=" * 70 + "\n\n")
            f.write("# Note: OTEL log pull requires backend-specific implementation\n")
            f.write(
                "# Configure your OTEL backend (Jaeger, Tempo, etc.) query endpoint\n"
            )

        self.metadata["sessions"][str(session_id)] = session_info
        self._save_metadata()

        return session_info

    def _parse_duration_to_ns(self, duration: str) -> int:
        """Parse duration string (e.g., '1h', '30m', '2d') to nanoseconds."""
        duration = duration.strip().lower()

        multipliers = {
            "s": 1e9,
            "m": 60 * 1e9,
            "h": 3600 * 1e9,
            "d": 86400 * 1e9,
        }

        for suffix, mult in multipliers.items():
            if duration.endswith(suffix):
                value = float(duration[:-1])
                return int(value * mult)

        # Default to seconds
        return int(float(duration) * 1e9)
