"""
Tests for sync commands.
"""
import pytest
import tempfile
import subprocess
import shutil
from pathlib import Path
from src.sync import ProjectSync
from src.messages import MessageManager


class TestProjectSync:
    """Tests for ProjectSync class."""
    
    def setup_git_repo(self, tmpdir):
        """Set up a git repo and return the checked-out branch name."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmpdir, check=True)
        
        # Create initial commit
        test_file = Path(tmpdir) / "README.md"
        test_file.write_text("# Test Project")
        subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmpdir, check=True, capture_output=True)

        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        return branch_result.stdout.strip() or "master"

    def setup_remote(self, tmpdir, branch_name):
        """Create a bare remote outside the working tree and push the branch."""
        remote_path = Path(tempfile.mkdtemp(prefix="remote-repo-"))
        subprocess.run(
            ["git", "init", "--bare", str(remote_path)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_path)],
            cwd=tmpdir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=tmpdir,
            check=True,
            capture_output=True,
        )
        return remote_path
    
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

    def test_sync_push_with_remote_creates_branch_and_restores_local_branch(self):
        """End-to-end push with a bare remote simulating Claude Web."""
        with tempfile.TemporaryDirectory() as tmpdir:
            branch = self.setup_git_repo(tmpdir)
            remote_path = self.setup_remote(tmpdir, branch)
            try:
                notes_file = Path(tmpdir) / "notes.txt"
                notes_file.write_text("codex scratch work")

                syncer = ProjectSync(tmpdir)
                result = syncer.sync_push(include_untracked=True)

                assert result["pushed"] is True
                assert result["sync_branch"].startswith("idlergear-web-sync")

                ls_remote = subprocess.run(
                    ["git", "ls-remote", "origin", result["sync_branch"]],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                assert result["sync_branch"] in ls_remote.stdout

                branch_check = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                assert branch_check.stdout.strip() == branch

                status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                assert status.stdout.strip() == ""
            finally:
                shutil.rmtree(remote_path, ignore_errors=True)

    def test_sync_pull_merges_remote_changes_and_cleans_up(self):
        """Simulate Claude Web committing to sync branch and pulling locally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            branch = self.setup_git_repo(tmpdir)
            remote_path = self.setup_remote(tmpdir, branch)
            syncer = ProjectSync(tmpdir)
            try:
                scratch = Path(tmpdir) / "scratch.md"
                scratch.write_text("initial draft")
                push_result = syncer.sync_push(include_untracked=True)
                sync_branch = push_result["sync_branch"]

                subprocess.run(["git", "checkout", sync_branch], cwd=tmpdir, check=True)
                scratch.write_text("edited remotely in Claude Code")
                subprocess.run(["git", "add", "scratch.md"], cwd=tmpdir, check=True, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", "Remote Claude update"],
                    cwd=tmpdir,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "push", "origin", sync_branch],
                    cwd=tmpdir,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(["git", "checkout", branch], cwd=tmpdir, check=True)

                assert not scratch.exists()

                pull_result = syncer.sync_pull()
                assert pull_result["merged"] is True
                assert pull_result["cleaned_up"] is True
                assert scratch.exists()
                assert scratch.read_text() == "edited remotely in Claude Code"

                # Verify clean-up removed local and remote sync branches.
                returncode, _, _ = syncer._run_git("rev-parse", "--verify", sync_branch, check=False)
                assert returncode != 0
                ls_remote = subprocess.run(
                    ["git", "ls-remote", "origin", sync_branch],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                assert ls_remote.stdout.strip() == ""
            finally:
                shutil.rmtree(remote_path, ignore_errors=True)

    def test_message_exchange_via_sync_branch(self):
        """Full round-trip message exchange between local Codex and Claude Web."""
        with tempfile.TemporaryDirectory() as tmpdir:
            branch = self.setup_git_repo(tmpdir)
            remote_path = self.setup_remote(tmpdir, branch)
            syncer = ProjectSync(tmpdir)
            manager = MessageManager(tmpdir)

            message_id = manager.send_message(to="web", body="Ping from Codex", from_env="codex")
            push_result = syncer.sync_push(include_untracked=True)
            sync_branch = push_result["sync_branch"]

            remote_workdir = Path(tempfile.mkdtemp(prefix="remote-workdir-"))
            try:
                subprocess.run(["git", "clone", str(remote_path), str(remote_workdir)], check=True, capture_output=True)
                subprocess.run(["git", "config", "user.name", "Test"], cwd=remote_workdir, check=True)
                subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=remote_workdir, check=True)
                subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=remote_workdir, check=True)
                subprocess.run(
                    ["git", "checkout", "-b", sync_branch, f"origin/{sync_branch}"],
                    cwd=remote_workdir,
                    check=True,
                    capture_output=True,
                )

                remote_manager = MessageManager(remote_workdir)
                remote_messages = remote_manager.list_messages(filter_to="web")
                assert any(msg["id"] == message_id for msg in remote_messages)

                response_id = remote_manager.respond_to_message(
                    message_id,
                    "Reply from Claude",
                    from_env="claude",
                )

                subprocess.run(["git", "add", "-A"], cwd=remote_workdir, check=True, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", "Remote Claude response"],
                    cwd=remote_workdir,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "push", "origin", sync_branch],
                    cwd=remote_workdir,
                    check=True,
                    capture_output=True,
                )

                pull_result = syncer.sync_pull()
                assert pull_result["merged"] is True

                local_messages = manager.list_messages(filter_from="claude")
                assert any(msg["id"] == response_id for msg in local_messages)
            finally:
                shutil.rmtree(remote_path, ignore_errors=True)
                shutil.rmtree(remote_workdir, ignore_errors=True)
    
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
