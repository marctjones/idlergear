"""
Teleport session tracking for IdlerGear.

This module provides functionality to track and manage Claude Code web teleport
sessions, allowing users to log session information, list past sessions, and
export session details.
"""

import json
import subprocess
import time
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class TeleportTracker:
    """
    Manages teleport session tracking for IdlerGear projects.

    Teleport sessions represent transfers from Claude Code web to local CLI.
    This class stores metadata about each teleport session including:
    - Session UUID
    - Timestamp
    - Branch name
    - Description
    - Files changed
    """

    def __init__(self, project_path: str = "."):
        """
        Initialize the teleport tracker.

        Args:
            project_path: Path to the project root (default: current directory)
        """
        self.project_root = Path(project_path).resolve()
        self.teleport_dir = self.project_root / ".idlergear" / "teleport-sessions"
        self.metadata_file = self.teleport_dir / "metadata.json"

        # Ensure teleport directory exists
        self.teleport_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metadata file if it doesn't exist
        if not self.metadata_file.exists():
            self._write_metadata({"sessions": []})

    def _read_metadata(self) -> Dict:
        """Read teleport sessions metadata."""
        if not self.metadata_file.exists():
            return {"sessions": []}

        with open(self.metadata_file, "r") as f:
            return json.load(f)

    def _write_metadata(self, data: Dict):
        """Write teleport sessions metadata."""
        with open(self.metadata_file, "w") as f:
            json.dump(data, f, indent=2)

    def _get_current_branch(self) -> str:
        """Get the current git branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def _get_changed_files(self) -> List[str]:
        """Get list of currently changed files."""
        try:
            # Get staged files
            staged_result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Get unstaged files
            unstaged_result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Get untracked files
            untracked_result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Combine all changed files
            all_files = set()
            for result in [staged_result, unstaged_result, untracked_result]:
                files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
                all_files.update(files)

            return sorted(list(all_files))

        except subprocess.CalledProcessError:
            return []

    def prepare_for_teleport(self, branch: str) -> Dict:
        """
        Prepare the local environment for teleport.

        This method:
        1. Verifies we're in a git repo
        2. Fetches latest from remote
        3. Stashes any uncommitted changes
        4. Checks out the specified branch
        5. Pulls latest changes

        Args:
            branch: The branch to check out

        Returns:
            Dictionary with preparation status and details
        """
        result = {
            "status": "ok",
            "branch": branch,
            "stashed": False,
            "stash_name": None,
            "messages": [],
        }

        try:
            # 1. Check if we're in a git repo
            git_check = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if git_check.returncode != 0:
                return {
                    "status": "error",
                    "error": "Not a git repository",
                    "messages": ["Please run this command from a git repository"],
                }

            # 2. Get current branch
            current_branch = self._get_current_branch()
            result["original_branch"] = current_branch

            # 3. Fetch from remote
            result["messages"].append("Fetching from remote...")
            fetch_result = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if fetch_result.returncode != 0:
                result["messages"].append(
                    f"Warning: fetch failed: {fetch_result.stderr}"
                )

            # 4. Check for uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            has_changes = bool(status_result.stdout.strip())

            # 5. Stash if there are uncommitted changes
            if has_changes:
                stash_name = (
                    f"idlergear-teleport-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                )
                result["messages"].append(
                    f"Stashing uncommitted changes as '{stash_name}'..."
                )

                stash_result = subprocess.run(
                    ["git", "stash", "push", "-m", stash_name, "--include-untracked"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )

                if stash_result.returncode == 0:
                    result["stashed"] = True
                    result["stash_name"] = stash_name
                    result["messages"].append("Changes stashed successfully")
                else:
                    return {
                        "status": "error",
                        "error": f"Failed to stash changes: {stash_result.stderr}",
                        "messages": result["messages"],
                    }

            # 6. Check out the branch
            if current_branch != branch:
                result["messages"].append(
                    f"Switching from '{current_branch}' to '{branch}'..."
                )

                checkout_result = subprocess.run(
                    ["git", "checkout", branch],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )

                if checkout_result.returncode != 0:
                    # Try to create the branch from remote
                    checkout_result = subprocess.run(
                        ["git", "checkout", "-b", branch, f"origin/{branch}"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                    )

                    if checkout_result.returncode != 0:
                        # Restore stash if we made one
                        if result["stashed"]:
                            subprocess.run(
                                ["git", "stash", "pop"],
                                cwd=self.project_root,
                                capture_output=True,
                            )
                        return {
                            "status": "error",
                            "error": f"Failed to checkout branch '{branch}': {checkout_result.stderr}",
                            "messages": result["messages"],
                        }

                result["messages"].append(f"Switched to branch '{branch}'")
            else:
                result["messages"].append(f"Already on branch '{branch}'")

            # 7. Pull latest changes
            result["messages"].append("Pulling latest changes...")
            pull_result = subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if pull_result.returncode == 0:
                result["messages"].append("Pull completed successfully")
            else:
                result["messages"].append(f"Warning: pull failed: {pull_result.stderr}")

            result["messages"].append("")
            result["messages"].append("Ready for teleport! Run:")
            result["messages"].append("  claude --teleport <uuid>")

            if result["stashed"]:
                result["messages"].append("")
                result["messages"].append(
                    "After teleport, restore your stashed changes with:"
                )
                result["messages"].append("  idlergear teleport restore-stash")

            return result

        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "error": str(e),
                "messages": result.get("messages", []),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "messages": result.get("messages", []),
            }

    def restore_stash(self) -> Dict:
        """
        Restore the most recent idlergear teleport stash.

        Returns:
            Dictionary with restoration status
        """
        try:
            # List stashes to find idlergear teleport stashes
            stash_list = subprocess.run(
                ["git", "stash", "list"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Find the most recent idlergear-teleport stash
            stash_index = None
            stash_name = None
            for line in stash_list.stdout.split("\n"):
                if "idlergear-teleport-" in line:
                    # Extract stash index (e.g., "stash@{0}")
                    stash_index = line.split(":")[0]
                    # Extract stash name
                    if "idlergear-teleport-" in line:
                        start = line.find("idlergear-teleport-")
                        stash_name = line[start:].strip()
                    break

            if stash_index is None:
                return {
                    "status": "no_stash",
                    "message": "No idlergear teleport stash found",
                }

            # Pop the stash
            pop_result = subprocess.run(
                ["git", "stash", "pop", stash_index],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if pop_result.returncode == 0:
                return {
                    "status": "restored",
                    "stash_name": stash_name,
                    "message": f"Restored stash: {stash_name}",
                }
            else:
                return {
                    "status": "error",
                    "error": pop_result.stderr,
                    "message": f"Failed to restore stash: {pop_result.stderr}",
                }

        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def finish_teleport(self, target_branch: str = "main") -> Dict:
        """
        Finish teleport by merging to target branch and cleaning up.

        This method:
        1. If on a feature branch, merge it to target branch (default: main)
        2. Delete the feature branch locally and remotely
        3. Push changes
        4. Restore any stashed changes

        Args:
            target_branch: Branch to merge into (default: main)

        Returns:
            Dictionary with finish status and details
        """
        result = {
            "status": "ok",
            "messages": [],
            "merged_branch": None,
            "deleted_branches": [],
        }

        try:
            current_branch = self._get_current_branch()
            result["original_branch"] = current_branch

            # If already on target branch, just push and restore stash
            if current_branch == target_branch:
                result["messages"].append(f"Already on {target_branch}")

                # Push any changes
                result["messages"].append(f"Pushing to {target_branch}...")
                push_result = subprocess.run(
                    ["git", "push", "origin", target_branch],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if push_result.returncode == 0:
                    result["messages"].append("Push completed")
                else:
                    result["messages"].append(
                        f"Warning: push failed: {push_result.stderr}"
                    )

                # Restore stash
                stash_result = self.restore_stash()
                if stash_result["status"] == "restored":
                    result["messages"].append(
                        f"Restored stash: {stash_result.get('stash_name', '')}"
                    )

                return result

            # We're on a feature branch - merge to target
            feature_branch = current_branch
            result["merged_branch"] = feature_branch
            result["messages"].append(
                f"Merging '{feature_branch}' into '{target_branch}'..."
            )

            # Checkout target branch
            checkout_result = subprocess.run(
                ["git", "checkout", target_branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if checkout_result.returncode != 0:
                return {
                    "status": "error",
                    "error": f"Failed to checkout {target_branch}: {checkout_result.stderr}",
                    "messages": result["messages"],
                }

            # Merge feature branch
            merge_result = subprocess.run(
                ["git", "merge", feature_branch, "--no-edit"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if merge_result.returncode != 0:
                return {
                    "status": "error",
                    "error": f"Merge failed: {merge_result.stderr}. Resolve conflicts manually.",
                    "messages": result["messages"],
                }

            result["messages"].append(
                f"Merged '{feature_branch}' into '{target_branch}'"
            )

            # Push target branch
            result["messages"].append(f"Pushing {target_branch}...")
            push_result = subprocess.run(
                ["git", "push", "origin", target_branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if push_result.returncode == 0:
                result["messages"].append("Push completed")
            else:
                result["messages"].append(f"Warning: push failed: {push_result.stderr}")

            # Delete local feature branch
            result["messages"].append(f"Deleting local branch '{feature_branch}'...")
            delete_local = subprocess.run(
                ["git", "branch", "-d", feature_branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if delete_local.returncode == 0:
                result["deleted_branches"].append(f"{feature_branch} (local)")
                result["messages"].append(f"Deleted local branch '{feature_branch}'")
            else:
                result["messages"].append(
                    f"Warning: could not delete local branch: {delete_local.stderr}"
                )

            # Delete remote feature branch
            result["messages"].append(f"Deleting remote branch '{feature_branch}'...")
            delete_remote = subprocess.run(
                ["git", "push", "origin", "--delete", feature_branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if delete_remote.returncode == 0:
                result["deleted_branches"].append(f"{feature_branch} (remote)")
                result["messages"].append(f"Deleted remote branch '{feature_branch}'")
            else:
                result["messages"].append(
                    f"Warning: could not delete remote branch: {delete_remote.stderr}"
                )

            # Restore stash
            stash_result = self.restore_stash()
            if stash_result["status"] == "restored":
                result["messages"].append(
                    f"Restored stash: {stash_result.get('stash_name', '')}"
                )

            result["messages"].append("")
            result["messages"].append(f"✅ All changes merged to {target_branch}")
            if result["deleted_branches"]:
                result["messages"].append(
                    f"   Cleaned up: {', '.join(result['deleted_branches'])}"
                )

            return result

        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "error": str(e),
                "messages": result.get("messages", []),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "messages": result.get("messages", []),
            }

    def watch_session(
        self,
        command: str,
        poll_interval: int = 10,
        log_push_interval: int = 60,
        callback=None,
    ) -> Dict:
        """
        Run a long-running watch session for GUI testing.

        This method:
        1. Runs the specified command (e.g., GUI app)
        2. Captures logs to .idlergear/logs/
        3. Polls for new commits on current branch
        4. Auto-pulls and restarts command when changes detected
        5. Periodically commits and pushes logs for Claude Code web to see

        Args:
            command: Command to run (e.g., "python -m src.gui.main")
            poll_interval: Seconds between checking for remote changes
            log_push_interval: Seconds between pushing logs to remote
            callback: Optional callback function for status updates

        Returns:
            Dictionary with session summary when terminated
        """
        result = {
            "status": "ok",
            "restarts": 0,
            "logs_pushed": 0,
            "duration": 0,
            "messages": [],
        }

        # Track state
        process = None
        running = True
        start_time = datetime.now()
        last_log_push = start_time
        last_commit = self._get_last_commit_hash()
        log_file = None

        def signal_handler(sig, frame):
            nonlocal running
            running = False
            if callback:
                callback("Received termination signal, shutting down...")

        # Set up signal handlers
        original_sigint = signal.signal(signal.SIGINT, signal_handler)
        original_sigterm = signal.signal(signal.SIGTERM, signal_handler)

        try:
            current_branch = self._get_current_branch()
            result["branch"] = current_branch

            if callback:
                callback(f"Starting watch session on branch '{current_branch}'")
                callback(f"Command: {command}")
                callback(
                    f"Poll interval: {poll_interval}s, Log push interval: {log_push_interval}s"
                )
                callback("")

            # Create log directory
            logs_dir = self.project_root / ".idlergear" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            session_name = f"watch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            log_file = logs_dir / f"{session_name}.log"

            def start_process():
                nonlocal process
                # Start process with output capture
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=self.project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                if callback:
                    callback(f"Started process (PID: {process.pid})")
                return process

            def stop_process():
                nonlocal process
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    if callback:
                        callback("Stopped process")

            def check_for_updates():
                """Check if there are new commits on remote."""
                # Fetch from remote
                fetch_result = subprocess.run(
                    ["git", "fetch", "origin", current_branch],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if fetch_result.returncode != 0:
                    return False

                # Check if remote is ahead
                result = subprocess.run(
                    ["git", "rev-parse", f"origin/{current_branch}"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    return False

                remote_commit = result.stdout.strip()
                return remote_commit != last_commit

            def pull_updates():
                nonlocal last_commit
                pull_result = subprocess.run(
                    ["git", "pull", "origin", current_branch],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if pull_result.returncode == 0:
                    last_commit = self._get_last_commit_hash()
                    return True
                return False

            def push_logs():
                """Commit and push logs so Claude Code web can see them."""
                nonlocal last_log_push

                # Add log file
                subprocess.run(
                    ["git", "add", str(log_file)],
                    cwd=self.project_root,
                    capture_output=True,
                )

                # Check if there are changes to commit
                status = subprocess.run(
                    ["git", "diff", "--cached", "--quiet"],
                    cwd=self.project_root,
                )

                if status.returncode != 0:  # There are staged changes
                    # Commit
                    subprocess.run(
                        [
                            "git",
                            "commit",
                            "-m",
                            f"chore: Update watch session logs ({session_name})",
                        ],
                        cwd=self.project_root,
                        capture_output=True,
                    )

                    # Push
                    push_result = subprocess.run(
                        ["git", "push", "origin", current_branch],
                        cwd=self.project_root,
                        capture_output=True,
                    )

                    if push_result.returncode == 0:
                        result["logs_pushed"] += 1
                        if callback:
                            callback(f"Pushed logs to {current_branch}")
                        last_log_push = datetime.now()
                        return True

                return False

            # Start initial process
            process = start_process()

            # Main watch loop
            with open(log_file, "w") as lf:
                lf.write(f"=== Watch Session Started: {start_time.isoformat()} ===\n")
                lf.write(f"Command: {command}\n")
                lf.write(f"Branch: {current_branch}\n")
                lf.write("=" * 60 + "\n\n")

                while running:
                    # Read any available output from process
                    if process and process.poll() is None:
                        try:
                            # Non-blocking read
                            import select

                            if hasattr(select, "select"):
                                readable, _, _ = select.select(
                                    [process.stdout], [], [], 0.1
                                )
                                if readable:
                                    line = process.stdout.readline()
                                    if line:
                                        timestamp = datetime.now().strftime("%H:%M:%S")
                                        log_line = f"[{timestamp}] {line}"
                                        lf.write(log_line)
                                        lf.flush()
                                        if callback:
                                            callback(f"LOG: {line.strip()}")
                        except Exception:
                            pass
                    elif process:
                        # Process ended
                        if callback:
                            callback(f"Process exited with code {process.returncode}")
                        lf.write(f"\n[Process exited with code {process.returncode}]\n")
                        lf.flush()

                    # Check for remote updates
                    if check_for_updates():
                        if callback:
                            callback("New commits detected on remote!")
                        lf.write(
                            f"\n[{datetime.now().strftime('%H:%M:%S')}] New commits detected, pulling...\n"
                        )

                        stop_process()

                        if pull_updates():
                            if callback:
                                callback("Pulled updates, restarting...")
                            lf.write(
                                f"[{datetime.now().strftime('%H:%M:%S')}] Pulled updates, restarting command\n\n"
                            )
                            result["restarts"] += 1
                            process = start_process()
                        else:
                            if callback:
                                callback("Failed to pull updates")
                            lf.write(
                                f"[{datetime.now().strftime('%H:%M:%S')}] Failed to pull updates\n"
                            )

                    # Check if it's time to push logs
                    now = datetime.now()
                    if (now - last_log_push).total_seconds() >= log_push_interval:
                        lf.flush()
                        push_logs()

                    # Sleep before next poll
                    time.sleep(poll_interval)

                # Clean shutdown
                lf.write(
                    f"\n=== Watch Session Ended: {datetime.now().isoformat()} ===\n"
                )

            # Stop the process
            stop_process()

            # Final log push
            push_logs()

            # Calculate duration
            end_time = datetime.now()
            result["duration"] = int((end_time - start_time).total_seconds())
            result["log_file"] = str(log_file)

            result["messages"].append("Watch session ended")
            result["messages"].append(f"Duration: {result['duration']} seconds")
            result["messages"].append(f"Restarts: {result['restarts']}")
            result["messages"].append(f"Logs pushed: {result['logs_pushed']}")
            result["messages"].append(f"Log file: {log_file}")

            return result

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            return result

        finally:
            # Restore signal handlers
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)

            # Ensure process is stopped
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

    def _get_last_commit_hash(self) -> str:
        """Get the hash of the last commit on current branch."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def log_session(
        self,
        session_id: str,
        description: Optional[str] = None,
        files_changed: Optional[List[str]] = None,
        branch: Optional[str] = None,
    ) -> Dict:
        """
        Log a teleport session.

        Args:
            session_id: The UUID from the teleport command
            description: Optional description of the session
            files_changed: Optional list of files changed (auto-detected if not provided)
            branch: Optional branch name (auto-detected if not provided)

        Returns:
            Dictionary with session information
        """
        # Get current branch if not provided
        if branch is None:
            branch = self._get_current_branch()

        # Get changed files if not provided
        if files_changed is None:
            files_changed = self._get_changed_files()

        # Create session record
        session = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "branch": branch,
            "description": description or f"Teleport session {session_id[:8]}",
            "files_changed": files_changed,
            "files_count": len(files_changed),
        }

        # Read existing metadata
        metadata = self._read_metadata()

        # Check if session already exists
        existing_index = None
        for i, s in enumerate(metadata["sessions"]):
            if s["session_id"] == session_id:
                existing_index = i
                break

        # Update or append session
        if existing_index is not None:
            metadata["sessions"][existing_index] = session
            status = "updated"
        else:
            metadata["sessions"].append(session)
            status = "created"

        # Write metadata
        self._write_metadata(metadata)

        # Also write individual session file for easy reference
        session_file = self.teleport_dir / f"{session_id}.json"
        with open(session_file, "w") as f:
            json.dump(session, f, indent=2)

        return {
            "status": status,
            "session": session,
            "session_file": str(session_file),
        }

    def list_sessions(
        self,
        limit: Optional[int] = None,
        branch: Optional[str] = None,
    ) -> List[Dict]:
        """
        List teleport sessions.

        Args:
            limit: Optional limit on number of sessions to return
            branch: Optional branch filter

        Returns:
            List of session dictionaries
        """
        metadata = self._read_metadata()
        sessions = metadata.get("sessions", [])

        # Filter by branch if specified
        if branch:
            sessions = [s for s in sessions if s.get("branch") == branch]

        # Sort by timestamp (most recent first)
        sessions = sorted(
            sessions,
            key=lambda s: s.get("timestamp", ""),
            reverse=True,
        )

        # Apply limit if specified
        if limit:
            sessions = sessions[:limit]

        return sessions

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get a specific teleport session by ID.

        Args:
            session_id: The session UUID (full or partial)

        Returns:
            Session dictionary if found, None otherwise
        """
        metadata = self._read_metadata()
        sessions = metadata.get("sessions", [])

        # Try exact match first
        for session in sessions:
            if session["session_id"] == session_id:
                return session

        # Try partial match (for convenience)
        matches = [s for s in sessions if s["session_id"].startswith(session_id)]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous session ID '{session_id}'. "
                f"Matches: {[s['session_id'][:8] for s in matches]}"
            )

        return None

    def export_session(
        self,
        session_id: str,
        output_format: str = "json",
    ) -> Dict:
        """
        Export a teleport session in the specified format.

        Args:
            session_id: The session UUID
            output_format: Format for export (json or markdown)

        Returns:
            Dictionary with export content and metadata
        """
        session = self.get_session(session_id)

        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if output_format == "json":
            content = json.dumps(session, indent=2)
        elif output_format == "markdown":
            content = self._format_session_markdown(session)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

        return {
            "session": session,
            "format": output_format,
            "content": content,
        }

    def _format_session_markdown(self, session: Dict) -> str:
        """Format a session as markdown."""
        lines = [
            f"# Teleport Session: {session['session_id'][:8]}",
            "",
            f"**Session ID:** `{session['session_id']}`",
            f"**Timestamp:** {session['timestamp']}",
            f"**Branch:** `{session['branch']}`",
            f"**Description:** {session['description']}",
            "",
            "## Files Changed",
            "",
        ]

        files = session.get("files_changed", [])
        if files:
            for file_path in files:
                lines.append(f"- `{file_path}`")
        else:
            lines.append("_(No files changed)_")

        lines.extend(["", f"**Total Files:** {session['files_count']}", ""])

        return "\n".join(lines)

    def format_session_list(self, sessions: List[Dict]) -> str:
        """
        Format a list of sessions for display.

        Args:
            sessions: List of session dictionaries

        Returns:
            Formatted string for terminal display
        """
        if not sessions:
            return "No teleport sessions found."

        lines = [f"Found {len(sessions)} teleport session(s):", ""]

        for session in sessions:
            session_id_short = session["session_id"][:8]
            timestamp = session.get("timestamp", "unknown")
            branch = session.get("branch", "unknown")
            desc = session.get("description", "")
            files_count = session.get("files_count", 0)

            lines.extend(
                [
                    f"📍 Session: {session_id_short}",
                    f"   Time: {timestamp}",
                    f"   Branch: {branch}",
                    f"   Description: {desc}",
                    f"   Files changed: {files_count}",
                    "",
                ]
            )

        return "\n".join(lines)

    def format_session(self, session: Dict) -> str:
        """
        Format a single session for detailed display.

        Args:
            session: Session dictionary

        Returns:
            Formatted string for terminal display
        """
        lines = [
            f"Teleport Session: {session['session_id'][:8]}",
            "",
            f"Session ID:  {session['session_id']}",
            f"Timestamp:   {session.get('timestamp', 'unknown')}",
            f"Branch:      {session.get('branch', 'unknown')}",
            f"Description: {session.get('description', '')}",
            "",
            "Files Changed:",
        ]

        files = session.get("files_changed", [])
        if files:
            for file_path in files:
                lines.append(f"  - {file_path}")
        else:
            lines.append("  (none)")

        lines.extend(["", f"Total: {session.get('files_count', 0)} file(s)", ""])

        return "\n".join(lines)
