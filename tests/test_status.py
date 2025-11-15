"""
Tests for status command.
"""
import pytest
import tempfile
import subprocess
from pathlib import Path
from src.status import ProjectStatus


class TestProjectStatus:
    """Tests for ProjectStatus class."""
    
    def test_not_a_git_repo(self):
        """Test status in a non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            status = ProjectStatus(tmpdir)
            assert not status.is_git_repo
            assert status.git_root is None
            assert status.get_git_branch() is None
    
    def test_is_git_repo(self):
        """Test status detects git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize git repo
            subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
            
            status = ProjectStatus(tmpdir)
            assert status.is_git_repo
            assert status.git_root is not None
    
    def test_get_branch_name(self):
        """Test getting current branch name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
            
            # Create initial commit so we have a branch
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=tmpdir, check=True, capture_output=True)
            
            status = ProjectStatus(tmpdir)
            branch = status.get_git_branch()
            # Default branch might be 'main' or 'master' depending on git version
            assert branch in ['main', 'master']
    
    def test_uncommitted_changes(self):
        """Test counting uncommitted changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
            
            status = ProjectStatus(tmpdir)
            assert status.get_uncommitted_changes() == 0
            
            # Add a file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            
            assert status.get_uncommitted_changes() == 1
            
            # Add another file
            test_file2 = Path(tmpdir) / "test2.txt"
            test_file2.write_text("test2")
            
            assert status.get_uncommitted_changes() == 2
    
    def test_recent_commits(self):
        """Test getting recent commits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
            
            status = ProjectStatus(tmpdir)
            assert status.get_recent_commits() == []
            
            # Create commits
            for i in range(5):
                test_file = Path(tmpdir) / f"test{i}.txt"
                test_file.write_text(f"test{i}")
                subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"commit {i}"], cwd=tmpdir, check=True, capture_output=True)
            
            commits = status.get_recent_commits(count=3)
            assert len(commits) == 3
            assert commits[0]['message'] == 'commit 4'  # Most recent first
            assert commits[1]['message'] == 'commit 3'
            assert commits[2]['message'] == 'commit 2'
            assert 'hash' in commits[0]
            assert 'time' in commits[0]
    
    def test_charter_doc_age_not_found(self):
        """Test charter document that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
            
            status = ProjectStatus(tmpdir)
            age = status.get_charter_doc_age("VISION.md")
            assert age == "Not found"
    
    def test_charter_doc_age_exists(self):
        """Test charter document that exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
            
            vision_file = Path(tmpdir) / "VISION.md"
            vision_file.write_text("# Vision")
            subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "add vision"], cwd=tmpdir, check=True, capture_output=True)
            
            status = ProjectStatus(tmpdir)
            age = status.get_charter_doc_age("VISION.md")
            assert age is not None
            assert age != "Not found"
            assert "second" in age or "minute" in age or "hour" in age or "day" in age
    
    def test_format_status_output(self):
        """Test formatted status output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
            
            # Create initial commit
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmpdir, check=True, capture_output=True)
            
            status = ProjectStatus(tmpdir)
            output = status.format_status()
            
            assert "📊 Project:" in output
            assert "📍 Location:" in output
            assert "🌿 Git Status:" in output
            assert "Branch:" in output
            assert "📋 Charter Documents:" in output
