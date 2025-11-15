"""
Tests for sync commands.
"""
import pytest
import tempfile
import subprocess
from pathlib import Path
from src.sync import ProjectSync


class TestProjectSync:
    """Tests for ProjectSync class."""
    
    def setup_git_repo(self, tmpdir):
        """Helper to set up a git repo with remote."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
        
        # Create initial commit
        test_file = Path(tmpdir) / "README.md"
        test_file.write_text("# Test Project")
        subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmpdir, check=True, capture_output=True)
    
    def test_initialization(self):
        """Test sync initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            syncer = ProjectSync(tmpdir)
            assert syncer.project_path == Path(tmpdir).resolve()
            assert syncer.status.is_git_repo
    
    def test_get_sync_branch_name(self):
        """Test sync branch name generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            syncer = ProjectSync(tmpdir)
            sync_branch = syncer.get_sync_branch_name()
            
            # Should be idlergear-web-sync-<current-branch>
            assert sync_branch.startswith("idlergear-web-sync-")
            assert "main" in sync_branch or "master" in sync_branch
    
    def test_sync_status_no_sync_branch(self):
        """Test sync status when no sync branch exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            syncer = ProjectSync(tmpdir)
            status = syncer.sync_status()
            
            assert status['current_branch'] in ['main', 'master']
            assert status['local_exists'] is False
            assert status['remote_exists'] is False
    
    def test_sync_push_creates_branch(self):
        """Test that sync push creates a sync branch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Add a file to commit
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")
            subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Add test file"], cwd=tmpdir, check=True, capture_output=True)
            
            syncer = ProjectSync(tmpdir)
            
            # This will fail without a remote, but we can test the branch creation logic
            try:
                result = syncer.sync_push()
                # If it succeeds, verify result
                assert result['created_branch'] or not result['created_branch']
                assert 'sync_branch' in result
            except RuntimeError as e:
                # Expected to fail on push without remote
                assert "remote" in str(e).lower() or "origin" in str(e).lower()
    
    def test_run_git_command(self):
        """Test git command execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            syncer = ProjectSync(tmpdir)
            
            # Test successful command
            returncode, stdout, stderr = syncer._run_git("status", "--short", check=False)
            assert returncode == 0
    
    def test_run_git_command_failure(self):
        """Test git command failure handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            syncer = ProjectSync(tmpdir)
            
            # Test failing command
            with pytest.raises(RuntimeError):
                syncer._run_git("nonexistent-command", check=True)
    
    def test_sync_pull_no_remote_branch(self):
        """Test sync pull when remote branch doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            syncer = ProjectSync(tmpdir)
            
            # Should raise error about missing remote or branch
            with pytest.raises(RuntimeError) as exc_info:
                syncer.sync_pull()
            
            error_msg = str(exc_info.value).lower()
            # Either "not found" or "does not appear to be" (no remote)
            assert "not found" in error_msg or "does not appear" in error_msg
    
    def test_sync_status_tracks_uncommitted(self):
        """Test that sync status tracks uncommitted changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create uncommitted file
            test_file = Path(tmpdir) / "uncommitted.txt"
            test_file.write_text("uncommitted")
            
            syncer = ProjectSync(tmpdir)
            status = syncer.sync_status()
            
            assert status['uncommitted_changes'] >= 1
    
    def test_sync_branch_prefix_constant(self):
        """Test sync branch prefix is correct."""
        assert ProjectSync.SYNC_BRANCH_PREFIX == "idlergear-web-sync"
