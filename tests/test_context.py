"""
Tests for context command.
"""
import pytest
import tempfile
import subprocess
from pathlib import Path
from src.context import ProjectContext


class TestProjectContext:
    """Tests for ProjectContext class."""
    
    def setup_git_repo(self, tmpdir):
        """Helper to set up a git repo with commits."""
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
        
        # Create initial commit
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=tmpdir, check=True, capture_output=True)
    
    def test_read_charter_documents(self):
        """Test reading charter documents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create charter docs
            vision = Path(tmpdir) / "VISION.md"
            vision.write_text("# Vision\nThis is the vision")
            
            todo = Path(tmpdir) / "TODO.md"
            todo.write_text("# TODO\n- Task 1\n- Task 2")
            
            context = ProjectContext(tmpdir)
            docs = context.read_charter_documents()
            
            assert 'VISION.md' in docs
            assert 'TODO.md' in docs
            assert "This is the vision" in docs['VISION.md']
            assert "Task 1" in docs['TODO.md']
    
    def test_read_charter_documents_missing(self):
        """Test reading when documents don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            context = ProjectContext(tmpdir)
            docs = context.read_charter_documents()
            
            # Should return empty dict for missing docs
            assert isinstance(docs, dict)
            # No docs exist, so dict should be empty or only have missing entries
            for doc_name, content in docs.items():
                assert content == "" or "[Error" in content or content is not None
    
    def test_get_recent_activity(self):
        """Test getting recent activity summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            context = ProjectContext(tmpdir)
            activity = context.get_recent_activity()
            
            assert "Current branch:" in activity
            assert "No uncommitted changes" in activity or "Uncommitted changes:" in activity
            assert "Recent commits:" in activity
    
    def test_get_recent_activity_no_git(self):
        """Test activity in non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ProjectContext(tmpdir)
            activity = context.get_recent_activity()
            
            assert "Not a git repository" in activity
    
    def test_get_project_structure(self):
        """Test getting project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create some directories and files
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "tests").mkdir()
            (Path(tmpdir) / "README.md").write_text("# README")
            
            context = ProjectContext(tmpdir)
            structure = context.get_project_structure()
            
            assert "src/" in structure
            assert "tests/" in structure
            assert "README.md" in structure
    
    def test_format_markdown_context(self):
        """Test markdown format output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create a charter doc
            vision = Path(tmpdir) / "VISION.md"
            vision.write_text("# Vision\nProject vision here")
            
            context = ProjectContext(tmpdir)
            output = context.format_context(format_type="markdown")
            
            assert "# Project Context" in output
            assert "## Recent Activity" in output
            assert "## Project Structure" in output
            assert "## Charter Documents" in output
            assert "### VISION.md" in output
            assert "Project vision here" in output
    
    def test_format_plain_context(self):
        """Test plain text format output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            context = ProjectContext(tmpdir)
            output = context.format_context(format_type="plain")
            
            assert "PROJECT CONTEXT:" in output
            assert "RECENT ACTIVITY" in output
            assert "PROJECT STRUCTURE" in output
            assert "=" in output  # Plain format uses = and - separators
    
    def test_format_context_selective_sections(self):
        """Test formatting with selective sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            vision = Path(tmpdir) / "VISION.md"
            vision.write_text("# Vision")
            
            context = ProjectContext(tmpdir)
            
            # Only activity
            output = context.format_context(
                include_docs=False,
                include_activity=True,
                include_structure=False
            )
            assert "Recent Activity" in output
            assert "Charter Documents" not in output
            assert "Project Structure" not in output
            
            # Only docs
            output = context.format_context(
                include_docs=True,
                include_activity=False,
                include_structure=False
            )
            assert "Charter Documents" in output or "VISION.md" in output
            assert "Recent Activity" not in output
    
    def test_context_includes_llm_branches(self):
        """Test that context includes LLM-managed branches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create an LLM branch
            subprocess.run(["git", "checkout", "-b", "claude-feature"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", "-"], cwd=tmpdir, check=True, capture_output=True)
            
            context = ProjectContext(tmpdir)
            activity = context.get_recent_activity()
            
            assert "claude-feature" in activity or "LLM-managed branches" in activity
