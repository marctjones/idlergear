"""Upstream issue reporting for IdlerGear.

Allows users to report bugs and feature requests directly to the IdlerGear repository.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class IssueType(str, Enum):
    """Types of issues that can be reported."""

    BUG = "bug"
    FEATURE = "enhancement"
    QUESTION = "question"
    DOCUMENTATION = "documentation"


@dataclass
class UpstreamIssue:
    """Represents an issue to report upstream."""

    title: str
    body: str
    issue_type: IssueType
    labels: list[str] | None = None

    def format_body(self) -> str:
        """Format issue body with environment information."""
        import platform
        import sys

        from idlergear import __version__

        env_info = f"""
## Environment

- **IdlerGear Version:** {__version__}
- **Python Version:** {sys.version.split()[0]}
- **OS:** {platform.system()} {platform.release()}
- **Platform:** {platform.platform()}

## Description

{self.body}
"""
        return env_info.strip()


def report_issue(
    title: str,
    body: str,
    issue_type: IssueType = IssueType.BUG,
    labels: list[str] | None = None,
) -> dict[str, str]:
    """Report an issue to the IdlerGear upstream repository.

    Args:
        title: Issue title
        body: Issue description
        issue_type: Type of issue (bug, feature, etc.)
        labels: Additional labels to add

    Returns:
        Dict with 'url' and 'number' keys

    Raises:
        RuntimeError: If gh CLI is not available or issue creation fails
    """
    # Check if gh CLI is available
    try:
        subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(
            "GitHub CLI (gh) is not installed. Install it first: https://cli.github.com/"
        )

    # Create issue object
    issue = UpstreamIssue(
        title=title,
        body=body,
        issue_type=issue_type,
        labels=labels or [],
    )

    # Build labels list
    all_labels = [issue_type.value]
    if issue.labels:
        all_labels.extend(issue.labels)

    # Create issue using gh CLI
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        "marctjones/idlergear",
        "--title",
        issue.title,
        "--body",
        issue.format_body(),
    ]

    # Add labels
    for label in all_labels:
        cmd.extend(["--label", label])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse URL from output (gh returns the issue URL)
        url = result.stdout.strip()

        # Extract issue number from URL
        number = url.split("/")[-1] if url else "unknown"

        return {
            "url": url,
            "number": number,
        }

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create issue: {e.stderr}")


def report_bug(
    title: str,
    description: str,
    steps_to_reproduce: str | None = None,
    expected_behavior: str | None = None,
    actual_behavior: str | None = None,
    error_output: str | None = None,
) -> dict[str, str]:
    """Report a bug to upstream IdlerGear.

    Args:
        title: Short bug title
        description: Bug description
        steps_to_reproduce: How to reproduce the bug
        expected_behavior: What should happen
        actual_behavior: What actually happens
        error_output: Error messages or stack traces

    Returns:
        Dict with 'url' and 'number' keys
    """
    body_parts = [description]

    if steps_to_reproduce:
        body_parts.append(f"\n## Steps to Reproduce\n\n{steps_to_reproduce}")

    if expected_behavior:
        body_parts.append(f"\n## Expected Behavior\n\n{expected_behavior}")

    if actual_behavior:
        body_parts.append(f"\n## Actual Behavior\n\n{actual_behavior}")

    if error_output:
        body_parts.append(f"\n## Error Output\n\n```\n{error_output}\n```")

    body = "\n".join(body_parts)

    return report_issue(
        title=title,
        body=body,
        issue_type=IssueType.BUG,
        labels=["user-reported"],
    )


def report_feature(
    title: str,
    description: str,
    use_case: str | None = None,
    proposed_solution: str | None = None,
) -> dict[str, str]:
    """Report a feature request to upstream IdlerGear.

    Args:
        title: Feature title
        description: Feature description
        use_case: Why this feature is needed
        proposed_solution: How it could be implemented

    Returns:
        Dict with 'url' and 'number' keys
    """
    body_parts = [description]

    if use_case:
        body_parts.append(f"\n## Use Case\n\n{use_case}")

    if proposed_solution:
        body_parts.append(f"\n## Proposed Solution\n\n{proposed_solution}")

    body = "\n".join(body_parts)

    return report_issue(
        title=title,
        body=body,
        issue_type=IssueType.FEATURE,
        labels=["user-requested"],
    )


def check_upstream_auth() -> bool:
    """Check if user is authenticated with GitHub CLI.

    Returns:
        True if authenticated, False otherwise
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
