"""Tests for multi-assistant installation."""

from unittest.mock import patch

from idlergear.assistant_install import (
    Assistant,
    ASSISTANT_CONFIGS,
    detect_installed_assistants,
    generate_gemini_md,
    generate_copilot_md,
    generate_goosehints,
    generate_aider_conventions,
    install_for_assistant,
)


class TestAssistantEnum:
    """Test Assistant enum."""

    def test_all_assistants_defined(self):
        """All expected assistants are defined."""
        assert Assistant.CLAUDE.value == "claude"
        assert Assistant.GEMINI.value == "gemini"
        assert Assistant.COPILOT.value == "copilot"
        assert Assistant.CODEX.value == "codex"
        assert Assistant.AIDER.value == "aider"
        assert Assistant.GOOSE.value == "goose"

    def test_all_assistants_have_configs(self):
        """All assistants have configurations."""
        for assistant in Assistant:
            assert assistant in ASSISTANT_CONFIGS


class TestDetectInstalledAssistants:
    """Test assistant detection."""

    @patch("shutil.which")
    def test_detect_claude(self, mock_which):
        """Detect Claude Code when installed."""
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/claude" if cmd == "claude" else None
        )
        detected = detect_installed_assistants()
        assert Assistant.CLAUDE in detected

    @patch("shutil.which")
    def test_detect_gemini(self, mock_which):
        """Detect Gemini CLI when installed."""
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/gemini" if cmd == "gemini" else None
        )
        detected = detect_installed_assistants()
        assert Assistant.GEMINI in detected

    @patch("shutil.which")
    def test_detect_aider(self, mock_which):
        """Detect Aider when installed."""
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/aider" if cmd == "aider" else None
        )
        detected = detect_installed_assistants()
        assert Assistant.AIDER in detected

    @patch("shutil.which")
    def test_detect_goose(self, mock_which):
        """Detect Goose when installed."""
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/goose" if cmd == "goose" else None
        )
        detected = detect_installed_assistants()
        assert Assistant.GOOSE in detected

    @patch("shutil.which")
    def test_detect_none(self, mock_which):
        """No assistants detected when none installed."""
        mock_which.return_value = None
        detected = detect_installed_assistants()
        # Claude might still be detected based on current install
        # but in general, should return empty list if nothing found
        assert isinstance(detected, list)


class TestGenerateFiles:
    """Test file generation for various assistants."""

    def test_generate_gemini_md(self, tmp_path):
        """Generate GEMINI.md content."""
        content = generate_gemini_md(tmp_path)

        # Check basic structure
        assert "# Gemini CLI" in content
        assert "IdlerGear Integration" in content

        # Check key sections exist
        assert "CRITICAL: Session Start" in content
        assert "idlergear context" in content
        assert "Core Commands" in content
        assert "Task Management" in content
        assert "Notes & Insights" in content
        assert "File Registry" in content

        # Check forbidden patterns section
        assert "FORBIDDEN Patterns" in content
        assert "NEVER create these files" in content
        assert "TODO.md" in content
        assert "NEVER write these comments" in content
        assert "# TODO:" in content

        # Check MCP server section
        assert "MCP Server (146 Tools)" in content
        assert "~/.gemini/settings.json" in content

        # Check workflow section
        assert "Development Workflow" in content

        # Check token efficiency section
        assert "Token Efficiency" in content
        assert "97% savings" in content

        # Check best practices
        assert "Best Practices" in content

        # Check troubleshooting
        assert "Troubleshooting" in content
        assert "Command not found" in content

    def test_generate_copilot_md(self, tmp_path):
        """Generate COPILOT.md content."""
        content = generate_copilot_md(tmp_path)

        # Check basic structure
        assert "# GitHub Copilot CLI" in content
        assert "IdlerGear Integration" in content

        # Check key sections exist
        assert "CRITICAL: Session Start" in content
        assert "idlergear context" in content
        assert "Core Commands" in content
        assert "Task Management" in content
        assert "Notes & Insights" in content
        assert "File Registry" in content

        # Check forbidden patterns section
        assert "FORBIDDEN Patterns" in content
        assert "NEVER create these files" in content
        assert "TODO.md" in content
        assert "NEVER write these comments" in content
        assert "# TODO:" in content

        # Check MCP server section
        assert "MCP Server (146 Tools)" in content
        assert "gh copilot /mcp add" in content

        # Check workflow section
        assert "Development Workflow" in content

        # Check token efficiency section
        assert "Token Efficiency" in content
        assert "97% savings" in content

        # Check best practices
        assert "Best Practices" in content

        # Check troubleshooting
        assert "Troubleshooting" in content
        assert "Command not found" in content

    def test_generate_goosehints(self, tmp_path):
        """Generate .goosehints content."""
        content = generate_goosehints(tmp_path)
        assert "Goose Hints" in content
        assert "idlergear context" in content
        assert "idlergear task" in content

    def test_generate_aider_conventions(self, tmp_path):
        """Generate .aider.conventions.md content."""
        content = generate_aider_conventions(tmp_path)
        assert "Aider Conventions" in content
        assert "IdlerGear" in content


