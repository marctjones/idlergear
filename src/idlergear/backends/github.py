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
                raise GitHubBackendError("Not in a git repository with GitHub remote")
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
        labels = [
            l.get("name", l) if isinstance(l, dict) else l for l in issue["labels"]
        ]

    # Extract assignees as list of strings
    assignees = []
    if issue.get("assignees"):
        assignees = [
            a.get("login", a) if isinstance(a, dict) else a for a in issue["assignees"]
        ]

    # Map priority from label (convention: priority:high, priority:medium, priority:low)
    priority = None
    for label in labels:
        if label.startswith("priority:"):
            priority = label.split(":", 1)[1]
            break

    # Extract milestone if present
    milestone = None
    if issue.get("milestone"):
        milestone_data = issue["milestone"]
        if isinstance(milestone_data, dict):
            milestone = {
                "number": milestone_data.get("number"),
                "title": milestone_data.get("title"),
            }

    return {
        "id": issue.get("number"),
        "title": issue.get("title", ""),
        "body": issue.get("body", ""),
        "state": issue.get("state", "open").lower(),
        "labels": [l for l in labels if not l.startswith("priority:")],
        "assignees": assignees,
        "priority": priority,
        "due": None,  # GitHub doesn't have native due dates
        "milestone": milestone,
        "url": issue.get("url", ""),
        "created_at": issue.get("createdAt", ""),
        "updated_at": issue.get("updatedAt", ""),
    }


# Standard IdlerGear labels with colors and descriptions
IDLERGEAR_LABELS = {
    "exploration": {"color": "0E8A16", "description": "IdlerGear exploration"},
    "note": {"color": "FBCA04", "description": "IdlerGear note"},
    "tag": {"color": "C2E0C6", "description": "IdlerGear note tag"},
}


