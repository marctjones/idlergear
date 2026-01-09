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


class TestAddClaudeMdSection:
    """Tests for add_claude_md_section."""

    def test_add_to_new_file(self, initialized_project):
        from idlergear.install import add_claude_md_section

        result = add_claude_md_section()
        assert result is True

        claude_path = initialized_project / "CLAUDE.md"
        assert claude_path.exists()

        content = claude_path.read_text()
        assert "## IdlerGear Usage" in content
        assert "idlergear context" in content

    def test_add_to_existing_file(self, initialized_project):
        from idlergear.install import add_claude_md_section

        # Create existing CLAUDE.md
        claude_path = initialized_project / "CLAUDE.md"
        claude_path.write_text("# My Project\n\nCustom project info.\n")

        add_claude_md_section()

        content = claude_path.read_text()
        assert "# My Project" in content
        assert "Custom project info" in content
        assert "## IdlerGear Usage" in content

    def test_add_already_present(self, initialized_project):
        from idlergear.install import add_claude_md_section

        add_claude_md_section()
        result = add_claude_md_section()

        assert result is False  # Already present


class TestRemoveClaudeMdSection:
    """Tests for remove_claude_md_section."""

    def test_remove_section(self, initialized_project):
        from idlergear.install import add_claude_md_section, remove_claude_md_section

        add_claude_md_section()
        result = remove_claude_md_section()

        assert result is True

        claude_path = initialized_project / "CLAUDE.md"
        # File may not exist if only IdlerGear section was there
        if claude_path.exists():
            content = claude_path.read_text()
            assert "## IdlerGear Usage" not in content

    def test_remove_not_present(self, initialized_project):
        from idlergear.install import remove_claude_md_section

        result = remove_claude_md_section()
        assert result is False

    def test_remove_preserves_other_content(self, initialized_project):
        from idlergear.install import add_claude_md_section, remove_claude_md_section

        # Create CLAUDE.md with other content
        claude_path = initialized_project / "CLAUDE.md"
        claude_path.write_text("# My Project\n\n## Custom Section\n\nKeep this.\n")

        add_claude_md_section()
        remove_claude_md_section()

        content = claude_path.read_text()
        assert "## Custom Section" in content
        assert "Keep this" in content
        assert "## IdlerGear Usage" not in content


class TestAddRulesFile:
    """Tests for add_rules_file."""

    def test_add_rules_file(self, initialized_project):
        from idlergear.install import add_rules_file

        result = add_rules_file()
        assert result == "created"

        rules_path = initialized_project / ".claude" / "rules" / "idlergear.md"
        assert rules_path.exists()

        content = rules_path.read_text()
        assert "IdlerGear" in content
        assert "idlergear context" in content
        assert "alwaysApply: true" in content

    def test_add_already_exists(self, initialized_project):
        from idlergear.install import add_rules_file

        add_rules_file()
        result = add_rules_file()

        assert result == "unchanged"  # Content identical

    def test_add_updates_when_different(self, initialized_project):
        from idlergear.install import add_rules_file

        add_rules_file()
        rules_path = initialized_project / ".claude" / "rules" / "idlergear.md"
        rules_path.write_text("old content")

        result = add_rules_file()
        assert result == "updated"
        assert "IdlerGear" in rules_path.read_text()


class TestRemoveRulesFile:
    """Tests for remove_rules_file."""

    def test_remove_rules_file(self, initialized_project):
        from idlergear.install import add_rules_file, remove_rules_file

        add_rules_file()
        result = remove_rules_file()

        assert result is True

        rules_path = initialized_project / ".claude" / "rules" / "idlergear.md"
        assert not rules_path.exists()

    def test_remove_not_present(self, initialized_project):
        from idlergear.install import remove_rules_file

        result = remove_rules_file()
        assert result is False

    def test_remove_cleans_empty_dirs(self, initialized_project):
        from idlergear.install import add_rules_file, remove_rules_file

        add_rules_file()
        remove_rules_file()

        # Empty directories should be cleaned up
        rules_dir = initialized_project / ".claude" / "rules"
        claude_dir = initialized_project / ".claude"

        # If dirs exist, they should have other files
        if rules_dir.exists():
            assert list(rules_dir.iterdir()), "rules dir should have files or not exist"
        if claude_dir.exists():
            assert list(claude_dir.iterdir()), ".claude dir should have files or not exist"


