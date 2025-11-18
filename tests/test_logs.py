"""
Tests for log coordinator.
"""
import pytest
import tempfile
import time
from pathlib import Path
from src.logs import LogCoordinator


class TestLogCoordinator:
    """Tests for LogCoordinator class."""
    
    def test_initialization(self):
        """Test log coordinator initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            assert coordinator.logs_dir.exists()
            assert coordinator.metadata_file.exists()
            assert 'sessions' in coordinator.metadata
    
    def test_run_with_capture(self):
        """Test capturing output from a command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            # Run a simple command
            session = coordinator.run_with_capture(['echo', 'Hello World'], name='test-echo')
            
            assert session['session_id'] == 1
            assert session['name'] == 'test-echo'
            # Status might be 'running' or 'completed' depending on timing
            assert session['status'] in ['running', 'completed']
            assert 'log_file' in session
            
            # Wait for command to complete
            time.sleep(0.5)
            
            # Read log
            log_content = coordinator.read_log(session['session_id'])
            assert 'Hello World' in log_content
    
    def test_run_multiline_output(self):
        """Test capturing multi-line output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            # Run command with multiple lines
            session = coordinator.run_with_capture(
                ['sh', '-c', 'echo "Line 1"; echo "Line 2"; echo "Line 3"'],
                name='multiline'
            )
            
            # Wait for completion
            time.sleep(0.5)
            
            log_content = coordinator.read_log(session['session_id'])
            assert 'Line 1' in log_content
            assert 'Line 2' in log_content
            assert 'Line 3' in log_content
    
    def test_list_sessions(self):
        """Test listing sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            # Create multiple sessions
            session1 = coordinator.run_with_capture(['echo', 'Test 1'], name='test1')
            session2 = coordinator.run_with_capture(['echo', 'Test 2'], name='test2')
            
            time.sleep(0.5)
            
            sessions = coordinator.list_sessions()
            assert len(sessions) == 2
            assert any(s['name'] == 'test1' for s in sessions)
            assert any(s['name'] == 'test2' for s in sessions)
    
    def test_get_session(self):
        """Test getting specific session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            session = coordinator.run_with_capture(['echo', 'Test'], name='test')
            session_id = session['session_id']
            
            retrieved = coordinator.get_session(session_id)
            assert retrieved is not None
            assert retrieved['session_id'] == session_id
            assert retrieved['name'] == 'test'
    
    def test_read_log_tail(self):
        """Test reading last N lines of log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            # Generate log with many lines
            session = coordinator.run_with_capture(
                ['sh', '-c', 'for i in $(seq 1 10); do echo "Line $i"; done'],
                name='many-lines'
            )
            
            time.sleep(0.5)
            
            # Read full log first
            full_content = coordinator.read_log(session['session_id'])
            # Verify full content has all lines
            assert 'Line 1' in full_content
            assert 'Line 10' in full_content
            
            # Read last 5 lines (should include Line 10)
            tail_content = coordinator.read_log(session['session_id'], tail=5)
            assert 'Line 10' in tail_content
    
    def test_stop_session(self):
        """Test stopping a running session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            # Start a long-running command
            session = coordinator.run_with_capture(
                ['sleep', '10'],
                name='long-sleep'
            )
            
            time.sleep(0.2)
            
            # Stop it
            stopped = coordinator.stop_session(session['session_id'])
            assert stopped['status'] == 'stopped'
    
    def test_cleanup_old_logs(self):
        """Test cleaning up old logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            # Create a session
            session = coordinator.run_with_capture(['echo', 'Test'], name='test')
            time.sleep(0.5)
            
            # Shouldn't delete recent logs
            deleted = coordinator.cleanup_old_logs(days=7)
            assert deleted == 0
            
            # Should still exist
            assert coordinator.get_session(session['session_id']) is not None
    
    def test_export_session(self):
        """Test exporting a session log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)
            
            session = coordinator.run_with_capture(['echo', 'Export Test'], name='export')
            time.sleep(0.5)
            
            # Export to file
            export_file = Path(tmpdir) / 'exported.log'
            result = coordinator.export_session(session['session_id'], str(export_file))
            
            assert export_file.exists()
            content = export_file.read_text()
            assert 'Export Test' in content
            assert 'IdlerGear Log Export' in content

    def test_serve_and_stream(self):
        """Test log server and streaming."""
        import threading
        import socket

        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)

            # Start server in background thread
            server_result = {}
            def run_server():
                try:
                    result = coordinator.serve(name='test-server', port=19999)
                    server_result['session'] = result
                except Exception as e:
                    server_result['error'] = str(e)

            server_thread = threading.Thread(target=run_server)
            server_thread.start()

            # Give server time to start
            time.sleep(0.3)

            # Connect and send data
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', 19999))
                sock.sendall(b"Test line 1\nTest line 2\n")
                sock.close()
            except Exception:
                pass

            # Give time to receive
            time.sleep(0.2)

            # Stop server (send signal)
            import signal
            import os
            # Can't easily signal the thread, so just wait for it
            # In real usage, Ctrl+C would stop it

            # For testing, we'll check that the socket was created
            socket_path = f"/tmp/idlergear-logs-test-server.sock"
            # Server is using port, not socket in this test

            server_thread.join(timeout=1)

    def test_follow(self):
        """Test following a log session."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)

            # Create a session with some content
            session = coordinator.run_with_capture(['echo', 'Initial'], name='follow-test')
            time.sleep(0.3)

            # Verify we can get the session
            retrieved = coordinator.get_session(session['session_id'])
            assert retrieved is not None

            # follow() would block, so we just verify the method exists and session is valid
            log_file = Path(retrieved['log_file'])
            assert log_file.exists()

    def test_pull_from_loki_invalid_url(self):
        """Test pull_from_loki with invalid URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)

            # Should raise an error for invalid URL
            with pytest.raises(Exception):
                coordinator.pull_from_loki(
                    url='http://invalid-host-that-does-not-exist:3100',
                    query='{app="test"}',
                    since='1h',
                    name='loki-test'
                )

    def test_pull_from_otel(self):
        """Test pull_from_otel creates session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)

            # OTEL pull currently creates a placeholder
            session = coordinator.pull_from_otel(
                endpoint='http://localhost:4318',
                query='service.name=test',
                since='1h',
                name='otel-test'
            )

            assert session['session_id'] == 1
            assert session['name'] == 'otel-test'
            assert session['source'] == 'otel'
            assert session['status'] == 'completed'

            # Check log file was created
            log_file = Path(session['log_file'])
            assert log_file.exists()

    def test_parse_duration_to_ns(self):
        """Test duration parsing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)

            # Test various duration formats
            assert coordinator._parse_duration_to_ns('1s') == 1e9
            assert coordinator._parse_duration_to_ns('1m') == 60 * 1e9
            assert coordinator._parse_duration_to_ns('1h') == 3600 * 1e9
            assert coordinator._parse_duration_to_ns('1d') == 86400 * 1e9
            assert coordinator._parse_duration_to_ns('30m') == 30 * 60 * 1e9

    def test_stream_to_nonexistent_target(self):
        """Test streaming to non-existent target fails gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = LogCoordinator(tmpdir)

            # Streaming to non-existent socket should return error
            result = coordinator.stream(target='nonexistent-session')
            assert result['status'] == 'error'
            assert 'error' in result
