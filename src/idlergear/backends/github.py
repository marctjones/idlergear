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


class GitHubNoteBackend:
    """GitHub Issues (with 'note' label) as note backend."""

    NOTE_LABEL = "note"

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path
        self._next_local_id = 1  # For tracking notes locally

    def _ensure_label_exists(self) -> None:
        """Ensure the note label exists."""
        try:
            _run_gh_command([
                "label", "create", self.NOTE_LABEL,
                "--description", "IdlerGear note",
                "--color", "FBCA04",  # Yellow
                "--force",
            ])
        except GitHubBackendError:
            pass  # Label might already exist

    def _ensure_tag_labels_exist(self, tags: list[str]) -> None:
        """Ensure tag labels exist (tag:explore, tag:idea, etc.)."""
        for tag in tags:
            label_name = f"tag:{tag}"
            try:
                _run_gh_command([
                    "label", "create", label_name,
                    "--description", f"IdlerGear note tag: {tag}",
                    "--color", "C2E0C6",  # Light green
                    "--force",
                ])
            except GitHubBackendError:
                pass  # Label might already exist

    def create(
        self,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new note as a GitHub issue with optional tags."""
        self._ensure_label_exists()
        if tags:
            self._ensure_tag_labels_exist(tags)

        # Use first line as title, rest as body
        lines = content.strip().split('\n', 1)
        title = lines[0][:80] if lines else content[:80]
        body = lines[1] if len(lines) > 1 else ""

        args = [
            "issue", "create",
            "--title", title,
            "--label", self.NOTE_LABEL,
            "--body", body,
        ]

        # Add tag labels
        for tag in (tags or []):
            args.extend(["--label", f"tag:{tag}"])

        output = _run_gh_command(args)

        issue_number = _extract_issue_number_from_url(output)
        if issue_number is None:
            raise GitHubBackendError(f"Could not parse issue number from: {output}")

        return self.get(issue_number) or {"id": issue_number, "content": content, "tags": tags or []}

    def list(self, tag: str | None = None) -> list[dict[str, Any]]:
        """List notes, optionally filtered by tag."""
        args = [
            "issue", "list",
            "--state", "open",
            "--label", self.NOTE_LABEL,
            "--json", "number,title,body,labels,createdAt,updatedAt",
            "--limit", "100",
        ]

        # Filter by tag if specified
        if tag:
            args.extend(["--label", f"tag:{tag}"])

        output = _run_gh_command(args)
        issues = _parse_json(output) or []
        return [self._map_to_note(issue) for issue in issues]

    def get(self, note_id: int) -> dict[str, Any] | None:
        """Get a note by ID."""
        try:
            args = [
                "issue", "view", str(note_id),
                "--json", "number,title,body,state,labels,createdAt,updatedAt",
            ]
            output = _run_gh_command(args)
            issue = _parse_json(output)
            return self._map_to_note(issue) if issue else None
        except GitHubBackendError:
            return None

    def delete(self, note_id: int) -> bool:
        """Delete a note (close the issue)."""
        try:
            _run_gh_command(["issue", "close", str(note_id)])
            return True
        except GitHubBackendError:
            return False

    def promote(self, note_id: int, to_type: str) -> dict[str, Any] | None:
        """Promote a note to another type.

        For GitHub, this removes the 'note' label and adds appropriate label.
        """
        note = self.get(note_id)
        if not note:
            return None

        try:
            # Remove note label
            _run_gh_command([
                "issue", "edit", str(note_id),
                "--remove-label", self.NOTE_LABEL,
            ])

            # Add appropriate label based on target type
            if to_type == "task":
                # Just remove the note label, it becomes a regular issue/task
                pass
            elif to_type == "explore":
                _run_gh_command([
                    "issue", "edit", str(note_id),
                    "--add-label", "exploration",
                ])
            elif to_type == "reference":
                # For reference, we'd need to create a wiki page
                # For now, just remove the note label
                pass

            return self.get(note_id)
        except GitHubBackendError:
            return None

    def _map_to_note(self, issue: dict[str, Any]) -> dict[str, Any]:
        """Map GitHub issue to note."""
        title = issue.get("title", "")
        body = issue.get("body", "")
        content = f"{title}\n{body}".strip() if body else title

        # Extract tags from labels (format: tag:explore, tag:idea, etc.)
        tags = []
        if issue.get("labels"):
            for label in issue["labels"]:
                label_name = label.get("name", label) if isinstance(label, dict) else label
                if label_name.startswith("tag:"):
                    tags.append(label_name[4:])  # Remove "tag:" prefix

        return {
            "id": issue.get("number"),
            "content": content,
            "tags": tags,
            "created_at": issue.get("createdAt", ""),
            "updated_at": issue.get("updatedAt", ""),
        }


class GitHubVisionBackend:
    """GitHub repository file as vision backend.

    Syncs vision content to/from VISION.md in the repository root.
    Auto-commit behavior is configurable via github.vision_auto_commit config.
    """

    VISION_FILE = "VISION.md"

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path

    def _should_auto_commit(self) -> bool:
        """Check if auto-commit is enabled (default: True for backward compat)."""
        try:
            from idlergear.config import get_config
            value = get_config("github.vision_auto_commit", project_path=self.project_path)
            if value is None:
                return True  # Default to auto-commit for backward compatibility
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes")
        except Exception:
            return True  # Default to auto-commit

    def get(self) -> str | None:
        """Get the vision from GitHub (VISION.md in repo)."""
        try:
            # Try to read the file from the remote default branch
            output = _run_gh_command([
                "api", "-X", "GET",
                "/repos/{owner}/{repo}/contents/" + self.VISION_FILE,
                "--jq", ".content",
            ])

            if output:
                import base64
                # GitHub API returns base64-encoded content
                content = base64.b64decode(output).decode("utf-8")
                return content
        except GitHubBackendError:
            pass

        # Fall back to local file if exists
        if self.project_path:
            vision_path = self.project_path / self.VISION_FILE
            if vision_path.exists():
                return vision_path.read_text()

        return None

    def set(self, content: str) -> None:
        """Set the vision (write to local VISION.md and optionally commit).

        Note: This writes locally. Use git push to sync to GitHub.
        Auto-commit can be disabled via config: github.vision_auto_commit = false
        """
        if not self.project_path:
            raise GitHubBackendError("Project path required to set vision")

        vision_path = self.project_path / self.VISION_FILE
        vision_path.write_text(content)

        # Only commit if auto-commit is enabled
        if self._should_auto_commit():
            try:
                subprocess.run(
                    ["git", "add", self.VISION_FILE],
                    cwd=self.project_path,
                    capture_output=True,
                    check=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", "Update project vision"],
                    cwd=self.project_path,
                    capture_output=True,
                    check=False,  # Don't fail if nothing to commit
                )
            except subprocess.CalledProcessError:
                pass  # Git operations are optional


class GitHubReferenceBackend:
    """GitHub Wiki as reference backend.

    Uses gh api to manage wiki pages.
    """

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path
        self._wiki_enabled: bool | None = None

    def _check_wiki_enabled(self) -> bool:
        """Check if wiki is enabled for the repository."""
        if self._wiki_enabled is not None:
            return self._wiki_enabled

        try:
            output = _run_gh_command([
                "api", "/repos/{owner}/{repo}",
                "--jq", ".has_wiki",
            ])
            self._wiki_enabled = output.strip().lower() == "true"
        except GitHubBackendError:
            self._wiki_enabled = False

        return self._wiki_enabled

    def add(self, title: str, body: str | None = None) -> dict[str, Any]:
        """Add a new reference document.

        Note: GitHub Wiki API is limited. This creates a local wiki page
        that must be pushed manually.
        """
        # Wiki operations require cloning the wiki repo
        # For now, create locally and provide instructions
        if not self._check_wiki_enabled():
            raise GitHubBackendError(
                "Wiki not enabled for this repository. "
                "Enable it in Settings → Features → Wiki"
            )

        # Sanitize title for filename
        filename = title.replace(" ", "-").replace("/", "-") + ".md"
        content = f"# {title}\n\n{body or ''}"

        return {
            "id": hash(title) % 10000,  # Fake ID
            "title": title,
            "body": body or "",
            "filename": filename,
            "content": content,
            "note": "Wiki page created. Clone wiki repo and push to sync.",
        }

    def list(self) -> list[dict[str, Any]]:
        """List reference documents from wiki.

        Note: GitHub API doesn't provide wiki listing.
        This returns empty for now.
        """
        # GitHub doesn't have a wiki list API
        # Would need to clone wiki repo to list pages
        return []

    def get(self, title: str) -> dict[str, Any] | None:
        """Get a reference by title."""
        # Would need to clone wiki repo to get content
        return None

    def get_by_id(self, ref_id: int) -> dict[str, Any] | None:
        """Get a reference by ID."""
        return None

    def update(
        self,
        title: str,
        new_title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a reference document."""
        return None

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search reference documents."""
        # GitHub code search could work here, but requires authentication
        return []


class GitHubPlanBackend:
    """GitHub Projects (v2) as plan backend.

    Uses gh api to manage GitHub Projects.
    Current plan selection is persisted to config.
    """

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path

    def _get_current_plan_from_config(self) -> str | None:
        """Get current plan from IdlerGear config."""
        try:
            from idlergear.config import get_config
            return get_config("github.current_plan", project_path=self.project_path)
        except Exception:
            return None

    def _set_current_plan_in_config(self, plan_name: str | None) -> None:
        """Save current plan to IdlerGear config."""
        try:
            from idlergear.config import set_config
            if plan_name:
                set_config("github.current_plan", plan_name, project_path=self.project_path)
            # Note: We don't clear the config if plan_name is None
        except Exception:
            pass  # Config operations are optional

    def _get_owner_repo(self) -> tuple[str, str]:
        """Get owner and repo from current directory."""
        try:
            output = _run_gh_command([
                "repo", "view", "--json", "owner,name",
            ])
            data = _parse_json(output)
            if data:
                owner = data.get("owner", {})
                if isinstance(owner, dict):
                    owner = owner.get("login", "")
                return owner, data.get("name", "")
        except GitHubBackendError:
            pass
        return "", ""

    def create(
        self,
        name: str,
        title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Create a new GitHub Project."""
        owner, repo = self._get_owner_repo()
        if not owner:
            raise GitHubBackendError("Could not determine repository owner")

        project_title = title or name

        try:
            # Create project using gh api
            # Note: Projects v2 uses GraphQL
            mutation = """
            mutation($ownerId: ID!, $title: String!) {
                createProjectV2(input: {ownerId: $ownerId, title: $title}) {
                    projectV2 {
                        id
                        number
                        title
                    }
                }
            }
            """

            # First get the owner ID
            owner_query = _run_gh_command([
                "api", "graphql", "-f",
                f"query={{user(login: \"{owner}\") {{id}}}}",
                "--jq", ".data.user.id",
            ])

            if not owner_query:
                # Try organization
                owner_query = _run_gh_command([
                    "api", "graphql", "-f",
                    f"query={{organization(login: \"{owner}\") {{id}}}}",
                    "--jq", ".data.organization.id",
                ])

            if not owner_query:
                raise GitHubBackendError("Could not get owner ID")

            # Create the project
            output = _run_gh_command([
                "api", "graphql",
                "-f", f"query={mutation}",
                "-F", f"ownerId={owner_query.strip()}",
                "-F", f"title={project_title}",
            ])

            result = _parse_json(output)
            project = result.get("data", {}).get("createProjectV2", {}).get("projectV2", {})

            return {
                "name": name,
                "title": project.get("title", project_title),
                "id": project.get("number"),
                "body": body or "",
                "current": False,
            }

        except GitHubBackendError as e:
            raise GitHubBackendError(f"Failed to create project: {e}")

    def list(self) -> list[dict[str, Any]]:
        """List all GitHub Projects for the repository."""
        try:
            output = _run_gh_command([
                "project", "list",
                "--format", "json",
            ])

            projects = _parse_json(output)
            if not projects:
                return []

            result = []
            if isinstance(projects, dict) and "projects" in projects:
                projects = projects["projects"]

            current_plan = self._get_current_plan_from_config()

            for p in projects:
                plan_name = p.get("title", "").lower().replace(" ", "-")
                result.append({
                    "name": plan_name,
                    "title": p.get("title", ""),
                    "id": p.get("number"),
                    "body": "",
                    "current": plan_name == current_plan,
                    "url": p.get("url", ""),
                })

            return result

        except GitHubBackendError:
            return []

    def get(self, name: str) -> dict[str, Any] | None:
        """Get a plan by name."""
        plans = self.list()
        for plan in plans:
            if plan.get("name") == name or plan.get("title", "").lower() == name.lower():
                return plan
        return None

    def get_current(self) -> dict[str, Any] | None:
        """Get the current active plan."""
        current_plan = self._get_current_plan_from_config()
        if not current_plan:
            return None
        return self.get(current_plan)

    def switch(self, name: str) -> dict[str, Any] | None:
        """Switch to a plan and persist the selection."""
        plan = self.get(name)
        if plan:
            plan_name = plan.get("name")
            self._set_current_plan_in_config(plan_name)
            plan["current"] = True
            return plan
        return None

    def update(
        self,
        name: str,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a plan."""
        # GitHub Projects v2 update is complex via GraphQL
        # For now, return the existing plan
        return self.get(name)
