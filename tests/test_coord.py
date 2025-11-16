"""Tests for coordination repository."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.coord import CoordRepo


@pytest.fixture
def temp_coord_path():
    """Create a temporary coordination repo path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "coord"


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls."""
    with patch('src.coord.subprocess') as mock:
        yield mock


class TestCoordRepo:
    """Tests for CoordRepo class."""
    
    def test_initialization(self, temp_coord_path):
        """Test coordinator initialization."""
        coord = CoordRepo(temp_coord_path)
        assert coord.coord_path == temp_coord_path
        assert coord.repo_name == "idlergear-coord"
    
    def test_init_creates_repo(self, temp_coord_path, mock_subprocess):
        """Test init creates coordination repository."""
        # Mock successful repo creation
        mock_subprocess.run.return_value = Mock(returncode=0)
        
        # Mock that cloned directory exists
        cloned_path = Path.cwd() / "idlergear-coord"
        
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.rename') as mock_rename:
            
            # First check: coord_path doesn't exist
            # Second check: cloned_path exists
            mock_exists.side_effect = [False, True]
            
            coord = CoordRepo(temp_coord_path)
            result = coord.init()
            
            # Check that gh repo create was called
            assert any('gh' in str(call) and 'repo' in str(call) and 'create' in str(call) 
                      for call in mock_subprocess.run.call_args_list)
    
    def test_init_already_exists(self, temp_coord_path):
        """Test init when coordination repo already exists."""
        # Create a fake existing repo
        temp_coord_path.mkdir(parents=True)
        (temp_coord_path / ".git").mkdir()
        
        coord = CoordRepo(temp_coord_path)
        result = coord.init()
        
        assert result['status'] == 'already_exists'
        assert result['path'] == str(temp_coord_path)
    
    def test_send_message_file_method(self, temp_coord_path, mock_subprocess):
        """Test sending message via file method."""
        # Setup existing coord repo
        temp_coord_path.mkdir(parents=True)
        (temp_coord_path / ".git").mkdir()
        
        mock_subprocess.run.return_value = Mock(returncode=0)
        
        coord = CoordRepo(temp_coord_path)
        result = coord.send_message("test-project", "Hello from local", to="web", via="file")
        
        assert result['status'] == 'sent'
        assert result['via'] == 'file'
        assert 'message_id' in result
        
        # Check that message file was created
        messages_dir = temp_coord_path / "projects" / "test-project" / "messages"
        assert messages_dir.exists()
        
        # Check that at least one message file exists
        message_files = list(messages_dir.glob("*.json"))
        assert len(message_files) > 0
    
    def test_send_message_not_initialized(self, temp_coord_path):
        """Test sending message when repo not initialized."""
        coord = CoordRepo(temp_coord_path)
        result = coord.send_message("test-project", "Test", via="file")
        
        assert result['status'] == 'error'
        assert 'not initialized' in result['error']
    
    def test_read_messages_file_method(self, temp_coord_path, mock_subprocess):
        """Test reading messages via file method."""
        # Setup existing coord repo
        temp_coord_path.mkdir(parents=True)
        (temp_coord_path / ".git").mkdir()
        messages_dir = temp_coord_path / "projects" / "test-project" / "messages"
        messages_dir.mkdir(parents=True)
        
        # Create a test message
        import json
        from datetime import datetime
        
        msg_file = messages_dir / "20240101-120000.json"
        msg_data = {
            "id": "20240101-120000",
            "timestamp": datetime.utcnow().isoformat(),
            "from": "local",
            "to": "web",
            "message": "Test message",
            "status": "sent"
        }
        msg_file.write_text(json.dumps(msg_data))
        
        mock_subprocess.run.return_value = Mock(returncode=0)
        
        coord = CoordRepo(temp_coord_path)
        result = coord.read_messages("test-project", via="file")
        
        assert result['status'] == 'ok'
        assert result['count'] == 1
        assert len(result['messages']) == 1
        assert result['messages'][0]['message'] == "Test message"
    
    def test_read_messages_no_messages(self, temp_coord_path, mock_subprocess):
        """Test reading messages when none exist."""
        temp_coord_path.mkdir(parents=True)
        (temp_coord_path / ".git").mkdir()
        
        mock_subprocess.run.return_value = Mock(returncode=0)
        
        coord = CoordRepo(temp_coord_path)
        result = coord.read_messages("test-project", via="file")
        
        assert result['status'] == 'ok'
        assert result['messages'] == []
        assert result['count'] == 0
    
    def test_send_via_issue(self, temp_coord_path, mock_subprocess):
        """Test sending message via GitHub issue."""
        temp_coord_path.mkdir(parents=True)
        (temp_coord_path / ".git").mkdir()
        
        # Mock successful issue creation
        mock_result = Mock()
        mock_result.stdout = "https://github.com/user/idlergear-coord/issues/1"
        mock_subprocess.run.return_value = mock_result
        
        with patch.object(CoordRepo, '_get_remote_url', return_value="https://github.com/user/idlergear-coord"):
            coord = CoordRepo(temp_coord_path)
            result = coord.send_message("test-project", "Test issue", via="issue")
            
            assert result['status'] == 'sent'
            assert result['via'] == 'issue'
            assert 'issue_url' in result
    
    def test_read_via_issue(self, temp_coord_path, mock_subprocess):
        """Test reading messages via GitHub issues."""
        temp_coord_path.mkdir(parents=True)
        (temp_coord_path / ".git").mkdir()
        
        # Mock issue list response
        mock_result = Mock()
        mock_result.stdout = '''[
            {
                "number": 1,
                "title": "[test-project] Message to web",
                "body": "Test body",
                "createdAt": "2024-01-01T12:00:00Z",
                "state": "open"
            }
        ]'''
        mock_subprocess.run.return_value = mock_result
        
        with patch.object(CoordRepo, '_get_remote_url', return_value="https://github.com/user/idlergear-coord"):
            coord = CoordRepo(temp_coord_path)
            result = coord.read_messages("test-project", via="issue")
            
            assert result['status'] == 'ok'
            assert result['count'] == 1
            assert result['messages'][0]['number'] == 1
    
    def test_unknown_via_method(self, temp_coord_path):
        """Test using unknown via method."""
        temp_coord_path.mkdir(parents=True)
        (temp_coord_path / ".git").mkdir()
        
        coord = CoordRepo(temp_coord_path)
        result = coord.send_message("test-project", "Test", via="unknown")
        
        assert result['status'] == 'error'
        assert 'Unknown method' in result['error']