class LabelManager:
    """Centralized GitHub label management with caching."""

    def __init__(self):
        """Initialize label manager with empty cache."""
        self._label_cache: dict[str, bool] | None = None

    def _load_labels(self) -> dict[str, bool]:
        """Load all existing labels into cache."""
        if self._label_cache is not None:
            return self._label_cache

        try:
            output = _run_gh_command(["label", "list", "--json", "name"])
            labels = _parse_json(output) or []
            self._label_cache = {label["name"]: True for label in labels}
        except GitHubBackendError:
            self._label_cache = {}

        return self._label_cache

    def label_exists(self, name: str) -> bool:
        """Check if a label exists (cached)."""
        cache = self._load_labels()
        return name in cache

    def ensure_label(self, name: str, color: str, description: str) -> None:
        """Ensure a label exists, creating it if necessary.

        Args:
            name: Label name
            color: Hex color code (without #)
            description: Label description
        """
        # Check cache first
        if self.label_exists(name):
            return

        try:
            _run_gh_command(
                [
                    "label",
                    "create",
                    name,
                    "--description",
                    description,
                    "--color",
                    color,
                    "--force",
                ]
            )
            # Update cache
            if self._label_cache is not None:
                self._label_cache[name] = True
        except GitHubBackendError:
            # Label might already exist, update cache anyway
            if self._label_cache is not None:
                self._label_cache[name] = True

    def ensure_standard_label(self, label_type: str) -> None:
        """Ensure a standard IdlerGear label exists.

        Args:
            label_type: Type of label (exploration, note, tag)
        """
        if label_type not in IDLERGEAR_LABELS:
            raise ValueError(f"Unknown standard label type: {label_type}")

        config = IDLERGEAR_LABELS[label_type]
        self.ensure_label(label_type, config["color"], config["description"])

    def ensure_tag_label(self, tag: str) -> None:
        """Ensure a tag label exists (format: tag:tagname).

        Args:
            tag: Tag name (e.g., 'explore', 'idea')
        """
        label_name = f"tag:{tag}"
        tag_config = IDLERGEAR_LABELS["tag"]
        self.ensure_label(
            label_name,
            tag_config["color"],
            f"IdlerGear note tag: {tag}",
        )

    def invalidate_cache(self) -> None:
        """Invalidate the label cache."""
        self._label_cache = None


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
        milestone: str | None = None,
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

        if milestone:
            args.extend(["--milestone", milestone])

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
            "issue",
            "list",
            "--state",
            gh_state,
            "--json",
            "number,title,body,state,labels,assignees,milestone,url,createdAt,updatedAt",
            "--limit",
            "100",
        ]

        output = _run_gh_command(args)
        issues = _parse_json(output) or []
        return [_map_issue_to_task(issue) for issue in issues]

    def get(self, task_id: int) -> dict[str, Any] | None:
        """Get a GitHub issue by number."""
        args = [
            "issue",
            "view",
            str(task_id),
            "--json",
            "number,title,body,state,labels,assignees,milestone,url,createdAt,updatedAt",
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

    def close(self, task_id: int, comment: str | None = None) -> dict[str, Any] | None:
        """Close a GitHub issue.

        Args:
            task_id: Issue number to close
            comment: Optional closing comment
        """
        try:
            cmd = ["issue", "close", str(task_id)]
            if comment:
                cmd.extend(["--comment", comment])
            _run_gh_command(cmd)
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
        self.label_manager = LabelManager()

    def create(
        self,
        title: str,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Create a new exploration as a GitHub issue."""
        self.label_manager.ensure_standard_label("exploration")

        args = [
            "issue",
            "create",
            "--title",
            title,
            "--label",
            self.EXPLORE_LABEL,
            # gh issue create requires --body when running non-interactively
            "--body",
            body if body else "",
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
        gh_state = (
            "all" if state == "all" else ("closed" if state == "closed" else "open")
        )

        args = [
            "issue",
            "list",
            "--state",
            gh_state,
            "--label",
            self.EXPLORE_LABEL,
            "--json",
            "number,title,body,state,labels,url,createdAt,updatedAt",
            "--limit",
            "100",
        ]

        output = _run_gh_command(args)
        issues = _parse_json(output) or []
        return [self._map_to_exploration(issue) for issue in issues]

    def get(self, explore_id: int) -> dict[str, Any] | None:
        """Get an exploration by ID."""
        try:
            args = [
                "issue",
                "view",
                str(explore_id),
                "--json",
                "number,title,body,state,labels,url,createdAt,updatedAt",
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
        self.label_manager = LabelManager()

    def create(
        self,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new note as a GitHub issue with optional tags."""
        self.label_manager.ensure_standard_label("note")
        if tags:
            for tag in tags:
                self.label_manager.ensure_tag_label(tag)

        # Use first line as title, rest as body
        lines = content.strip().split("\n", 1)
        title = lines[0][:80] if lines else content[:80]
        body = lines[1] if len(lines) > 1 else ""

        args = [
            "issue",
            "create",
            "--title",
            title,
            "--label",
            self.NOTE_LABEL,
            "--body",
            body,
        ]

        # Add tag labels
        for tag in tags or []:
            args.extend(["--label", f"tag:{tag}"])

        output = _run_gh_command(args)

        issue_number = _extract_issue_number_from_url(output)
        if issue_number is None:
            raise GitHubBackendError(f"Could not parse issue number from: {output}")

        return self.get(issue_number) or {
            "id": issue_number,
            "content": content,
            "tags": tags or [],
        }

    def list(self, tag: str | None = None) -> list[dict[str, Any]]:
        """List notes, optionally filtered by tag."""
        args = [
            "issue",
            "list",
            "--state",
            "open",
            "--label",
            self.NOTE_LABEL,
            "--json",
            "number,title,body,labels,createdAt,updatedAt",
            "--limit",
            "100",
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
                "issue",
                "view",
                str(note_id),
                "--json",
                "number,title,body,state,labels,createdAt,updatedAt",
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
            _run_gh_command(
                [
                    "issue",
                    "edit",
                    str(note_id),
                    "--remove-label",
                    self.NOTE_LABEL,
                ]
            )

            # Add appropriate label based on target type
            if to_type == "task":
                # Just remove the note label, it becomes a regular issue/task
                pass
            elif to_type == "explore":
                _run_gh_command(
                    [
                        "issue",
                        "edit",
                        str(note_id),
                        "--add-label",
                        "exploration",
                    ]
                )
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
                label_name = (
                    label.get("name", label) if isinstance(label, dict) else label
                )
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

            value = get_config(
                "github.vision_auto_commit", project_path=self.project_path
            )
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
            output = _run_gh_command(
                [
                    "api",
                    "-X",
                    "GET",
                    "/repos/{owner}/{repo}/contents/" + self.VISION_FILE,
                    "--jq",
                    ".content",
                ]
            )

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

    Uses WikiSync to clone/pull wiki repo and manage pages locally.
    Changes are automatically pushed to GitHub.
    """

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self._wiki_enabled: bool | None = None
        self._wiki_sync = None
        self._title_to_id: dict[str, int] = {}
        self._next_id = 1

    def _get_wiki_sync(self):
        """Get or create WikiSync instance."""
        if self._wiki_sync is None:
            from idlergear.wiki import WikiSync

            self._wiki_sync = WikiSync(self.project_path)
        return self._wiki_sync

    def _ensure_wiki_cloned(self) -> bool:
        """Ensure wiki repo is cloned and up to date."""
        wiki_sync = self._get_wiki_sync()
        if not wiki_sync.wiki_dir.exists():
            return wiki_sync.clone_wiki()
        return wiki_sync.pull_wiki()

    def _check_wiki_enabled(self) -> bool:
        """Check if wiki is enabled for the repository."""
        if self._wiki_enabled is not None:
            return self._wiki_enabled

        try:
            output = _run_gh_command(
                [
                    "api",
                    "/repos/{owner}/{repo}",
                    "--jq",
                    ".has_wiki",
                ]
            )
            self._wiki_enabled = output.strip().lower() == "true"
        except GitHubBackendError:
            self._wiki_enabled = False

        return self._wiki_enabled

    def _get_id_for_title(self, title: str) -> int:
        """Get or create a stable ID for a title."""
        if title not in self._title_to_id:
            self._title_to_id[title] = self._next_id
            self._next_id += 1
        return self._title_to_id[title]

    def add(self, title: str, body: str | None = None) -> dict[str, Any]:
        """Add a new reference document to GitHub Wiki.

        Creates the wiki page locally and pushes to GitHub.
        """
        if not self._check_wiki_enabled():
            raise GitHubBackendError(
                "Wiki not enabled for this repository. "
                "Enable it in Settings → Features → Wiki"
            )

        if not self._ensure_wiki_cloned():
            raise GitHubBackendError("Failed to clone/pull wiki repository")

        wiki_sync = self._get_wiki_sync()

        # Create wiki page
        filename = title.replace(" ", "-").replace("/", "-") + ".md"
        wiki_path = wiki_sync.wiki_dir / filename
        content = f"# {title}\n\n{body or ''}"
        wiki_path.write_text(content, encoding="utf-8")

        # Push to GitHub
        if not wiki_sync.push_wiki():
            raise GitHubBackendError("Failed to push wiki changes to GitHub")

        ref_id = self._get_id_for_title(title)
        return {
            "id": ref_id,
            "title": title,
            "body": body or "",
            "path": str(wiki_path),
        }

    def list(self) -> list[dict[str, Any]]:
        """List reference documents from GitHub Wiki."""
        if not self._check_wiki_enabled():
            return []

        if not self._ensure_wiki_cloned():
            return []

        wiki_sync = self._get_wiki_sync()
        pages = wiki_sync.list_wiki_pages()

        results = []
        for page in pages:
            ref_id = self._get_id_for_title(page.title)
            # Extract body (skip the header line if present)
            body = page.content
            if body.startswith(f"# {page.title}"):
                body = body[len(f"# {page.title}") :].strip()

            results.append(
                {
                    "id": ref_id,
                    "title": page.title,
                    "body": body,
                    "path": str(page.path),
                }
            )

        return sorted(results, key=lambda r: r.get("title", "").lower())

    def get(self, title: str) -> dict[str, Any] | None:
        """Get a reference by title from GitHub Wiki."""
        if not self._check_wiki_enabled():
            return None

        if not self._ensure_wiki_cloned():
            return None

        wiki_sync = self._get_wiki_sync()

        # Look for matching page
        filename = title.replace(" ", "-").replace("/", "-") + ".md"
        wiki_path = wiki_sync.wiki_dir / filename

        if not wiki_path.exists():
            # Try case-insensitive search
            for page in wiki_sync.list_wiki_pages():
                if page.title.lower() == title.lower():
                    wiki_path = page.path
                    title = page.title
                    break
            else:
                return None

        content = wiki_path.read_text(encoding="utf-8")
        # Extract body (skip the header line if present)
        body = content
        if body.startswith(f"# {title}"):
            body = body[len(f"# {title}") :].strip()

        ref_id = self._get_id_for_title(title)
        return {
            "id": ref_id,
            "title": title,
            "body": body,
            "path": str(wiki_path),
        }

    def get_by_id(self, ref_id: int) -> dict[str, Any] | None:
        """Get a reference by ID."""
        # Search through title-to-id mapping
        for title, tid in self._title_to_id.items():
            if tid == ref_id:
                return self.get(title)
        return None

    def update(
        self,
        title: str,
        new_title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a reference document in GitHub Wiki."""
        if not self._check_wiki_enabled():
            return None

        if not self._ensure_wiki_cloned():
            return None

        wiki_sync = self._get_wiki_sync()

        # Find existing page
        filename = title.replace(" ", "-").replace("/", "-") + ".md"
        wiki_path = wiki_sync.wiki_dir / filename

        if not wiki_path.exists():
            return None

        # Read existing content
        existing_content = wiki_path.read_text(encoding="utf-8")

        # Update content
        final_title = new_title or title
        if body is not None:
            content = f"# {final_title}\n\n{body}"
        else:
            # Keep existing body, just update title if changed
            if existing_content.startswith(f"# {title}"):
                content = f"# {final_title}" + existing_content[len(f"# {title}") :]
            else:
                content = existing_content

        # Handle rename
        if new_title and new_title != title:
            wiki_path.unlink()
            new_filename = new_title.replace(" ", "-").replace("/", "-") + ".md"
            wiki_path = wiki_sync.wiki_dir / new_filename
            # Update ID mapping
            if title in self._title_to_id:
                self._title_to_id[new_title] = self._title_to_id.pop(title)

        wiki_path.write_text(content, encoding="utf-8")

        # Push changes
        if not wiki_sync.push_wiki():
            raise GitHubBackendError("Failed to push wiki changes to GitHub")

        ref_id = self._get_id_for_title(final_title)
        return {
            "id": ref_id,
            "title": final_title,
            "body": body or "",
            "path": str(wiki_path),
        }

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search reference documents in GitHub Wiki."""
        all_refs = self.list()
        query_lower = query.lower()

        results = []
        for ref in all_refs:
            title_match = query_lower in ref.get("title", "").lower()
            body_match = ref.get("body") and query_lower in ref["body"].lower()

            if title_match or body_match:
                results.append(ref)

        return results


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
                set_config(
                    "github.current_plan", plan_name, project_path=self.project_path
                )
            # Note: We don't clear the config if plan_name is None
        except Exception:
            pass  # Config operations are optional

    def _get_owner_repo(self) -> tuple[str, str]:
        """Get owner and repo from current directory."""
        try:
            output = _run_gh_command(
                [
                    "repo",
                    "view",
                    "--json",
                    "owner,name",
                ]
            )
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
            owner_query = _run_gh_command(
                [
                    "api",
                    "graphql",
                    "-f",
                    f'query={{user(login: "{owner}") {{id}}}}',
                    "--jq",
                    ".data.user.id",
                ]
            )

            if not owner_query:
                # Try organization
                owner_query = _run_gh_command(
                    [
                        "api",
                        "graphql",
                        "-f",
                        f'query={{organization(login: "{owner}") {{id}}}}',
                        "--jq",
                        ".data.organization.id",
                    ]
                )

            if not owner_query:
                raise GitHubBackendError("Could not get owner ID")

            # Create the project
            output = _run_gh_command(
                [
                    "api",
                    "graphql",
                    "-f",
                    f"query={mutation}",
                    "-F",
                    f"ownerId={owner_query.strip()}",
                    "-F",
                    f"title={project_title}",
                ]
            )

            result = _parse_json(output)
            project = (
                result.get("data", {}).get("createProjectV2", {}).get("projectV2", {})
            )

            return {
                "name": name,
                "title": project.get("title", project_title),
                "id": project.get("number"),
                "body": body or "",
                "current": False,
                "state": "active",
                "created": project.get("createdAt", ""),
            }

        except GitHubBackendError as e:
            raise GitHubBackendError(f"Failed to create project: {e}")

    def list(self) -> list[dict[str, Any]]:
        """List all GitHub Projects for the repository."""
        try:
            output = _run_gh_command(
                [
                    "project",
                    "list",
                    "--format",
                    "json",
                ]
            )

            projects = _parse_json(output)
            if not projects:
                return []

            result = []
            if isinstance(projects, dict) and "projects" in projects:
                projects = projects["projects"]

            current_plan = self._get_current_plan_from_config()

            for p in projects:
                plan_name = p.get("title", "").lower().replace(" ", "-")
                result.append(
                    {
                        "name": plan_name,
                        "title": p.get("title", ""),
                        "id": p.get("number"),
                        "body": "",
                        "current": plan_name == current_plan,
                        "state": "active" if not p.get("closed") else "closed",
                        "created": p.get("createdAt", ""),
                        "url": p.get("url", ""),
                    }
                )

            return result

        except GitHubBackendError:
            return []

    def get(self, name: str) -> dict[str, Any] | None:
        """Get a plan by name."""
        plans = self.list()
        for plan in plans:
            if (
                plan.get("name") == name
                or plan.get("title", "").lower() == name.lower()
            ):
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


    def delete(self, name: str) -> bool:
        """Delete a plan (GitHub Project)."""
        plan = self.get(name)
        if not plan:
            return False

        try:
            _run_gh_command(["project", "delete", str(plan["id"]), "--format", "json"])
            return True
        except GitHubBackendError:
            return False


class GitHubDiscussionsNoteBackend:
    """GitHub Discussions as note backend.

    Uses GitHub Discussions GraphQL API to store notes. Notes are stored in
    a configurable category (default: "Ideas"). Tags are mapped to labels.

    This provides cleaner separation between actionable work (Issues) and
    ephemeral thinking/notes (Discussions).
    """

    DEFAULT_CATEGORY = "Ideas"  # Use Ideas category if Notes doesn't exist

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path
        self._repo_id: str | None = None
        self._category_id: str | None = None
        self._discussions_enabled: bool | None = None
        self.label_manager = LabelManager()

    def _get_repo_id(self) -> str:
        """Get the repository node ID for GraphQL."""
        if self._repo_id:
            return self._repo_id

        output = _run_gh_command(
            [
                "api",
                "graphql",
                "-f",
                'query={repository(owner:"{owner}", name:"{repo}") { id }}',
                "--jq",
                ".data.repository.id",
            ]
        )

        if not output.strip():
            raise GitHubBackendError("Could not get repository ID")

        self._repo_id = output.strip()
        return self._repo_id

    def _get_category_id(self, category_name: str | None = None) -> str:
        """Get the discussion category node ID.

        Tries to find a "Notes" category first, falls back to "Ideas".
        """
        if self._category_id and category_name is None:
            return self._category_id

        # Query all discussion categories
        output = _run_gh_command(
            [
                "api",
                "graphql",
                "-f",
                'query={repository(owner:"{owner}", name:"{repo}") { '
                "discussionCategories(first:20) { nodes { id name } } }}",
                "--jq",
                ".data.repository.discussionCategories.nodes",
            ]
        )

        categories = _parse_json(output) or []
        target_name = category_name or "Notes"

        # Try to find the target category
        for cat in categories:
            if cat.get("name", "").lower() == target_name.lower():
                self._category_id = cat["id"]
                return self._category_id

        # Fall back to Ideas category
        for cat in categories:
            if cat.get("name", "").lower() == self.DEFAULT_CATEGORY.lower():
                self._category_id = cat["id"]
                return self._category_id

        # Use the first category if no match
        if categories:
            self._category_id = categories[0]["id"]
            return self._category_id

        raise GitHubBackendError("No discussion categories found. Enable discussions.")

    def _check_discussions_enabled(self) -> bool:
        """Check if discussions are enabled for the repository."""
        if self._discussions_enabled is not None:
            return self._discussions_enabled

        try:
            output = _run_gh_command(
                [
                    "api",
                    "/repos/{owner}/{repo}",
                    "--jq",
                    ".has_discussions",
                ]
            )
            self._discussions_enabled = output.strip().lower() == "true"
        except GitHubBackendError:
            self._discussions_enabled = False

        return self._discussions_enabled

    def create(
        self,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new note as a GitHub Discussion."""
        if not self._check_discussions_enabled():
            raise GitHubBackendError(
                "Discussions not enabled. Enable in Settings → Features → Discussions"
            )

        if tags:
            for tag in tags:
                self.label_manager.ensure_tag_label(tag)

        # Use first line as title, rest as body
        lines = content.strip().split("\n", 1)
        title = lines[0][:200] if lines else content[:200]
        body = lines[1].strip() if len(lines) > 1 else ""

        # Add tags as metadata at the end of body if present
        if tags:
            tags_line = f"\n\n---\n_Tags: {', '.join(tags)}_"
            body += tags_line

        repo_id = self._get_repo_id()
        category_id = self._get_category_id()

        # Create discussion using GraphQL mutation
        mutation = """
        mutation($repoId: ID!, $catId: ID!, $title: String!, $body: String!) {
            createDiscussion(input: {
                repositoryId: $repoId,
                categoryId: $catId,
                title: $title,
                body: $body
            }) {
                discussion {
                    id
                    number
                    title
                    body
                    createdAt
                    updatedAt
                    url
                }
            }
        }
        """

        output = _run_gh_command(
            [
                "api",
                "graphql",
                "-f",
                f"query={mutation}",
                "-F",
                f"repoId={repo_id}",
                "-F",
                f"catId={category_id}",
                "-F",
                f"title={title}",
                "-F",
                f"body={body}",
            ]
        )

        result = _parse_json(output)
        discussion = (
            result.get("data", {}).get("createDiscussion", {}).get("discussion", {})
        )

        if not discussion:
            errors = result.get("errors", [])
            if errors:
                raise GitHubBackendError(
                    f"Failed to create discussion: {errors[0].get('message', 'Unknown error')}"
                )
            raise GitHubBackendError("Failed to create discussion")

        return self._map_to_note(discussion, tags or [])

    def list(self, tag: str | None = None) -> list[dict[str, Any]]:
        """List notes (discussions), optionally filtered by tag."""
        if not self._check_discussions_enabled():
            return []

        try:
            category_id = self._get_category_id()
        except GitHubBackendError:
            return []

        # Query discussions in the notes category
        query = """
        query($categoryId: ID!) {
            repository(owner: "{owner}", name: "{repo}") {
                discussions(first: 100, categoryId: $categoryId, orderBy: {field: CREATED_AT, direction: DESC}) {
                    nodes {
                        id
                        number
                        title
                        body
                        createdAt
                        updatedAt
                        url
                    }
                }
            }
        }
        """

        output = _run_gh_command(
            [
                "api",
                "graphql",
                "-f",
                f"query={query}",
                "-F",
                f"categoryId={category_id}",
                "--jq",
                ".data.repository.discussions.nodes",
            ]
        )

        discussions = _parse_json(output) or []
        notes = []

        for disc in discussions:
            note = self._map_to_note(disc)
            # Filter by tag if specified
            if tag is None or tag in note.get("tags", []):
                notes.append(note)

        return notes

    def get(self, note_id: int) -> dict[str, Any] | None:
        """Get a note (discussion) by number."""
        if not self._check_discussions_enabled():
            return None

        query = """
        query($number: Int!) {
            repository(owner: "{owner}", name: "{repo}") {
                discussion(number: $number) {
                    id
                    number
                    title
                    body
                    createdAt
                    updatedAt
                    url
                    closed
                }
            }
        }
        """

        try:
            output = _run_gh_command(
                [
                    "api",
                    "graphql",
                    "-f",
                    f"query={query}",
                    "-F",
                    f"number={note_id}",
                    "--jq",
                    ".data.repository.discussion",
                ]
            )

            discussion = _parse_json(output)
            if not discussion:
                return None

            return self._map_to_note(discussion)
        except GitHubBackendError:
            return None

    def delete(self, note_id: int) -> bool:
        """Delete a note (close the discussion).

        Note: GitHub doesn't support deleting discussions via API,
        so we close it instead (similar to how issue "delete" works).
        """
        note = self.get(note_id)
        if not note:
            return False

        # Get the discussion node ID
        node_id = note.get("node_id")
        if not node_id:
            return False

        mutation = """
        mutation($discussionId: ID!) {
            closeDiscussion(input: {discussionId: $discussionId}) {
                discussion {
                    id
                    closed
                }
            }
        }
        """

        try:
            _run_gh_command(
                [
                    "api",
                    "graphql",
                    "-f",
                    f"query={mutation}",
                    "-F",
                    f"discussionId={node_id}",
                ]
            )
            return True
        except GitHubBackendError:
            return False

    def promote(self, note_id: int, to_type: str) -> dict[str, Any] | None:
        """Promote a note (discussion) to another type.

        For task: Creates a new GitHub issue with the discussion content.
        For reference: Creates a wiki page with the discussion content.
        """
        note = self.get(note_id)
        if not note:
            return None

        content = note.get("content", "")
        lines = content.split("\n", 1)
        title = lines[0][:80] if lines else content[:80]
        body = lines[1].strip() if len(lines) > 1 else ""

        try:
            if to_type == "task":
                # Create a GitHub issue
                args = [
                    "issue",
                    "create",
                    "--title",
                    title,
                    "--body",
                    body,
                ]
                output = _run_gh_command(args)

                # Parse issue number from URL
                issue_number = _extract_issue_number_from_url(output)
                if issue_number:
                    # Close the discussion
                    self.delete(note_id)
                    return {
                        "id": issue_number,
                        "title": title,
                        "body": body,
                        "type": "task",
                    }

            elif to_type == "reference":
                # For reference, we'd need to use the wiki backend
                # For now, just return the note content
                return {
                    "id": note_id,
                    "title": title,
                    "body": body,
                    "type": "reference",
                }

            return note
        except GitHubBackendError:
            return None

    def _map_to_note(
        self, discussion: dict[str, Any], tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Map GitHub discussion to note format."""
        title = discussion.get("title", "")
        body = discussion.get("body", "")

        # Reconstruct content from title and body
        content = f"{title}\n{body}".strip() if body else title

        # Extract tags from body (format: _Tags: explore, idea_)
        extracted_tags = tags or []
        if not extracted_tags and body:
            import re

            match = re.search(r"_Tags:\s*([^_]+)_", body)
            if match:
                extracted_tags = [t.strip() for t in match.group(1).split(",")]
                # Remove the tags line from content
                content = re.sub(r"\n*---\n_Tags:[^_]+_\s*$", "", content).strip()

        return {
            "id": discussion.get("number"),
            "node_id": discussion.get("id"),
            "content": content,
            "tags": extracted_tags,
            "created_at": discussion.get("createdAt", ""),
            "updated_at": discussion.get("updatedAt", ""),
            "url": discussion.get("url", ""),
            "closed": discussion.get("closed", False),
        }
