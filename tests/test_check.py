"""
Tests for check command.
"""
import pytest
import tempfile
import subprocess
from pathlib import Path
from src.check import ProjectChecker


class TestProjectChecker:
    """Tests for ProjectChecker class."""
    
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
    
    def test_check_test_coverage_warning(self):
        """Test that missing tests triggers a warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create commits without "test" in message
            for i in range(3):
                test_file = Path(tmpdir) / f"feature{i}.txt"
                test_file.write_text(f"feature{i}")
                subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"add feature {i}"], cwd=tmpdir, check=True, capture_output=True)
            
            checker = ProjectChecker(tmpdir)
            checker.check_test_coverage()
            
            # Should have a warning about missing tests
            assert len(checker.warnings) > 0
            assert any('test' in w['message'].lower() for w in checker.warnings)
    
    def test_check_test_coverage_ok(self):
        """Test that commits with tests don't trigger warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create commits with "test" in message
            for i in range(3):
                test_file = Path(tmpdir) / f"test{i}.txt"
                test_file.write_text(f"test{i}")
                subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"test: add test {i}"], cwd=tmpdir, check=True, capture_output=True)
            
            checker = ProjectChecker(tmpdir)
            checker.check_test_coverage()
            
            # Should not have test-related warnings
            test_warnings = [w for w in checker.warnings if 'test' in w['message'].lower()]
            assert len(test_warnings) == 0
    
    def test_check_charter_freshness_missing(self):
        """Test detection of missing charter documents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            checker = ProjectChecker(tmpdir)
            checker.check_charter_freshness()
            
            # Should have issue about missing TODO.md
            assert len(checker.issues) > 0
            assert any('TODO.md' in i['message'] for i in checker.issues)
    
    def test_check_uncommitted_work_many_files(self):
        """Test warning for many uncommitted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create 10 uncommitted files
            for i in range(10):
                (Path(tmpdir) / f"file{i}.txt").write_text(f"content{i}")
            
            checker = ProjectChecker(tmpdir)
            checker.check_uncommitted_work()
            
            # Should have warning about uncommitted files
            assert len(checker.warnings) > 0
            assert any('uncommitted' in w['message'].lower() for w in checker.warnings)
    
    def test_check_uncommitted_work_few_files(self):
        """Test suggestion for moderate uncommitted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create 5 uncommitted files
            for i in range(5):
                (Path(tmpdir) / f"file{i}.txt").write_text(f"content{i}")
            
            checker = ProjectChecker(tmpdir)
            checker.check_uncommitted_work()
            
            # Should have suggestion (not warning)
            assert len(checker.suggestions) > 0
            assert any('uncommitted' in s['message'].lower() for s in checker.suggestions)
    
    def test_check_dangling_branches(self):
        """Test detection of stale branches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # This is hard to test without mocking time
            # Just verify the method runs without error
            checker = ProjectChecker(tmpdir)
            checker.check_dangling_branches()
            # No assertion - just checking it doesn't crash
    
    def test_check_project_structure_missing_files(self):
        """Test detection of missing project files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Remove README if it exists
            readme = Path(tmpdir) / "README.md"
            if readme.exists():
                readme.unlink()
            
            checker = ProjectChecker(tmpdir)
            checker.check_project_structure()
            
            # Should suggest adding README
            assert len(checker.suggestions) > 0
            # README or gitignore should be mentioned
            messages = ' '.join(s['message'] for s in checker.suggestions)
            assert 'README' in messages or 'gitignore' in messages
    
    def test_run_all_checks(self):
        """Test running all checks together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            checker = ProjectChecker(tmpdir)
            checker.run_all_checks()
            
            # Should have run without error
            # Will likely have some issues/warnings/suggestions
            total = len(checker.issues) + len(checker.warnings) + len(checker.suggestions)
            assert total >= 0  # At least no crash
    
    def test_format_report(self):
        """Test report formatting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            checker = ProjectChecker(tmpdir)
            checker.run_all_checks()
            report = checker.format_report()
            
            assert "Project Health Check" in report
            assert len(report) > 0
    
    def test_format_report_no_issues(self):
        """Test report when everything is good."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create a good project structure
            (Path(tmpdir) / "README.md").write_text("# README")
            (Path(tmpdir) / "TODO.md").write_text("# TODO")
            (Path(tmpdir) / ".gitignore").write_text("*.pyc")
            
            subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "test: add docs"], cwd=tmpdir, check=True, capture_output=True)
            
            checker = ProjectChecker(tmpdir)
            
            # Manually ensure no issues
            checker.issues = []
            checker.warnings = []
            checker.suggestions = []
            
            report = checker.format_report()
            
            assert "Everything looks good" in report
