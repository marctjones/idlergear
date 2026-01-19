"""Tests for graph populators."""

import tempfile
from pathlib import Path
import subprocess

import pytest

from idlergear.graph import get_database, initialize_schema, GraphDatabase
from idlergear.graph.database import reset_database
from idlergear.graph.populators import GitPopulator


@pytest.fixture
def temp_db():
    """Create a temporary graph database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_graph.db"
        db = GraphDatabase(db_path)
        initialize_schema(db)
        yield db
        db.close()
        reset_database()


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository with some commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
        )

        # Create first commit
        test_file = repo_path / "test.py"
        test_file.write_text("print('hello')\n")
        subprocess.run(["git", "add", "test.py"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True
        )

        # Create second commit
        test_file.write_text("print('hello')\nprint('world')\n")
        subprocess.run(["git", "add", "test.py"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add world"], cwd=repo_path, check=True
        )

        # Create third commit with new file
        another_file = repo_path / "another.py"
        another_file.write_text("def foo():\n    pass\n")
        subprocess.run(["git", "add", "another.py"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add another file"], cwd=repo_path, check=True
        )

        yield repo_path


class TestGitPopulator:
    """Tests for GitPopulator."""

    def test_populate_basic(self, temp_db, temp_git_repo):
        """populate() creates commit and file nodes."""
        populator = GitPopulator(temp_db, temp_git_repo)
        stats = populator.populate(max_commits=10)

        # Should have created 3 commits
        assert stats["commits"] == 3

        # Should have created 2 files (test.py and another.py)
        assert stats["files"] == 2

        # Should have created relationships
        assert stats["relationships"] > 0

    def test_populate_incremental(self, temp_db, temp_git_repo):
        """populate() with incremental=True skips existing commits."""
        populator = GitPopulator(temp_db, temp_git_repo)

        # First population
        stats1 = populator.populate(max_commits=10)
        assert stats1["commits"] == 3

        # Second population (incremental)
        stats2 = populator.populate(max_commits=10, incremental=True)
        assert stats2["commits"] == 0  # No new commits

    def test_commit_nodes_created(self, temp_db, temp_git_repo):
        """Commit nodes have correct properties."""
        populator = GitPopulator(temp_db, temp_git_repo)
        populator.populate(max_commits=10)

        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (c:Commit)
            RETURN c.short_hash, c.message, c.author
            ORDER BY c.timestamp DESC
        """)

        commits = []
        while result.has_next():
            row = result.get_next()
            commits.append({
                "short_hash": row[0],
                "message": row[1],
                "author": row[2],
            })

        assert len(commits) == 3
        assert commits[0]["message"] == "Add another file"
        assert commits[0]["author"] == "Test User"

    def test_file_nodes_created(self, temp_db, temp_git_repo):
        """File nodes have correct properties."""
        populator = GitPopulator(temp_db, temp_git_repo)
        populator.populate(max_commits=10)

        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (f:File)
            RETURN f.path, f.language, f.file_exists
        """)

        files = []
        while result.has_next():
            row = result.get_next()
            files.append({
                "path": row[0],
                "language": row[1],
                "exists": row[2],
            })

        assert len(files) == 2

        # Check languages detected correctly
        languages = {f["path"]: f["language"] for f in files}
        assert languages["test.py"] == "python"
        assert languages["another.py"] == "python"

    def test_changes_relationships_created(self, temp_db, temp_git_repo):
        """CHANGES relationships connect commits to files."""
        populator = GitPopulator(temp_db, temp_git_repo)
        populator.populate(max_commits=10)

        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (c:Commit)-[r:CHANGES]->(f:File)
            RETURN c.message, f.path, r.insertions, r.deletions
        """)

        relationships = []
        while result.has_next():
            row = result.get_next()
            relationships.append({
                "commit_message": row[0],
                "file_path": row[1],
                "insertions": row[2],
                "deletions": row[3],
            })

        # Should have multiple CHANGES relationships
        assert len(relationships) > 0

        # Check that test.py has changes
        test_py_changes = [r for r in relationships if r["file_path"] == "test.py"]
        assert len(test_py_changes) >= 2  # At least 2 commits touched test.py

    def test_populate_limit(self, temp_db, temp_git_repo):
        """populate() respects max_commits limit."""
        populator = GitPopulator(temp_db, temp_git_repo)
        stats = populator.populate(max_commits=2)

        # Should only create 2 commits even though repo has 3
        assert stats["commits"] == 2

    def test_language_detection(self, temp_db, temp_git_repo):
        """Language is detected correctly from file extensions."""
        # Add files with different extensions
        (temp_git_repo / "test.js").write_text("console.log('test');")
        (temp_git_repo / "test.go").write_text("package main")
        (temp_git_repo / "test.rs").write_text("fn main() {}")

        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add multiple languages"],
            cwd=temp_git_repo,
            check=True,
        )

        populator = GitPopulator(temp_db, temp_git_repo)
        populator.populate(max_commits=10)

        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (f:File)
            RETURN f.path, f.language
        """)

        files = {}
        while result.has_next():
            row = result.get_next()
            files[row[0]] = row[1]

        assert files["test.js"] == "javascript"
        assert files["test.go"] == "go"
        assert files["test.rs"] == "rust"
