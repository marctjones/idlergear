"""GitHub repository detection and feature availability.

Detects if the current project is a GitHub repository and what features
are available (issues, discussions, wiki, etc.).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GitHubFeatures:
    """Available GitHub features for a repository."""

    is_github_repo: bool = False
    has_issues: bool = False
    has_discussions: bool = False
    has_wiki: bool = False
    has_projects: bool = False
    repo_name: str | None = None
    repo_url: str | None = None
    error: str | None = None


def detect_github_features(project_path: Path | None = None) -> GitHubFeatures:
    """Detect available GitHub features for the current repository.

    Args:
        project_path: Optional path to check (defaults to cwd)

    Returns:
        GitHubFeatures with detected capabilities
    """
    features = GitHubFeatures()

    # Check if gh CLI is available
    try:
        subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            timeout=5,
        )
    except FileNotFoundError:
        features.error = "GitHub CLI (gh) not installed"
        return features
    except subprocess.TimeoutExpired:
        features.error = "GitHub CLI timed out"
        return features

    # Check if we're in a git repo with GitHub remote
    try:
        result = subprocess.run(
            [
                "gh",
                "repo",
                "view",
                "--json",
                "name,url,hasIssuesEnabled,hasWikiEnabled,hasDiscussionsEnabled,hasProjectsEnabled",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_path,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "not a git repository" in stderr.lower():
                features.error = "Not a git repository"
            elif (
                "could not determine" in stderr.lower() or "no github" in stderr.lower()
            ):
                features.error = "No GitHub remote found"
            elif (
                "not logged in" in stderr.lower() or "authentication" in stderr.lower()
            ):
                features.error = "Not authenticated with GitHub (run: gh auth login)"
            else:
                features.error = stderr or "Unknown error"
            return features

        data = json.loads(result.stdout)
        features.is_github_repo = True
        features.repo_name = data.get("name")
        features.repo_url = data.get("url")
        features.has_issues = data.get("hasIssuesEnabled", False)
        features.has_wiki = data.get("hasWikiEnabled", False)
        features.has_discussions = data.get("hasDiscussionsEnabled", False)
        features.has_projects = data.get("hasProjectsEnabled", False)

    except subprocess.TimeoutExpired:
        features.error = "GitHub API timed out"
    except json.JSONDecodeError:
        features.error = "Invalid response from GitHub"
    except Exception as e:
        features.error = str(e)

    return features


def get_recommended_backends(features: GitHubFeatures) -> dict[str, str]:
    """Get recommended backend configuration based on GitHub features.

    Args:
        features: Detected GitHub features

    Returns:
        Dict mapping backend types to recommended backend names
    """
    recommendations = {}

    if not features.is_github_repo:
        return recommendations

    if features.has_issues:
        recommendations["task"] = "github"
        recommendations["explore"] = "github"  # Use issues with labels

    # Future: when we have wiki/discussions backends
    # if features.has_wiki:
    #     recommendations["reference"] = "github"
    # if features.has_discussions:
    #     recommendations["explore"] = "github-discussions"

    return recommendations


def get_github_owner(project_path: Path | None = None) -> str | None:
    """Get the GitHub owner (user or org) for the repository.

    Args:
        project_path: Optional path to check (defaults to cwd)

    Returns:
        Owner name string, or None if not a GitHub repo
    """
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "owner", "--jq", ".owner.login"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_path,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
        return None
    except Exception:
        return None


def format_features_summary(features: GitHubFeatures) -> str:
    """Format a human-readable summary of detected features.

    Args:
        features: Detected GitHub features

    Returns:
        Formatted string describing the features
    """
    if features.error:
        return f"GitHub detection: {features.error}"

    if not features.is_github_repo:
        return "Not a GitHub repository"

    lines = [f"GitHub repository: {features.repo_name}"]

    feature_list = []
    if features.has_issues:
        feature_list.append("Issues")
    if features.has_discussions:
        feature_list.append("Discussions")
    if features.has_wiki:
        feature_list.append("Wiki")
    if features.has_projects:
        feature_list.append("Projects")

    if feature_list:
        lines.append(f"Available features: {', '.join(feature_list)}")
    else:
        lines.append("No GitHub features enabled")

    return "\n".join(lines)
