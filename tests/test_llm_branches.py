"""
Tests for LLM branch tracking in status command.
"""
import pytest
import tempfile
import subprocess
from pathlib import Path
from src.status import ProjectStatus


class TestLLMBranchTracking:
    """Tests for LLM-managed branch identification."""
    
    def setup_git_repo(self, tmpdir):
        """Helper to set up a git repo with commits."""
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmpdir, check=True)
        
        # Create initial commit
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=tmpdir, check=True, capture_output=True)
        
        # Get the default branch name (might be 'main' or 'master')
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    
    def test_detect_web_sync_branch(self):
        """Test detection of idlergear-web-sync branches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_branch = self.setup_git_repo(tmpdir)
            
            # Create web sync branch
            subprocess.run(["git", "checkout", "-b", "idlergear-web-sync"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", default_branch], cwd=tmpdir, check=True, capture_output=True)
            
            status = ProjectStatus(tmpdir)
            llm_branches = status.get_llm_managed_branches()
            
            assert 'idlergear-web-sync' in llm_branches['web_sync']
    
    def test_detect_claude_branches(self):
        """Test detection of Claude-managed branches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_branch = self.setup_git_repo(tmpdir)
            
            # Create Claude branches
            subprocess.run(["git", "checkout", "-b", "claude-feature"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", default_branch], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", "-b", "claude-code-test"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", default_branch], cwd=tmpdir, check=True, capture_output=True)
            
            status = ProjectStatus(tmpdir)
            llm_branches = status.get_llm_managed_branches()
            
            assert 'claude-feature' in llm_branches['claude']
            assert 'claude-code-test' in llm_branches['claude']
    
    def test_detect_copilot_branches(self):
        """Test detection of Copilot-managed branches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_branch = self.setup_git_repo(tmpdir)
            
            subprocess.run(["git", "checkout", "-b", "copilot-feature"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", default_branch], cwd=tmpdir, check=True, capture_output=True)
            
            status = ProjectStatus(tmpdir)
            llm_branches = status.get_llm_managed_branches()
            
            assert 'copilot-feature' in llm_branches['copilot']
    
    def test_detect_gemini_branches(self):
        """Test detection of Gemini-managed branches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_branch = self.setup_git_repo(tmpdir)
            
            subprocess.run(["git", "checkout", "-b", "gemini-refactor"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", default_branch], cwd=tmpdir, check=True, capture_output=True)
            
            status = ProjectStatus(tmpdir)
            llm_branches = status.get_llm_managed_branches()
            
            assert 'gemini-refactor' in llm_branches['gemini']
    
    def test_ignore_main_branches(self):
        """Test that main/master branches are not flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_branch = self.setup_git_repo(tmpdir)
            
            status = ProjectStatus(tmpdir)
            llm_branches = status.get_llm_managed_branches()
            
            # No main branch should appear in any category
            all_branches = []
            for category in llm_branches.values():
                all_branches.extend(category)
            
            assert 'main' not in all_branches
            assert 'master' not in all_branches
    
    def test_status_output_with_llm_branches(self):
        """Test that status output includes LLM branches section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_branch = self.setup_git_repo(tmpdir)
            
            # Create various LLM branches
            subprocess.run(["git", "checkout", "-b", "claude-feature"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", default_branch], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", "-b", "idlergear-web-sync"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "checkout", default_branch], cwd=tmpdir, check=True, capture_output=True)
            
            status = ProjectStatus(tmpdir)
            output = status.format_status()
            
            assert "🤖 LLM-Managed Branches:" in output
            assert "Claude:" in output
            assert "Web Sync:" in output
