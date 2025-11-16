"""
Context command: Generate LLM-ready project context.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict

from src.status import ProjectStatus


class ProjectContext:
    """Collect and format comprehensive project context for LLM consumption."""

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.status = ProjectStatus(project_path)

    def read_charter_documents(self) -> Dict[str, str]:
        """Read all charter documents."""
        charter_docs = [
            "VISION.md",
            "DESIGN.md",
            "TODO.md",
            "IDEAS.md",
            "DEVELOPMENT.md",
            "ARCHITECTURE.md",
            "ROADMAP.md",
        ]
        docs = {}

        if not self.status.git_root:
            return docs

        for doc in charter_docs:
            doc_path = self.status.git_root / doc
            if doc_path.exists():
                try:
                    docs[doc] = doc_path.read_text()
                except Exception:
                    docs[doc] = f"[Error reading {doc}]"

        return docs

    def get_recent_activity(self) -> str:
        """Get recent git activity summary."""
        if not self.status.is_git_repo:
            return "Not a git repository"

        lines = []

        # Current branch
        branch = self.status.get_git_branch()
        if branch:
            lines.append(f"Current branch: {branch}")

        # Uncommitted changes
        uncommitted = self.status.get_uncommitted_changes()
        if uncommitted > 0:
            lines.append(f"Uncommitted changes: {uncommitted} files")
        else:
            lines.append("No uncommitted changes")

        # Recent commits
        commits = self.status.get_recent_commits(count=5)
        if commits:
            lines.append("\nRecent commits:")
            for commit in commits:
                lines.append(
                    f"  {commit['hash']}: {commit['message']} ({commit['time']})"
                )

        # LLM branches
        llm_branches = self.status.get_llm_managed_branches()
        active_llm_branches = []
        for category, branches in llm_branches.items():
            if branches and category != "dangling":
                active_llm_branches.extend(branches)

        if active_llm_branches:
            lines.append(f"\nLLM-managed branches: {', '.join(active_llm_branches)}")

        return "\n".join(lines)

    def get_project_structure(self) -> str:
        """Get basic project structure."""
        if not self.status.git_root:
            return "Not a git repository"

        lines = []
        root = self.status.git_root

        # List top-level directories and key files
        try:
            for item in sorted(root.iterdir()):
                # Skip hidden and common ignore patterns
                if item.name.startswith(".") or item.name in [
                    "venv",
                    "node_modules",
                    "__pycache__",
                    "target",
                    "build",
                    "dist",
                ]:
                    continue

                if item.is_dir():
                    lines.append(f"  {item.name}/")
                else:
                    lines.append(f"  {item.name}")
        except Exception:
            return "Error reading project structure"

        return "\n".join(lines) if lines else "Empty project"

    def format_context(
        self,
        include_docs: bool = True,
        include_activity: bool = True,
        include_structure: bool = True,
        format_type: str = "markdown",
    ) -> str:
        """Format complete project context."""

        if format_type == "markdown":
            return self._format_markdown(
                include_docs, include_activity, include_structure
            )
        elif format_type == "plain":
            return self._format_plain(include_docs, include_activity, include_structure)
        else:
            return self._format_markdown(
                include_docs, include_activity, include_structure
            )

    def _format_markdown(
        self, include_docs: bool, include_activity: bool, include_structure: bool
    ) -> str:
        """Format context as markdown."""
        lines = []

        # Header
        lines.append("# Project Context")
        lines.append("")
        lines.append(f"**Project:** {self.status.get_project_name()}")
        lines.append(f"**Location:** {self.project_path}")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Recent activity
        if include_activity:
            lines.append("## Recent Activity")
            lines.append("")
            lines.append(self.get_recent_activity())
            lines.append("")
            lines.append("---")
            lines.append("")

        # Project structure
        if include_structure:
            lines.append("## Project Structure")
            lines.append("")
            lines.append("```")
            lines.append(self.get_project_structure())
            lines.append("```")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Charter documents
        if include_docs:
            docs = self.read_charter_documents()

            if docs:
                lines.append("## Charter Documents")
                lines.append("")

                for doc_name, content in docs.items():
                    lines.append(f"### {doc_name}")
                    lines.append("")
                    lines.append(content)
                    lines.append("")
                    lines.append("---")
                    lines.append("")

        return "\n".join(lines)

    def _format_plain(
        self, include_docs: bool, include_activity: bool, include_structure: bool
    ) -> str:
        """Format context as plain text."""
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append(f"PROJECT CONTEXT: {self.status.get_project_name()}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Location: {self.project_path}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Recent activity
        if include_activity:
            lines.append("-" * 80)
            lines.append("RECENT ACTIVITY")
            lines.append("-" * 80)
            lines.append(self.get_recent_activity())
            lines.append("")

        # Project structure
        if include_structure:
            lines.append("-" * 80)
            lines.append("PROJECT STRUCTURE")
            lines.append("-" * 80)
            lines.append(self.get_project_structure())
            lines.append("")

        # Charter documents
        if include_docs:
            docs = self.read_charter_documents()

            if docs:
                for doc_name, content in docs.items():
                    lines.append("-" * 80)
                    lines.append(doc_name)
                    lines.append("-" * 80)
                    lines.append(content)
                    lines.append("")

        return "\n".join(lines)

    def format_markdown(self) -> str:
        """Format context as markdown (default, full context)."""
        return self.format_context(
            include_docs=True,
            include_activity=True,
            include_structure=True,
            format_type="markdown",
        )

    def format_json(self) -> str:
        """Format context as JSON for programmatic use."""
        import json

        data = {
            "project": {
                "name": self.status.get_project_name(),
                "path": str(self.project_path),
                "generated_at": datetime.now().isoformat(),
            },
            "activity": {
                "branch": self.status.get_git_branch(),
                "uncommitted_changes": self.status.get_uncommitted_changes(),
                "recent_commits": self.status.get_recent_commits(count=5),
                "llm_branches": self.status.get_llm_managed_branches(),
            },
            "structure": self.get_project_structure().split("\n"),
            "charter_documents": self.read_charter_documents(),
        }

        return json.dumps(data, indent=2)