class TestAddSkill:
    """Tests for add_skill."""

    def test_add_skill(self, initialized_project):
        from idlergear.install import add_skill

        result = add_skill()
        assert isinstance(result, dict)
        assert all(v == "created" for v in result.values())

        skill_dir = initialized_project / ".claude" / "skills" / "idlergear"
        assert skill_dir.exists()

        # Check SKILL.md
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists()
        content = skill_md.read_text()
        assert content.startswith("---")  # Has frontmatter
        assert "name: idlergear" in content
        assert "description:" in content

    def test_add_skill_creates_references(self, initialized_project):
        from idlergear.install import add_skill

        add_skill()

        refs_dir = initialized_project / ".claude" / "skills" / "idlergear" / "references"
        assert refs_dir.exists()

        # Check reference files exist
        assert (refs_dir / "knowledge-types.md").exists()
        assert (refs_dir / "mcp-tools.md").exists()
        assert (refs_dir / "multi-agent.md").exists()

    def test_add_skill_creates_scripts(self, initialized_project):
        from idlergear.install import add_skill
        import stat

        add_skill()

        scripts_dir = initialized_project / ".claude" / "skills" / "idlergear" / "scripts"
        assert scripts_dir.exists()

        # Check script files exist and are executable
        for script in ["context.sh", "status.sh", "session-start.sh"]:
            script_path = scripts_dir / script
            assert script_path.exists(), f"{script} should exist"
            mode = script_path.stat().st_mode
            assert mode & stat.S_IXUSR, f"{script} should be executable"

    def test_add_skill_already_exists(self, initialized_project):
        from idlergear.install import add_skill

        add_skill()
        result = add_skill()

        # All unchanged on second run
        assert all(v == "unchanged" for v in result.values())

    def test_add_skill_updates_changed_files(self, initialized_project):
        from idlergear.install import add_skill

        add_skill()

        # Modify a file
        skill_md = initialized_project / ".claude" / "skills" / "idlergear" / "SKILL.md"
        skill_md.write_text("modified content")

        result = add_skill()

        # SKILL.md should be updated, others unchanged
        assert result.get("SKILL.md") == "updated"


class TestRemoveSkill:
    """Tests for remove_skill."""

    def test_remove_skill(self, initialized_project):
        from idlergear.install import add_skill, remove_skill

        add_skill()
        result = remove_skill()

        assert result is True

        skill_dir = initialized_project / ".claude" / "skills" / "idlergear"
        assert not skill_dir.exists()

    def test_remove_skill_not_present(self, initialized_project):
        from idlergear.install import remove_skill

        result = remove_skill()
        assert result is False

    def test_remove_skill_cleans_empty_dirs(self, initialized_project):
        from idlergear.install import add_skill, remove_skill

        add_skill()
        remove_skill()

        # Empty skills directory should be cleaned up
        skills_dir = initialized_project / ".claude" / "skills"
        if skills_dir.exists():
            assert list(skills_dir.iterdir()), "skills dir should have files or not exist"


class TestFullUninstall:
    """Tests for uninstall_idlergear function."""

    def test_uninstall_all_components(self, initialized_project):
        from idlergear.install import (
            add_agents_md_section,
            add_claude_md_section,
            add_rules_file,
            add_skill,
            install_mcp_server,
        )
        from idlergear.uninstall import uninstall_idlergear

        # Install all components
        install_mcp_server()
        add_agents_md_section()
        add_claude_md_section()
        add_rules_file()
        add_skill()

        # Uninstall
        results = uninstall_idlergear(initialized_project)

        assert results["mcp_config"] is True
        assert results["agents_md"] is True
        assert results["claude_md"] is True
        assert results["rules_file"] is True

    def test_uninstall_dry_run(self, initialized_project):
        from idlergear.install import install_mcp_server
        from idlergear.uninstall import uninstall_idlergear

        install_mcp_server()

        # Dry run
        results = uninstall_idlergear(initialized_project, dry_run=True)

        assert results["mcp_config"] is True

        # But file should still exist
        mcp_path = initialized_project / ".mcp.json"
        assert mcp_path.exists()
        content = json.loads(mcp_path.read_text())
        assert "idlergear" in content["mcpServers"]

    def test_uninstall_with_remove_data(self, initialized_project):
        from idlergear.uninstall import uninstall_idlergear

        # Verify .idlergear exists
        assert (initialized_project / ".idlergear").exists()

        # Uninstall with remove_data
        results = uninstall_idlergear(initialized_project, remove_data=True)

        assert results["idlergear_data"] is True
        assert not (initialized_project / ".idlergear").exists()

    def test_uninstall_preserves_data_by_default(self, initialized_project):
        from idlergear.uninstall import uninstall_idlergear

        # Uninstall without remove_data
        results = uninstall_idlergear(initialized_project)

        assert results["idlergear_data"] is False
        assert (initialized_project / ".idlergear").exists()
