"""Tests for MCP server functionality."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from idlergear.mcp_server import _check_initialized, _format_result, call_tool, list_tools


@pytest.fixture
def mcp_project():
    """Create a temporary project for MCP tests."""
    from idlergear.init import init_project

    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            os.chdir(project_path)
            init_project(".")
            yield project_path
    finally:
        os.chdir(old_cwd)


class TestFormatResult:
    """Tests for _format_result helper."""

    def test_format_none(self):
        result = _format_result(None)
        assert len(result) == 1
        assert result[0].text == "null"

    def test_format_dict(self):
        result = _format_result({"key": "value"})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["key"] == "value"

    def test_format_list(self):
        result = _format_result([1, 2, 3])
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data == [1, 2, 3]

    def test_format_string(self):
        result = _format_result("hello")
        assert len(result) == 1
        assert json.loads(result[0].text) == "hello"


class TestCheckInitialized:
    """Tests for _check_initialized helper."""

    def test_not_initialized(self, save_cwd):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            with pytest.raises(ValueError, match="not initialized"):
                _check_initialized()

    def test_initialized(self, mcp_project):
        # Should not raise
        _check_initialized()


class TestListTools:
    """Tests for list_tools."""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        tools = await list_tools()

        assert len(tools) > 0

        # Check some expected tools
        tool_names = [t.name for t in tools]
        assert "idlergear_task_create" in tool_names
        assert "idlergear_note_create" in tool_names
        assert "idlergear_vision_show" in tool_names
        assert "idlergear_plan_create" in tool_names
        assert "idlergear_reference_add" in tool_names
        assert "idlergear_run_start" in tool_names
        assert "idlergear_config_get" in tool_names

    @pytest.mark.asyncio
    async def test_tools_have_schemas(self):
        tools = await list_tools()

        for tool in tools:
            assert tool.name is not None
            assert tool.description is not None
            assert tool.inputSchema is not None


class TestCallToolTasks:
    """Tests for task-related tool calls."""

    @pytest.mark.asyncio
    async def test_task_create(self, mcp_project):
        result = await call_tool("idlergear_task_create", {"title": "Test task"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["title"] == "Test task"
        assert data["id"] == 1

    @pytest.mark.asyncio
    async def test_task_list(self, mcp_project):
        await call_tool("idlergear_task_create", {"title": "Task 1"})
        await call_tool("idlergear_task_create", {"title": "Task 2"})

        result = await call_tool("idlergear_task_list", {})

        data = json.loads(result[0].text)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_task_show(self, mcp_project):
        await call_tool("idlergear_task_create", {"title": "Test", "body": "Body"})

        result = await call_tool("idlergear_task_show", {"id": 1})

        data = json.loads(result[0].text)
        assert data["title"] == "Test"
        assert data["body"] == "Body"

    @pytest.mark.asyncio
    async def test_task_show_not_found(self, mcp_project):
        result = await call_tool("idlergear_task_show", {"id": 999})

        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_task_close(self, mcp_project):
        await call_tool("idlergear_task_create", {"title": "Test"})

        result = await call_tool("idlergear_task_close", {"id": 1})

        data = json.loads(result[0].text)
        assert data["state"] == "closed"

    @pytest.mark.asyncio
    async def test_task_update(self, mcp_project):
        await call_tool("idlergear_task_create", {"title": "Original"})

        result = await call_tool("idlergear_task_update", {"id": 1, "title": "Updated"})

        data = json.loads(result[0].text)
        assert data["title"] == "Updated"


class TestCallToolNotes:
    """Tests for note-related tool calls."""

    @pytest.mark.asyncio
    async def test_note_create(self, mcp_project):
        result = await call_tool("idlergear_note_create", {"content": "Quick note"})

        data = json.loads(result[0].text)
        assert data["id"] == 1
        assert data["content"] == "Quick note"

    @pytest.mark.asyncio
    async def test_note_list(self, mcp_project):
        await call_tool("idlergear_note_create", {"content": "Note 1"})
        await call_tool("idlergear_note_create", {"content": "Note 2"})

        result = await call_tool("idlergear_note_list", {})

        data = json.loads(result[0].text)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_note_delete(self, mcp_project):
        await call_tool("idlergear_note_create", {"content": "To delete"})

        result = await call_tool("idlergear_note_delete", {"id": 1})

        data = json.loads(result[0].text)
        assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_note_promote(self, mcp_project):
        await call_tool("idlergear_note_create", {"content": "Promote me"})

        result = await call_tool("idlergear_note_promote", {"id": 1, "to": "task"})

        data = json.loads(result[0].text)
        assert "id" in data  # New task ID


class TestCallToolExplore:
    """Tests for exploration-related tool calls (deprecated - redirects to notes with 'explore' tag)."""

    @pytest.mark.asyncio
    async def test_explore_create(self, mcp_project):
        """Deprecated explore_create now creates a note with 'explore' tag."""
        result = await call_tool("idlergear_explore_create", {"title": "Test exploration"})

        data = json.loads(result[0].text)
        # Now creates a note with content = title
        assert data["content"] == "Test exploration"
        assert "explore" in data["tags"]
        assert "deprecated" in data

    @pytest.mark.asyncio
    async def test_explore_list(self, mcp_project):
        """Deprecated explore_list now lists notes with 'explore' tag."""
        await call_tool("idlergear_explore_create", {"title": "Exp 1"})

        result = await call_tool("idlergear_explore_list", {})

        data = json.loads(result[0].text)
        assert len(data["notes"]) == 1
        assert "deprecated" in data

    @pytest.mark.asyncio
    async def test_explore_delete(self, mcp_project):
        """Deprecated explore_delete now deletes the note."""
        await call_tool("idlergear_explore_create", {"title": "Test"})

        result = await call_tool("idlergear_explore_delete", {"id": 1})

        data = json.loads(result[0].text)
        assert data["deleted"] is True
        assert "deprecated" in data


class TestCallToolVision:
    """Tests for vision-related tool calls."""

    @pytest.mark.asyncio
    async def test_vision_show(self, mcp_project):
        result = await call_tool("idlergear_vision_show", {})

        data = json.loads(result[0].text)
        assert "content" in data

    @pytest.mark.asyncio
    async def test_vision_edit(self, mcp_project):
        result = await call_tool("idlergear_vision_edit", {"content": "New vision"})

        data = json.loads(result[0].text)
        assert data["updated"] is True

        # Verify
        result = await call_tool("idlergear_vision_show", {})
        data = json.loads(result[0].text)
        assert "New vision" in data["content"]


class TestCallToolPlan:
    """Tests for plan-related tool calls."""

    @pytest.mark.asyncio
    async def test_plan_create(self, mcp_project):
        result = await call_tool("idlergear_plan_create", {"name": "my-plan"})

        data = json.loads(result[0].text)
        assert data["name"] == "my-plan"

    @pytest.mark.asyncio
    async def test_plan_list(self, mcp_project):
        await call_tool("idlergear_plan_create", {"name": "plan-a"})
        await call_tool("idlergear_plan_create", {"name": "plan-b"})

        result = await call_tool("idlergear_plan_list", {})

        data = json.loads(result[0].text)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_plan_switch(self, mcp_project):
        await call_tool("idlergear_plan_create", {"name": "my-plan"})

        result = await call_tool("idlergear_plan_switch", {"name": "my-plan"})

        data = json.loads(result[0].text)
        assert data["name"] == "my-plan"

    @pytest.mark.asyncio
    async def test_plan_show_current(self, mcp_project):
        await call_tool("idlergear_plan_create", {"name": "my-plan"})
        await call_tool("idlergear_plan_switch", {"name": "my-plan"})

        result = await call_tool("idlergear_plan_show", {})

        data = json.loads(result[0].text)
        assert data["name"] == "my-plan"


class TestCallToolReference:
    """Tests for reference-related tool calls."""

    @pytest.mark.asyncio
    async def test_reference_add(self, mcp_project):
        result = await call_tool("idlergear_reference_add", {"title": "API Guide"})

        data = json.loads(result[0].text)
        assert data["title"] == "API Guide"

    @pytest.mark.asyncio
    async def test_reference_list(self, mcp_project):
        await call_tool("idlergear_reference_add", {"title": "Doc 1"})
        await call_tool("idlergear_reference_add", {"title": "Doc 2"})

        result = await call_tool("idlergear_reference_list", {})

        data = json.loads(result[0].text)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_reference_search(self, mcp_project):
        await call_tool("idlergear_reference_add", {"title": "Python Guide"})
        await call_tool("idlergear_reference_add", {"title": "Other Doc"})

        result = await call_tool("idlergear_reference_search", {"query": "python"})

        data = json.loads(result[0].text)
        assert len(data) == 1


class TestCallToolConfig:
    """Tests for config-related tool calls."""

    @pytest.mark.asyncio
    async def test_config_set_get(self, mcp_project):
        await call_tool("idlergear_config_set", {"key": "test.key", "value": "test-value"})

        result = await call_tool("idlergear_config_get", {"key": "test.key"})

        data = json.loads(result[0].text)
        assert data["value"] == "test-value"


class TestCallToolRuns:
    """Tests for run-related tool calls."""

    @pytest.mark.asyncio
    async def test_run_start(self, mcp_project):
        result = await call_tool("idlergear_run_start", {"command": "echo hello", "name": "test-run"})

        data = json.loads(result[0].text)
        assert data["name"] == "test-run"
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_run_list(self, mcp_project):
        import time

        await call_tool("idlergear_run_start", {"command": "echo test", "name": "run-1"})
        time.sleep(0.3)

        result = await call_tool("idlergear_run_list", {})

        data = json.loads(result[0].text)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_run_logs(self, mcp_project):
        import time

        await call_tool("idlergear_run_start", {"command": "echo 'hello world'", "name": "log-test"})
        time.sleep(0.5)

        result = await call_tool("idlergear_run_logs", {"name": "log-test"})

        data = json.loads(result[0].text)
        assert "hello world" in data["logs"]


class TestCallToolWatch:
    """Tests for watch-related tool calls."""

    @pytest.mark.asyncio
    async def test_watch_check(self, mcp_project):
        """Test watch check returns status."""
        result = await call_tool("idlergear_watch_check", {})

        data = json.loads(result[0].text)
        assert "files_changed" in data
        assert "lines_added" in data
        assert "suggestions" in data

    @pytest.mark.asyncio
    async def test_watch_check_with_act(self, mcp_project):
        """Test watch check with act flag."""
        result = await call_tool("idlergear_watch_check", {"act": True})

        data = json.loads(result[0].text)
        assert "status" in data
        assert "actions" in data

    @pytest.mark.asyncio
    async def test_watch_act_not_found(self, mcp_project):
        """Test watch act with unknown suggestion ID."""
        result = await call_tool("idlergear_watch_act", {"suggestion_id": "unknown"})

        data = json.loads(result[0].text)
        assert data["success"] is False
        assert "not found" in data["error"]

    @pytest.mark.asyncio
    async def test_watch_stats(self, mcp_project):
        """Test watch stats."""
        result = await call_tool("idlergear_watch_stats", {})

        data = json.loads(result[0].text)
        assert "changed_files" in data
        assert "changed_lines" in data
        assert "todos" in data
        assert "fixmes" in data
        assert "hacks" in data

    @pytest.mark.asyncio
    async def test_list_tools_includes_watch(self):
        """Test that list_tools includes watch tools."""
        tools = await list_tools()
        tool_names = [t.name for t in tools]

        assert "idlergear_watch_check" in tool_names
        assert "idlergear_watch_act" in tool_names
        assert "idlergear_watch_stats" in tool_names


class TestCallToolUnknown:
    """Tests for unknown tool calls."""

    @pytest.mark.asyncio
    async def test_unknown_tool(self, mcp_project):
        result = await call_tool("nonexistent_tool", {})

        assert "Error" in result[0].text
        assert "Unknown tool" in result[0].text
