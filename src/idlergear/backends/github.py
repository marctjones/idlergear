"""GitHub backend implementation.

This module provides backend implementations that use GitHub Issues/Discussions
via the `gh` CLI tool.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


class GitHubBackendError(Exception):
    """Error from GitHub backend execution."""

    pass


def _run_gh_command(args: list[str], timeout: int = 30) -> str:
    """Run a gh CLI command.

    Args:
        args: Arguments to pass to gh
        timeout: Timeout in seconds

    Returns:
        Command stdout as string

    Raises:
        GitHubBackendError: If command fails
    """
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            # Provide more helpful error messages
            if "not authenticated" in stderr.lower():
                raise GitHubBackendError(
                    "GitHub CLI not authenticated. Run: gh auth login"
                )
            if "not a git repository" in stderr.lower():
                raise GitHubBackendError(
                    "Not in a git repository with GitHub remote"
                )
            raise GitHubBackendError(f"gh command failed: {stderr}")

        return result.stdout.strip()

    except FileNotFoundError:
        raise GitHubBackendError(
            "GitHub CLI (gh) not found. Install from: https://cli.github.com"
        )
    except subprocess.TimeoutExpired:
        raise GitHubBackendError(f"gh command timed out after {timeout}s")


def _parse_json(output: str) -> Any:
    """Parse JSON output from gh command."""
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        raise GitHubBackendError(f"Invalid JSON from gh: {e}")


def _extract_issue_number_from_url(url: str) -> int | None:
    """Extract issue number from a GitHub issue URL.

    Args:
        url: GitHub issue URL like "https://github.com/owner/repo/issues/123"

    Returns:
        Issue number as int, or None if parsing fails
    """
    # Match URLs like https://github.com/owner/repo/issues/123
    match = re.search(r"/issues/(\d+)(?:\s|$)", url)
    if match:
        return int(match.group(1))
    return None


def _map_issue_to_task(issue: dict[str, Any]) -> dict[str, Any]:
    """Map GitHub issue fields to IdlerGear task fields."""
    # Extract labels as list of strings
    labels = []
    if issue.get("labels"):
        labels = [l.get("name", l) if isinstance(l, dict) else l for l in issue["labels"]]

    # Extract assignees as list of strings
    assignees = []
    if issue.get("assignees"):
        assignees = [
            a.get("login", a) if isinstance(a, dict) else a
            for a in issue["assignees"]
        ]

    # Map priority from label (convention: priority:high, priority:medium, priority:low)
    priority = None
    for label in labels:
        if label.startswith("priority:"):
            priority = label.split(":", 1)[1]
            break

    return {
        "id": issue.get("number"),
        "title": issue.get("title", ""),
        "body": issue.get("body", ""),
        "state": issue.get("state", "open").lower(),
        "labels": [l for l in labels if not l.startswith("priority:")],
        "assignees": assignees,
        "priority": priority,
        "due": None,  # GitHub doesn't have native due dates
        "url": issue.get("url", ""),
        "created_at": issue.get("createdAt", ""),
        "updated_at": issue.get("updatedAt", ""),
    }


class GitHubTaskBackend:
    """GitHub Issues as task backend."""

    def __init__(self, project_path: Path | None = None):
        """Initialize GitHub task backend.

        Args:
            project_path: Optional project path (used to find git repo)
        """
        self.project_path = project_path

    def create(
        self,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        priority: str | None = None,
        due: str | None = None,
    ) -> dict[str, Any]:
        """Create a new GitHub issue."""
        args = ["issue", "create", "--title", title]

        # gh issue create requires --body when running non-interactively
        args.extend(["--body", body if body else ""])

        # Build label list including priority
        all_labels = list(labels or [])
        if priority:
            all_labels.append(f"priority:{priority}")

        for label in all_labels:
            args.extend(["--label", label])

        for assignee in assignees or []:
            args.extend(["--assignee", assignee])

        # gh issue create returns the issue URL, not JSON
        output = _run_gh_command(args)

        # Parse issue number from URL (e.g., "https://github.com/owner/repo/issues/123")
        issue_number = _extract_issue_number_from_url(output)
        if issue_number is None:
            raise GitHubBackendError(f"Could not parse issue number from: {output}")

        # Fetch full issue details
        return self.get(issue_number) or {"id": issue_number, "title": title}

    def list(self, state: str = "open") -> list[dict[str, Any]]:
        """List GitHub issues."""
        # Map IdlerGear states to GitHub states
        gh_state = state
        if state == "all":
            gh_state = "all"
        elif state in ("closed", "done", "complete"):
            gh_state = "closed"
        else:
            gh_state = "open"

        args = [
            "issue", "list",
            "--state", gh_state,
            "--json", "number,title,body,state,labels,assignees,url,createdAt,updatedAt",
            "--limit", "100",
        ]

        output = _run_gh_command(args)
        issues = _parse_json(output) or []
        return [_map_issue_to_task(issue) for issue in issues]

    def get(self, task_id: int) -> dict[str, Any] | None:
        """Get a GitHub issue by number."""
        args = [
            "issue", "view", str(task_id),
            "--json", "number,title,body,state,labels,assignees,url,createdAt,updatedAt",
        ]

        try:
            output = _run_gh_command(args)
            issue = _parse_json(output)
            return _map_issue_to_task(issue) if issue else None
        except GitHubBackendError:
            return None

    def update(
        self,
        task_id: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        priority: str | None = None,
        due: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a GitHub issue."""
        args = ["issue", "edit", str(task_id)]

        if title:
            args.extend(["--title", title])

        if body:
            args.extend(["--body", body])

        # Handle labels (note: gh edit --add-label, not --label)
        if labels is not None:
            for label in labels:
                args.extend(["--add-label", label])

        if priority:
            args.extend(["--add-label", f"priority:{priority}"])

        try:
            _run_gh_command(args)

            # Handle state change separately
            if state:
                if state in ("closed", "done", "complete"):
                    _run_gh_command(["issue", "close", str(task_id)])
                elif state in ("open", "reopen"):
                    _run_gh_command(["issue", "reopen", str(task_id)])

            return self.get(task_id)
        except GitHubBackendError:
            return None

    def close(self, task_id: int) -> dict[str, Any] | None:
        """Close a GitHub issue."""
        try:
            _run_gh_command(["issue", "close", str(task_id)])
            return self.get(task_id)
        except GitHubBackendError:
            return None

    def reopen(self, task_id: int) -> dict[str, Any] | None:
        """Reopen a GitHub issue."""
        try:
            _run_gh_command(["issue", "reopen", str(task_id)])
            return self.get(task_id)
        except GitHubBackendError:
            return None


