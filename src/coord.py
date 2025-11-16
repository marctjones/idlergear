"""Coordination repository management for LLM-to-LLM communication."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class CoordRepo:
    """Manages private GitHub coordination repository for message passing."""

    def __init__(self, coord_path: Optional[Path] = None):
        """Initialize coordinator with path to coordination repo."""
        self.coord_path = coord_path or Path.home() / ".idlergear" / "coord"
        self.repo_name = "idlergear-coord"

    def init(self) -> dict:
        """Initialize coordination repository."""
        result = {"status": "initialized", "path": str(self.coord_path)}

        # Check if already initialized
        if self.coord_path.exists() and (self.coord_path / ".git").exists():
            result["status"] = "already_exists"
            return result

        # Create coordination repo on GitHub
        try:
            # Create private repo via gh CLI
            cmd = [
                "gh",
                "repo",
                "create",
                self.repo_name,
                "--private",
                "--clone",
                "--description",
                "IdlerGear coordination for LLM message passing",
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Move cloned repo to correct location
            cloned_path = Path.cwd() / self.repo_name
            if cloned_path.exists():
                self.coord_path.parent.mkdir(parents=True, exist_ok=True)
                cloned_path.rename(self.coord_path)

            # Create directory structure
            (self.coord_path / "projects").mkdir(parents=True, exist_ok=True)

            # Create README
            readme = self.coord_path / "README.md"
            readme.write_text(
                """# IdlerGear Coordination Repository

This private repository is used by IdlerGear for:
- Message passing between local and web LLM coding tools
- Coordination data for multi-environment development
- Temporary storage for cross-tool communication

**Note:** This repo is managed automatically by IdlerGear. Do not edit manually.
"""
            )

            # Initial commit
            self._git_commit("Initial setup", add_all=True)

            result["status"] = "created"
            result["repo_url"] = self._get_remote_url()

        except subprocess.CalledProcessError as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def send_message(
        self, project: str, message: str, to: str = "web", via: str = "file"
    ) -> dict:
        """Send message to another LLM environment."""
        if not self.coord_path.exists():
            return {
                "status": "error",
                "error": "Coordination repo not initialized. Run: idlergear coord init",
            }

        project_dir = self.coord_path / "projects" / project
        project_dir.mkdir(parents=True, exist_ok=True)

        if via == "file":
            return self._send_via_file(project_dir, message, to)
        elif via == "issue":
            return self._send_via_issue(project, message, to)
        else:
            return {"status": "error", "error": f"Unknown method: {via}"}

    def _send_via_file(self, project_dir: Path, message: str, to: str) -> dict:
        """Send message via file in coordination repo."""
        messages_dir = project_dir / "messages"
        messages_dir.mkdir(exist_ok=True)

        # Create message file with timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        msg_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        msg_file = messages_dir / f"{msg_id}.json"

        msg_data = {
            "id": msg_id,
            "timestamp": timestamp,
            "from": "local",
            "to": to,
            "message": message,
            "status": "sent",
        }

        msg_file.write_text(json.dumps(msg_data, indent=2))

        # Commit and push
        self._git_commit(f"Message to {to}: {message[:50]}", add_all=True)
        self._git_push()

        return {"status": "sent", "message_id": msg_id, "via": "file"}

    def _send_via_issue(self, project: str, message: str, to: str) -> dict:
        """Send message via GitHub issue."""
        try:
            # Create issue with project label
            title = f"[{project}] Message to {to}"
            body = f"""**From:** local
**To:** {to}
**Timestamp:** {datetime.now(timezone.utc).isoformat()}

---

{message}
"""

            cmd = [
                "gh",
                "issue",
                "create",
                "--repo",
                self._get_remote_url().replace("https://github.com/", ""),
                "--title",
                title,
                "--body",
                body,
                "--label",
                f"project:{project}",
                "--label",
                "message",
            ]

            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True, cwd=self.coord_path
            )
            issue_url = result.stdout.strip()

            return {"status": "sent", "issue_url": issue_url, "via": "issue"}

        except subprocess.CalledProcessError as e:
            return {"status": "error", "error": str(e)}

    def read_messages(self, project: str, via: str = "file") -> dict:
        """Read messages for a project."""
        if not self.coord_path.exists():
            return {"status": "error", "error": "Coordination repo not initialized"}

        # Pull latest
        self._git_pull()

        if via == "file":
            return self._read_via_file(project)
        elif via == "issue":
            return self._read_via_issue(project)
        else:
            return {"status": "error", "error": f"Unknown method: {via}"}

    def _read_via_file(self, project: str) -> dict:
        """Read messages from files."""
        messages_dir = self.coord_path / "projects" / project / "messages"

        if not messages_dir.exists():
            return {"status": "ok", "messages": [], "count": 0}

        messages = []
        for msg_file in sorted(messages_dir.glob("*.json")):
            try:
                msg_data = json.loads(msg_file.read_text())
                messages.append(msg_data)
            except Exception:
                continue

        return {"status": "ok", "messages": messages, "count": len(messages)}

    def _read_via_issue(self, project: str) -> dict:
        """Read messages from GitHub issues."""
        try:
            cmd = [
                "gh",
                "issue",
                "list",
                "--repo",
                self._get_remote_url().replace("https://github.com/", ""),
                "--label",
                f"project:{project}",
                "--label",
                "message",
                "--json",
                "number,title,body,createdAt,state",
                "--limit",
                "50",
            ]

            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True, cwd=self.coord_path
            )
            issues = json.loads(result.stdout)

            return {"status": "ok", "messages": issues, "count": len(issues)}

        except subprocess.CalledProcessError as e:
            return {"status": "error", "error": str(e)}

    def _git_commit(self, message: str, add_all: bool = False):
        """Commit changes to coordination repo."""
        if add_all:
            subprocess.run(["git", "add", "."], cwd=self.coord_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", message], cwd=self.coord_path, check=False
        )

    def _git_push(self):
        """Push to remote coordination repo."""
        subprocess.run(["git", "push"], cwd=self.coord_path, check=True)

    def _git_pull(self):
        """Pull from remote coordination repo."""
        subprocess.run(["git", "pull", "--rebase"], cwd=self.coord_path, check=True)

    def _get_remote_url(self) -> str:
        """Get remote URL of coordination repo."""
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=self.coord_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