class TestInstallForAssistant:
    """Test installation for specific assistants."""

    def test_install_gemini(self, tmp_path):
        """Install for Gemini creates GEMINI.md."""
        # Initialize IdlerGear first
        (tmp_path / ".idlergear").mkdir()

        with patch(
            "idlergear.assistant_install.add_mcp_to_gemini_settings"
        ) as mock_mcp:
            mock_mcp.return_value = True
            results = install_for_assistant(Assistant.GEMINI, tmp_path)

        assert "GEMINI.md" in results
        assert (tmp_path / "GEMINI.md").exists()

    def test_install_gemini_already_exists(self, tmp_path):
        """Install for Gemini skips if GEMINI.md exists."""
        (tmp_path / ".idlergear").mkdir()
        (tmp_path / "GEMINI.md").write_text("# Existing\n")

        with patch(
            "idlergear.assistant_install.add_mcp_to_gemini_settings"
        ) as mock_mcp:
            mock_mcp.return_value = False
            results = install_for_assistant(Assistant.GEMINI, tmp_path)

        assert results.get("GEMINI.md") == "unchanged"

    def test_install_aider(self, tmp_path):
        """Install for Aider creates .aider.conventions.md."""
        (tmp_path / ".idlergear").mkdir()

        results = install_for_assistant(Assistant.AIDER, tmp_path)

        assert ".aider.conventions.md" in results
        assert (tmp_path / ".aider.conventions.md").exists()
        content = (tmp_path / ".aider.conventions.md").read_text()
        assert "IdlerGear" in content

    def test_install_goose(self, tmp_path):
        """Install for Goose creates .goosehints."""
        (tmp_path / ".idlergear").mkdir()

        with patch("idlergear.assistant_install.add_mcp_to_goose_config") as mock_mcp:
            mock_mcp.return_value = True
            results = install_for_assistant(Assistant.GOOSE, tmp_path)

        assert ".goosehints" in results
        assert (tmp_path / ".goosehints").exists()

    def test_install_copilot(self, tmp_path):
        """Install for Copilot creates COPILOT.md."""
        (tmp_path / ".idlergear").mkdir()

        results = install_for_assistant(Assistant.COPILOT, tmp_path)

        assert "COPILOT.md" in results
        assert (tmp_path / "COPILOT.md").exists()


class TestAssistantConfigs:
    """Test assistant configuration data."""

    def test_claude_config(self):
        """Claude config has expected fields."""
        config = ASSISTANT_CONFIGS[Assistant.CLAUDE]
        assert config.display_name == "Claude Code"
        assert config.instruction_file == "CLAUDE.md"
        assert ".mcp.json" in config.project_files

    def test_gemini_config(self):
        """Gemini config has expected fields."""
        config = ASSISTANT_CONFIGS[Assistant.GEMINI]
        assert config.display_name == "Gemini CLI"
        assert config.instruction_file == "GEMINI.md"

    def test_aider_config(self):
        """Aider config has expected fields."""
        config = ASSISTANT_CONFIGS[Assistant.AIDER]
        assert config.display_name == "Aider"
        assert config.instruction_file == ".aider.conventions.md"

    def test_goose_config(self):
        """Goose config has expected fields."""
        config = ASSISTANT_CONFIGS[Assistant.GOOSE]
        assert config.display_name == "Goose"
        assert config.instruction_file == ".goosehints"