class GitHubExploreBackend:
    """GitHub Issues (labeled) as exploration backend."""

    EXPLORE_LABEL = "exploration"

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path

    def _ensure_label_exists(self) -> None:
        """Ensure the exploration label exists."""
        try:
            _run_gh_command([
                "label", "create", self.EXPLORE_LABEL,
                "--description", "IdlerGear exploration",
                "--color", "0E8A16",
                "--force",
            ])
        except GitHubBackendError:
            pass  # Label might already exist

    def create(
        self,
        title: str,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Create a new exploration as a GitHub issue."""
        self._ensure_label_exists()

        args = [
            "issue", "create",
            "--title", title,
            "--label", self.EXPLORE_LABEL,
            # gh issue create requires --body when running non-interactively
            "--body", body if body else "",
        ]

        # gh issue create returns the issue URL, not JSON
        output = _run_gh_command(args)

        # Parse issue number from URL
        issue_number = _extract_issue_number_from_url(output)
        if issue_number is None:
            raise GitHubBackendError(f"Could not parse issue number from: {output}")

        # Fetch full issue details
        return self.get(issue_number) or {"id": issue_number, "title": title}

    def list(self, state: str = "open") -> list[dict[str, Any]]:
        """List explorations (issues with exploration label)."""
        gh_state = "all" if state == "all" else ("closed" if state == "closed" else "open")

        args = [
            "issue", "list",
            "--state", gh_state,
            "--label", self.EXPLORE_LABEL,
            "--json", "number,title,body,state,labels,url,createdAt,updatedAt",
            "--limit", "100",
        ]

        output = _run_gh_command(args)
        issues = _parse_json(output) or []
        return [self._map_to_exploration(issue) for issue in issues]

    def get(self, explore_id: int) -> dict[str, Any] | None:
        """Get an exploration by ID."""
        try:
            args = [
                "issue", "view", str(explore_id),
                "--json", "number,title,body,state,labels,url,createdAt,updatedAt",
            ]
            output = _run_gh_command(args)
            issue = _parse_json(output)
            return self._map_to_exploration(issue) if issue else None
        except GitHubBackendError:
            return None

    def update(
        self,
        explore_id: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an exploration."""
        args = ["issue", "edit", str(explore_id)]

        if title:
            args.extend(["--title", title])
        if body:
            args.extend(["--body", body])

        try:
            if title or body:
                _run_gh_command(args)

            if state:
                if state in ("closed", "done"):
                    _run_gh_command(["issue", "close", str(explore_id)])
                elif state in ("open", "reopen"):
                    _run_gh_command(["issue", "reopen", str(explore_id)])

            return self.get(explore_id)
        except GitHubBackendError:
            return None

    def close(self, explore_id: int) -> dict[str, Any] | None:
        """Close an exploration."""
        try:
            _run_gh_command(["issue", "close", str(explore_id)])
            return self.get(explore_id)
        except GitHubBackendError:
            return None

    def reopen(self, explore_id: int) -> dict[str, Any] | None:
        """Reopen an exploration."""
        try:
            _run_gh_command(["issue", "reopen", str(explore_id)])
            return self.get(explore_id)
        except GitHubBackendError:
            return None

    def _map_to_exploration(self, issue: dict[str, Any]) -> dict[str, Any]:
        """Map GitHub issue to exploration."""
        return {
            "id": issue.get("number"),
            "title": issue.get("title", ""),
            "body": issue.get("body", ""),
            "state": issue.get("state", "open").lower(),
            "url": issue.get("url", ""),
            "created_at": issue.get("createdAt", ""),
            "updated_at": issue.get("updatedAt", ""),
        }
