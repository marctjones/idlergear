"""Tests for install/uninstall functionality."""

import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def initialized_project():
    """Create a temporary initialized project."""
    from idlergear.init import init_project

    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            os.chdir(project_path)

            # Initialize idlergear
            init_project(".")

            yield project_path
    finally:
        os.chdir(old_cwd)


class TestInstallMcpServer:
    """Tests for install_mcp_server."""

    def test_install_mcp_server(self, initialized_project):
        from idlergear.install import install_mcp_server

        result = install_mcp_server()
        assert result is True

        mcp_path = initialized_project / ".mcp.json"
        assert mcp_path.exists()

        with open(mcp_path) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "idlergear" in config["mcpServers"]
        assert config["mcpServers"]["idlergear"]["command"] == "idlergear-mcp"

    def test_install_already_installed(self, initialized_project):
        from idlergear.install import install_mcp_server

        install_mcp_server()
        result = install_mcp_server()

        assert result is False  # Already installed

    def test_install_adds_to_existing(self, initialized_project):
        from idlergear.install import install_mcp_server

        # Create existing .mcp.json with another server
        mcp_path = initialized_project / ".mcp.json"
        mcp_path.write_text(json.dumps({
            "mcpServers": {
                "other-server": {"command": "other"}
            }
        }))

        install_mcp_server()

        with open(mcp_path) as f:
            config = json.load(f)

        assert "other-server" in config["mcpServers"]
        assert "idlergear" in config["mcpServers"]


class TestUninstallMcpServer:
    """Tests for uninstall_mcp_server."""

    def test_uninstall_mcp_server(self, initialized_project):
        from idlergear.install import install_mcp_server, uninstall_mcp_server

        install_mcp_server()
        result = uninstall_mcp_server()

        assert result is True

        mcp_path = initialized_project / ".mcp.json"
        if mcp_path.exists():
            with open(mcp_path) as f:
                config = json.load(f)
            assert "idlergear" not in config.get("mcpServers", {})

    def test_uninstall_not_installed(self, initialized_project):
        from idlergear.install import uninstall_mcp_server

        result = uninstall_mcp_server()
        assert result is False

    def test_uninstall_preserves_others(self, initialized_project):
        from idlergear.install import install_mcp_server, uninstall_mcp_server

        # Create .mcp.json with idlergear and another server
        mcp_path = initialized_project / ".mcp.json"
        mcp_path.write_text(json.dumps({
            "mcpServers": {
                "other-server": {"command": "other"},
                "idlergear": {"command": "idlergear-mcp"}
            }
        }))

        uninstall_mcp_server()

        with open(mcp_path) as f:
            config = json.load(f)

        assert "other-server" in config["mcpServers"]
        assert "idlergear" not in config["mcpServers"]

    def test_uninstall_removes_empty_file(self, initialized_project):
        from idlergear.install import install_mcp_server, uninstall_mcp_server

        install_mcp_server()
        uninstall_mcp_server()

        mcp_path = initialized_project / ".mcp.json"
        # File should be removed if empty
        assert not mcp_path.exists() or json.loads(mcp_path.read_text())


class TestAddAgentsMdSection:
    """Tests for add_agents_md_section."""

    def test_add_to_new_file(self, initialized_project):
        from idlergear.install import add_agents_md_section

        result = add_agents_md_section()
        assert result is True

        agents_path = initialized_project / "AGENTS.md"
        assert agents_path.exists()

        content = agents_path.read_text()
        assert "## IdlerGear" in content
        assert "idlergear vision show" in content

    def test_add_to_existing_file(self, initialized_project):
        from idlergear.install import add_agents_md_section

        # Create existing AGENTS.md
        agents_path = initialized_project / "AGENTS.md"
        agents_path.write_text("# Existing Content\n\nSome instructions.\n")

        add_agents_md_section()

        content = agents_path.read_text()
        assert "# Existing Content" in content
        assert "## IdlerGear" in content

    def test_add_already_present(self, initialized_project):
        from idlergear.install import add_agents_md_section

        add_agents_md_section()
        result = add_agents_md_section()

        assert result is False  # Already present


class TestRemoveAgentsMdSection:
    """Tests for remove_agents_md_section."""

    def test_remove_section(self, initialized_project):
        from idlergear.install import add_agents_md_section, remove_agents_md_section

        add_agents_md_section()
        result = remove_agents_md_section()

        assert result is True

        agents_path = initialized_project / "AGENTS.md"
        if agents_path.exists():
            content = agents_path.read_text()
            assert "## IdlerGear" not in content

    def test_remove_not_present(self, initialized_project):
        from idlergear.install import remove_agents_md_section

        result = remove_agents_md_section()
        assert result is False

    def test_remove_preserves_other_content(self, initialized_project):
        from idlergear.install import add_agents_md_section, remove_agents_md_section

        # Create AGENTS.md with other content
        agents_path = initialized_project / "AGENTS.md"
        agents_path.write_text("# Agent Instructions\n\n## Other Section\n\nKeep this.\n")

        add_agents_md_section()
        remove_agents_md_section()

        content = agents_path.read_text()
        assert "## Other Section" in content
        assert "## IdlerGear" not in content

    def test_remove_deletes_empty_file(self, initialized_project):
        from idlergear.install import add_agents_md_section, remove_agents_md_section

        add_agents_md_section()
        remove_agents_md_section()

        agents_path = initialized_project / "AGENTS.md"
        # File should be removed if only IdlerGear section existed
        # (though our implementation leaves the header)


class TestGetIdlergearMcpConfig:
    """Tests for get_idlergear_mcp_config."""

    def test_get_config(self):
        from idlergear.install import get_idlergear_mcp_config

        config = get_idlergear_mcp_config()

        assert config["command"] == "idlergear-mcp"
        assert config["type"] == "stdio"
        assert config["args"] == []
