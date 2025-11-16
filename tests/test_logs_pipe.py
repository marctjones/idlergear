"""
Tests for log pipe/stdin capture.
"""
import pytest
import tempfile
import subprocess
from pathlib import Path
from src.logs import LogCoordinator


class TestLogPipe:
    """Tests for piped input capture."""
    
    def test_capture_stdin_basic(self):
        """Test basic stdin capture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            # Simulate stdin input
            import sys
            from io import StringIO
            
            # Save original stdin
            original_stdin = sys.stdin
            
            try:
                # Replace stdin with test data
                sys.stdin = StringIO("Line 1\nLine 2\nLine 3\n")
                
                session = coordinator.capture_stdin(name="test-pipe", source="test")
                
                assert session['session_id'] == 1
                assert session['name'] == 'test-pipe'
                assert session['status'] == 'completed'
                assert session['line_count'] == 3
                
                # Read the log file
                log_file = Path(session['log_file'])
                assert log_file.exists()
                
                content = log_file.read_text()
                assert 'Line 1' in content
                assert 'Line 2' in content
                assert 'Line 3' in content
                assert '# Source: test' in content
                
            finally:
                sys.stdin = original_stdin
    
    def test_capture_stdin_empty(self):
        """Test capture with no input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            import sys
            from io import StringIO
            
            original_stdin = sys.stdin
            
            try:
                sys.stdin = StringIO("")
                
                session = coordinator.capture_stdin(name="empty")
                
                assert session['status'] == 'completed'
                assert session['line_count'] == 0
                
            finally:
                sys.stdin = original_stdin
    
    def test_capture_stdin_default_name(self):
        """Test capture with default name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            import sys
            from io import StringIO
            
            original_stdin = sys.stdin
            
            try:
                sys.stdin = StringIO("test")
                
                session = coordinator.capture_stdin()
                
                assert session['name'] == 'piped-input'
                assert session['source'] == 'stdin'
                
            finally:
                sys.stdin = original_stdin
    
    def test_pipe_cli_integration(self):
        """Test actual CLI pipe command."""
        import subprocess
        
        # Test piping to CLI command
        process = subprocess.Popen(
            ['python', '-m', 'src.main', 'logs', 'pipe', '--name', 'cli-test', '--path', '.'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd='/home/marc/idlergear'
        )
        
        stdout, stderr = process.communicate(input="CLI Line 1\nCLI Line 2\n")
        
        assert process.returncode == 0
        assert 'Capture completed' in stdout or 'Capture completed' in stderr
        assert 'Session ID:' in stdout or 'Session ID:' in stderr
    
    def test_metadata_updates_correctly(self):
        """Test that metadata is updated correctly for piped input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            import sys
            from io import StringIO
            
            original_stdin = sys.stdin
            
            try:
                sys.stdin = StringIO("data\n")
                
                session = coordinator.capture_stdin(name="meta-test", source="test-source")
                
                # Reload metadata
                coordinator2 = LogCoordinator(tmpdir)
                sessions = coordinator2.list_sessions()
                
                assert len(sessions) == 1
                assert sessions[0]['name'] == 'meta-test'
                assert sessions[0]['status'] == 'completed'
                
            finally:
                sys.stdin = original_stdin
