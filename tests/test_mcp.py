"""
Tests for MCP server.
"""
import pytest
import tempfile
import subprocess
from pathlib import Path
from src.mcp_server import app, list_tools, call_tool
from mcp.types import TextContent


class TestMCPServer:
    """Tests for MCP server functionality."""
    
    def setup_git_repo(self, tmpdir):
        """Helper to set up a git repo."""
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
        
        # Create initial commit
        test_file = Path(tmpdir) / "README.md"
        test_file.write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmpdir, check=True, capture_output=True)
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test that all tools are properly registered."""
        tools = await list_tools()
        
        # Should have all the tools
        tool_names = [t.name for t in tools]
        
        assert "project_status" in tool_names
        assert "project_context" in tool_names
        assert "project_check" in tool_names
        assert "sync_status" in tool_names
        assert "sync_push" in tool_names
        assert "sync_pull" in tool_names
        
        # Should have at least 6 tools
        assert len(tools) >= 6
    
    @pytest.mark.asyncio
    async def test_tool_schemas(self):
        """Test that tools have proper schemas."""
        tools = await list_tools()
        
        for tool in tools:
            # Each tool should have a name and description
            assert tool.name
            assert tool.description
            
            # Should have inputSchema
            assert hasattr(tool, 'inputSchema')
            assert 'type' in tool.inputSchema
            assert tool.inputSchema['type'] == 'object'
    
    @pytest.mark.asyncio
    async def test_call_project_status(self):
        """Test calling project_status tool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            result = await call_tool("project_status", {"path": tmpdir})
            
            assert isinstance(result, list)
            assert len(result) > 0
            assert isinstance(result[0], TextContent)
            
            # Should contain project info
            text = result[0].text
            assert "Project:" in text or "Git Status" in text
    
    @pytest.mark.asyncio
    async def test_call_project_context(self):
        """Test calling project_context tool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            # Create a charter document
            (Path(tmpdir) / "VISION.md").write_text("# Vision\nTest vision")
            
            result = await call_tool("project_context", {
                "path": tmpdir,
                "format": "markdown",
                "include_docs": True,
                "include_activity": True,
                "include_structure": True
            })
            
            assert isinstance(result, list)
            assert len(result) > 0
            
            text = result[0].text
            assert "Project Context" in text or "Test vision" in text or "VISION" in text
    
    @pytest.mark.asyncio
    async def test_call_project_check(self):
        """Test calling project_check tool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            result = await call_tool("project_check", {"path": tmpdir})
            
            assert isinstance(result, list)
            assert len(result) > 0
            
            text = result[0].text
            assert "Project Health Check" in text or "check" in text.lower()
    
    @pytest.mark.asyncio
    async def test_call_sync_status(self):
        """Test calling sync_status tool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.setup_git_repo(tmpdir)
            
            result = await call_tool("sync_status", {"path": tmpdir})
            
            assert isinstance(result, list)
            assert len(result) > 0
            
            text = result[0].text
            assert "Sync Status" in text
            assert "Current branch" in text
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """Test calling unknown tool returns error."""
        result = await call_tool("nonexistent_tool", {})
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        text = result[0].text
        assert "Unknown tool" in text or "❌" in text
    
    @pytest.mark.asyncio
    async def test_call_tool_with_error(self):
        """Test tool error handling."""
        # Call with invalid path
        result = await call_tool("project_status", {"path": "/nonexistent/path/12345"})
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        text = result[0].text
        # Should contain error message
        assert "Error" in text or "❌" in text
    
    @pytest.mark.asyncio
    async def test_server_instance(self):
        """Test that server instance is created."""
        assert app is not None
        assert app.name == "idlergear"
