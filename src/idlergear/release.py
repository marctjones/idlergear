"""Release management for IdlerGear (GitHub backend)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class Release:
    """A GitHub release."""

    tag: str
    name: str
    published_at: Optional[datetime]
    is_draft: bool
    is_prerelease: bool
    body: Optional[str]
    url: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tag": self.tag,
            "name": self.name,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "is_draft": self.is_draft,
            "is_prerelease": self.is_prerelease,
            "body": self.body,
            "url": self.url,
        }


def check_gh_installed() -> bool:
    """Check if gh CLI is installed."""
    try:
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def check_gh_auth() -> bool:
    """Check if gh CLI is authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def list_releases(limit: int = 10) -> list[Release]:
    """List releases from GitHub.

    Args:
        limit: Maximum number of releases to return

    Returns:
        List of Release objects
    """
    result = subprocess.run(
        [
            "gh", "release", "list",
            "--limit", str(limit),
            "--json", "tagName,name,publishedAt,isDraft,isPrerelease",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to list releases: {result.stderr}")

    releases = []
    data = json.loads(result.stdout)

    for item in data:
        published_at = None
        if item.get("publishedAt"):
            try:
                published_at = datetime.fromisoformat(
                    item["publishedAt"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        releases.append(Release(
            tag=item["tagName"],
            name=item.get("name") or item["tagName"],
            published_at=published_at,
            is_draft=item.get("isDraft", False),
            is_prerelease=item.get("isPrerelease", False),
            body=None,  # Not available in list, use get_release for full details
            url=None,
        ))

    return releases


def get_release(tag: str) -> Optional[Release]:
    """Get a specific release by tag.

    Args:
        tag: Release tag (e.g., v0.3.27)

    Returns:
        Release object or None if not found
    """
    result = subprocess.run(
        [
            "gh", "release", "view", tag,
            "--json", "tagName,name,publishedAt,isDraft,isPrerelease,body,url",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        return None

    item = json.loads(result.stdout)
    published_at = None
    if item.get("publishedAt"):
        try:
            published_at = datetime.fromisoformat(
                item["publishedAt"].replace("Z", "+00:00")
            )
        except ValueError:
            pass

    return Release(
        tag=item["tagName"],
        name=item.get("name") or item["tagName"],
        published_at=published_at,
        is_draft=item.get("isDraft", False),
        is_prerelease=item.get("isPrerelease", False),
        body=item.get("body"),
        url=item.get("url"),
    )


def get_latest_release() -> Optional[Release]:
    """Get the latest release.

    Returns:
        Latest Release or None if no releases exist
    """
    releases = list_releases(limit=1)
    return releases[0] if releases else None


def generate_notes_from_tasks(since_tag: Optional[str] = None) -> str:
    """Generate release notes from closed tasks since a given tag.

    Args:
        since_tag: Tag to start from (defaults to latest release)

    Returns:
        Generated release notes in markdown format
    """
    from idlergear.config import find_idlergear_root
    from idlergear.tasks import list_tasks

    root = find_idlergear_root()
    if root is None:
        return "No IdlerGear project found."

    # Get closed tasks
    closed_tasks = list_tasks(state="closed", project_path=root)

    if not closed_tasks:
        return "No closed tasks since last release."

    # Group by label
    bugs = []
    features = []
    other = []

    for task in closed_tasks:
        labels = task.get("labels", [])
        if "bug" in labels:
            bugs.append(task)
        elif any(l in labels for l in ["enhancement", "feature"]):
            features.append(task)
        else:
            other.append(task)

    lines = ["## What's Changed\n"]

    if features:
        lines.append("### New Features\n")
        for task in features:
            lines.append(f"- {task['title']} (#{task['id']})")
        lines.append("")

    if bugs:
        lines.append("### Bug Fixes\n")
        for task in bugs:
            lines.append(f"- {task['title']} (#{task['id']})")
        lines.append("")

    if other:
        lines.append("### Other Changes\n")
        for task in other:
            lines.append(f"- {task['title']} (#{task['id']})")
        lines.append("")

    return "\n".join(lines)


def run_version_command(project_path: Optional[Path] = None) -> tuple[bool, str]:
    """Run the configured version bump command.

    Args:
        project_path: Path to project (defaults to finding IdlerGear root)

    Returns:
        Tuple of (success, output/error)
    """
    from idlergear.config import find_idlergear_root, get_config_value

    if project_path is None:
        project_path = find_idlergear_root()

    if project_path is None:
        return False, "Not in an IdlerGear project"

    version_command = get_config_value("release.version_command")
    if not version_command:
        return False, "No version_command configured. Set release.version_command in config."

    try:
        result = subprocess.run(
            version_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=60,
        )

        if result.returncode != 0:
            return False, f"Version command failed: {result.stderr or result.stdout}"

        return True, result.stdout or "Version bumped successfully"

    except subprocess.TimeoutExpired:
        return False, "Version command timed out"
    except Exception as e:
        return False, f"Version command error: {e}"


def create_release(
    tag: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    notes_from_tasks: bool = False,
    draft: bool = False,
    prerelease: bool = False,
    bump: bool = False,
    target: Optional[str] = None,
) -> tuple[bool, str, Optional[str]]:
    """Create a new release on GitHub.

    Args:
        tag: Release tag (e.g., v0.4.0)
        title: Release title (defaults to tag)
        notes: Release notes
        notes_from_tasks: Generate notes from closed tasks
        draft: Create as draft
        prerelease: Mark as pre-release
        bump: Run version command before creating release
        target: Target branch or commit

    Returns:
        Tuple of (success, message, url)
    """
    # Run version bump if requested
    if bump:
        success, output = run_version_command()
        if not success:
            return False, output, None

    # Generate notes from tasks if requested
    if notes_from_tasks and not notes:
        notes = generate_notes_from_tasks()

    # Build command
    cmd = ["gh", "release", "create", tag]

    if title:
        cmd.extend(["--title", title])
    else:
        cmd.extend(["--title", tag])

    if notes:
        cmd.extend(["--notes", notes])
    else:
        cmd.append("--generate-notes")

    if draft:
        cmd.append("--draft")

    if prerelease:
        cmd.append("--prerelease")

    if target:
        cmd.extend(["--target", target])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return False, f"Failed to create release: {result.stderr}", None

        # Extract URL from output
        url = result.stdout.strip() if result.stdout else None
        return True, f"Created release {tag}", url

    except subprocess.TimeoutExpired:
        return False, "Release creation timed out", None
    except Exception as e:
        return False, f"Release creation error: {e}", None


def delete_release(tag: str, yes: bool = False) -> tuple[bool, str]:
    """Delete a release.

    Args:
        tag: Release tag to delete
        yes: Skip confirmation

    Returns:
        Tuple of (success, message)
    """
    cmd = ["gh", "release", "delete", tag]
    if yes:
        cmd.append("--yes")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return False, f"Failed to delete release: {result.stderr}"

        return True, f"Deleted release {tag}"

    except Exception as e:
        return False, f"Delete error: {e}"
