"""
Tests for MessageManager and CLI messaging flow.
"""
import json
from pathlib import Path
from src.messages import MessageManager


def test_send_message_creates_file(tmp_path):
    manager = MessageManager(tmp_path)
    message_id = manager.send_message(to="web", body="Hello Claude", from_env="codex")
    
    message_file = tmp_path / ".idlergear" / "messages" / f"{message_id}.json"
    assert message_file.exists()
    
    message = json.loads(message_file.read_text())
    assert message["body"] == "Hello Claude"
    assert message["to"] == "web"
    assert message["from"] == "codex"


def test_list_filters_and_ordering(tmp_path):
    manager = MessageManager(tmp_path)
    first = manager.send_message(to="web", body="First", from_env="codex")
    second = manager.send_message(to="local", body="Second", from_env="claude")
    
    all_msgs = manager.list_messages()
    assert [msg["id"] for msg in all_msgs] == [second, first]  # reverse chronological
    
    filtered = manager.list_messages(filter_to="web")
    assert len(filtered) == 1
    assert filtered[0]["id"] == first
    
    filtered_from = manager.list_messages(filter_from="claude")
    assert len(filtered_from) == 1
    assert filtered_from[0]["id"] == second


def test_read_marks_message_as_read(tmp_path):
    manager = MessageManager(tmp_path)
    message_id = manager.send_message(to="web", body="Ping")
    
    message = manager.read_message(message_id)
    assert message["status"] == "read"
    
    # File should persist status
    message_file = tmp_path / ".idlergear" / "messages" / f"{message_id}.json"
    persisted = json.loads(message_file.read_text())
    assert persisted["status"] == "read"
    assert "read_at" in persisted


def test_respond_links_messages(tmp_path):
    manager = MessageManager(tmp_path)
    message_id = manager.send_message(to="web", body="Codex ping", from_env="codex")
    
    response_id = manager.respond_to_message(message_id, "Claude ack", from_env="claude")
    
    response_file = tmp_path / ".idlergear" / "messages" / f"{response_id}.json"
    response = json.loads(response_file.read_text())
    assert response["in_reply_to"] == message_id
    assert response["from"] == "claude"
