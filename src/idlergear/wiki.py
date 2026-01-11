"""
Wiki synchronization for IdlerGear.

Bidirectional sync between IdlerGear references and GitHub Wiki.
"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import get_config_value, set_config_value
from .reference import add_reference, get_reference, list_references


@dataclass
class WikiPage:
    """Represents a GitHub Wiki page."""

    title: str
    content: str
    path: Path
    modified: datetime


@dataclass
class SyncResult:
    """Result of a wiki sync operation."""

    pushed: List[str]
    pulled: List[str]
    conflicts: List[str]
    errors: List[str]

    def __str__(self) -> str:
        """Format sync result as human-readable string."""
        lines = []

        if self.pushed:
            lines.append(f"✅ Pushed {len(self.pushed)} references to Wiki:")
            for title in self.pushed:
                lines.append(f"   - {title}")

        if self.pulled:
            lines.append(f"✅ Pulled {len(self.pulled)} pages from Wiki:")
            for title in self.pulled:
                lines.append(f"   - {title}")

        if self.conflicts:
            lines.append(f"⚠️  {len(self.conflicts)} conflicts detected:")
            for title in self.conflicts:
                lines.append(f"   - {title}")

        if self.errors:
            lines.append(f"❌ {len(self.errors)} errors:")
            for error in self.errors:
                lines.append(f"   - {error}")

        return "\n".join(lines) if lines else "No changes"


class WikiSync:
    """GitHub Wiki synchronization manager."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize wiki sync manager.

        Args:
            project_root: Project root directory (default: current directory)
        """
        self.project_root = project_root or Path.cwd()
        self.wiki_dir = self.project_root / ".wiki"

    def _run_git(self, *args: str, cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Run git command and return (returncode, stdout, stderr).

        Args:
            *args: Git command arguments
            cwd: Working directory (default: wiki_dir)

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        cwd = cwd or self.wiki_dir
        result = subprocess.run(
            ["git"] + list(args), cwd=str(cwd), capture_output=True, text=True
        )
        return result.returncode, result.stdout, result.stderr

    def _get_wiki_url(self) -> Optional[str]:
        """Get GitHub Wiki URL from git remote.

        Returns:
            Wiki URL or None if not found
        """
        # Get origin URL
        returncode, stdout, stderr = self._run_git(
            "remote", "get-url", "origin", cwd=self.project_root
        )
        if returncode != 0:
            return None

        origin_url = stdout.strip()

        # Convert to wiki URL
        # https://github.com/user/repo.git -> https://github.com/user/repo.wiki.git
        # git@github.com:user/repo.git -> git@github.com:user/repo.wiki.git
        if origin_url.endswith(".git"):
            wiki_url = origin_url[:-4] + ".wiki.git"
        else:
            wiki_url = origin_url + ".wiki.git"

        return wiki_url

    def wiki_exists(self) -> bool:
        """Check if the GitHub Wiki repository exists.

        GitHub wikis don't exist until the first page is created.
        This checks if the wiki repo can be accessed.

        Returns:
            True if wiki exists and is accessible, False otherwise
        """
        wiki_url = self._get_wiki_url()
        if not wiki_url:
            return False

        # Try to ls-remote the wiki repo
        result = subprocess.run(
            ["git", "ls-remote", wiki_url],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return result.returncode == 0

    def initialize_wiki(self) -> bool:
        """Initialize GitHub Wiki by creating the first page via API.

        GitHub wikis don't exist until the first page is created via
        the web UI or API. This creates a Home page to initialize the wiki.

        Returns:
            True if wiki was initialized successfully, False otherwise
        """
        # Check if wiki already exists
        if self.wiki_exists():
            return True

        # Get owner and repo from git remote
        returncode, stdout, stderr = self._run_git(
            "remote", "get-url", "origin", cwd=self.project_root
        )
        if returncode != 0:
            return False

        origin_url = stdout.strip()

        # Parse owner/repo from URL
        # https://github.com/owner/repo.git or git@github.com:owner/repo.git
        import re

        match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", origin_url)
        if not match:
            return False

        owner, repo = match.groups()
        if repo.endswith(".git"):
            repo = repo[:-4]

        # Create initial wiki page via GitHub API
        # GitHub doesn't have a direct wiki API, but we can use gh to create it
        try:
            # First, check if wiki is enabled for the repo
            result = subprocess.run(
                ["gh", "api", f"/repos/{owner}/{repo}", "--jq", ".has_wiki"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0 or result.stdout.strip().lower() != "true":
                return False

            # Unfortunately, GitHub API doesn't support creating wiki pages directly.
            # We need to init locally and push.
            # Create a local wiki repo with Home.md
            import shutil

            if self.wiki_dir.exists():
                shutil.rmtree(self.wiki_dir)

            self.wiki_dir.mkdir(parents=True)

            # Init git repo
            subprocess.run(
                ["git", "init"],
                cwd=str(self.wiki_dir),
                capture_output=True,
                check=True,
            )

            # Create Home.md
            home_page = self.wiki_dir / "Home.md"
            home_page.write_text(
                "# Welcome to the Wiki\n\n"
                "This wiki was auto-initialized by IdlerGear.\n\n"
                "## Getting Started\n\n"
                "Add your project documentation here.\n"
            )

            # Add and commit
            subprocess.run(
                ["git", "add", "."],
                cwd=str(self.wiki_dir),
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initialize wiki"],
                cwd=str(self.wiki_dir),
                capture_output=True,
                check=True,
            )

            # Add remote and push
            wiki_url = self._get_wiki_url()
            subprocess.run(
                ["git", "remote", "add", "origin", wiki_url],
                cwd=str(self.wiki_dir),
                capture_output=True,
                check=True,
            )

            # Push to master (GitHub wikis use master)
            result = subprocess.run(
                ["git", "push", "-u", "origin", "master"],
                cwd=str(self.wiki_dir),
                capture_output=True,
                text=True,
            )

            # If push fails, try creating with HEAD:master
            if result.returncode != 0:
                result = subprocess.run(
                    ["git", "push", "-u", "origin", "HEAD:master"],
                    cwd=str(self.wiki_dir),
                    capture_output=True,
                    text=True,
                )

            return result.returncode == 0

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            return False

    def clone_wiki(self) -> bool:
        """Clone GitHub Wiki repository.

        If wiki doesn't exist, attempts to initialize it first.

        Returns:
            True if successful, False otherwise
        """
        wiki_url = self._get_wiki_url()
        if not wiki_url:
            return False

        # Remove existing wiki dir if it exists
        if self.wiki_dir.exists():
            import shutil

            shutil.rmtree(self.wiki_dir)

        # Clone wiki
        returncode, stdout, stderr = self._run_git(
            "clone", wiki_url, str(self.wiki_dir), cwd=self.project_root
        )

        # If clone failed, try to initialize the wiki
        if returncode != 0:
            if "not found" in stderr.lower() or "does not exist" in stderr.lower():
                if self.initialize_wiki():
                    return True  # initialize_wiki already creates the local repo
            return False

        return True

    def pull_wiki(self) -> bool:
        """Pull latest changes from GitHub Wiki.

        Returns:
            True if successful, False otherwise
        """
        if not self.wiki_dir.exists():
            return self.clone_wiki()

        # Pull latest changes
        returncode, stdout, stderr = self._run_git("pull", "origin", "master")

        # Try main if master doesn't exist
        if returncode != 0:
            returncode, stdout, stderr = self._run_git("pull", "origin", "main")

        return returncode == 0

    def push_wiki(self) -> bool:
        """Push changes to GitHub Wiki.

        Returns:
            True if successful, False otherwise
        """
        if not self.wiki_dir.exists():
            return False

        # Add all changes
        self._run_git("add", ".")

        # Commit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._run_git("commit", "-m", f"Sync from IdlerGear at {timestamp}")

        # Push
        returncode, stdout, stderr = self._run_git("push", "origin", "master")

        # Try main if master doesn't exist
        if returncode != 0:
            returncode, stdout, stderr = self._run_git("push", "origin", "main")

        return returncode == 0

    def list_wiki_pages(self) -> List[WikiPage]:
        """List all pages in the wiki.

        Returns:
            List of WikiPage objects
        """
        if not self.wiki_dir.exists():
            return []

        pages = []

        for md_file in self.wiki_dir.glob("*.md"):
            # Skip special files
            if md_file.name in ["_Sidebar.md", "_Footer.md"]:
                continue

            # Read content
            content = md_file.read_text(encoding="utf-8")

            # Get title from filename
            title = md_file.stem.replace("-", " ")

            # Get modified time
            stat = md_file.stat()
            modified = datetime.fromtimestamp(stat.st_mtime)

            pages.append(
                WikiPage(title=title, content=content, path=md_file, modified=modified)
            )

        return pages

    def push_references_to_wiki(self) -> SyncResult:
        """Push all IdlerGear references to GitHub Wiki.

        Returns:
            SyncResult with details of the sync operation
        """
        result = SyncResult(pushed=[], pulled=[], conflicts=[], errors=[])

        # Ensure wiki is cloned
        if not self.wiki_dir.exists():
            if not self.clone_wiki():
                result.errors.append("Failed to clone wiki repository")
                return result

        # Pull latest changes first
        if not self.pull_wiki():
            result.errors.append("Failed to pull latest wiki changes")
            return result

        # Get all references
        references = list_references()

        # Push each reference
        for ref in references:
            try:
                # Get full reference content
                ref_data = get_reference(ref["title"])
                if not ref_data:
                    result.errors.append(f"{ref['title']}: Reference not found")
                    continue

                ref_content = ref_data.get("body", "")

                # Create wiki filename (replace spaces with hyphens)
                wiki_filename = ref["title"].replace(" ", "-") + ".md"
                wiki_path = self.wiki_dir / wiki_filename

                # Check for conflicts
                if wiki_path.exists():
                    existing_content = wiki_path.read_text(encoding="utf-8")
                    if existing_content != ref_content and existing_content.strip():
                        result.conflicts.append(ref["title"])
                        continue

                # Write reference to wiki
                wiki_path.write_text(ref_content, encoding="utf-8")
                result.pushed.append(ref["title"])

            except Exception as e:
                result.errors.append(f"{ref['title']}: {str(e)}")

        # Push to remote if there are changes
        if result.pushed:
            if not self.push_wiki():
                result.errors.append("Failed to push changes to wiki")

        return result

    def pull_wiki_to_references(self, overwrite: bool = False) -> SyncResult:
        """Pull GitHub Wiki pages into IdlerGear references.

        Args:
            overwrite: If True, overwrite existing references

        Returns:
            SyncResult with details of the sync operation
        """
        result = SyncResult(pushed=[], pulled=[], conflicts=[], errors=[])

        # Ensure wiki is cloned and up to date
        if not self.wiki_dir.exists():
            if not self.clone_wiki():
                result.errors.append("Failed to clone wiki repository")
                return result
        else:
            if not self.pull_wiki():
                result.errors.append("Failed to pull latest wiki changes")
                return result

        # Get all wiki pages
        wiki_pages = self.list_wiki_pages()

        # Get existing references
        existing_refs = {ref.title: ref for ref in list_references()}

        # Pull each wiki page
        for page in wiki_pages:
            try:
                # Check if reference already exists
                if page.title in existing_refs:
                    if not overwrite:
                        result.conflicts.append(page.title)
                        continue

                # Add as reference
                add_reference(page.title, page.content)
                result.pulled.append(page.title)

            except Exception as e:
                result.errors.append(f"{page.title}: {str(e)}")

        return result

    def sync_bidirectional(self, conflict_resolution: str = "manual") -> SyncResult:
        """Bidirectional sync between IdlerGear and GitHub Wiki.

        Args:
            conflict_resolution: How to handle conflicts ("manual", "local", "remote")

        Returns:
            SyncResult with details of the sync operation
        """
        result = SyncResult(pushed=[], pulled=[], conflicts=[], errors=[])

        # Ensure wiki is cloned and up to date
        if not self.wiki_dir.exists():
            if not self.clone_wiki():
                result.errors.append("Failed to clone wiki repository")
                return result
        else:
            if not self.pull_wiki():
                result.errors.append("Failed to pull latest wiki changes")
                return result

        # Get references and wiki pages
        # list_references() returns list of dicts, use dict key access
        references = {ref["title"]: ref for ref in list_references()}
        wiki_pages = {page.title: page for page in self.list_wiki_pages()}

        # All titles
        all_titles = set(references.keys()) | set(wiki_pages.keys())

        for title in all_titles:
            try:
                ref = references.get(title)
                page = wiki_pages.get(title)

                if ref and not page:
                    # Reference exists, page doesn't - push to wiki
                    ref_data = get_reference(ref["title"])
                    ref_content = ref_data.get("body", "") if ref_data else ""
                    wiki_filename = title.replace(" ", "-") + ".md"
                    wiki_path = self.wiki_dir / wiki_filename
                    wiki_path.write_text(ref_content, encoding="utf-8")
                    result.pushed.append(title)

                elif page and not ref:
                    # Page exists, reference doesn't - pull to references
                    add_reference(page.title, page.content)
                    result.pulled.append(title)

                elif ref and page:
                    # Both exist - check for conflicts
                    ref_data = get_reference(ref["title"])
                    ref_content = ref_data.get("body", "") if ref_data else ""

                    if ref_content != page.content:
                        # Conflict detected
                        if conflict_resolution == "local":
                            # Use local (push to wiki)
                            wiki_filename = title.replace(" ", "-") + ".md"
                            wiki_path = self.wiki_dir / wiki_filename
                            wiki_path.write_text(ref_content, encoding="utf-8")
                            result.pushed.append(title)
                        elif conflict_resolution == "remote":
                            # Use remote (pull from wiki)
                            add_reference(page.title, page.content)
                            result.pulled.append(title)
                        else:
                            # Manual resolution needed
                            result.conflicts.append(title)

            except Exception as e:
                result.errors.append(f"{title}: {str(e)}")

        # Push changes if any
        if result.pushed:
            if not self.push_wiki():
                result.errors.append("Failed to push changes to wiki")

        return result


def get_wiki_config() -> Dict:
    """Get wiki configuration.

    Returns:
        Dictionary of wiki configuration values
    """
    return {
        "enabled": get_config_value("wiki.enabled", "false") == "true",
        "auto_sync": get_config_value("wiki.auto_sync", "false") == "true",
        "sync_interval": int(get_config_value("wiki.sync_interval", "300")),
    }


def set_wiki_config(key: str, value: str) -> None:
    """Set wiki configuration value.

    Args:
        key: Configuration key (e.g., "enabled", "auto_sync")
        value: Configuration value
    """
    set_config_value(f"wiki.{key}", value)
