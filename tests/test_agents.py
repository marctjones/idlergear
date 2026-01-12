"""Tests for AGENTS.md generation and management."""

from idlergear.agents import (
    Language,
    TEMPLATES,
    detect_language,
    generate_agents_md,
    generate_claude_md,
    validate_agents_md,
    update_agents_md,
)


class TestLanguageDetection:
    """Test language detection from project files."""

    def test_detect_python_pyproject(self, tmp_path):
        """Detect Python from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
        assert detect_language(tmp_path) == Language.PYTHON

    def test_detect_python_requirements(self, tmp_path):
        """Detect Python from requirements.txt."""
        (tmp_path / "requirements.txt").write_text("requests>=2.0")
        assert detect_language(tmp_path) == Language.PYTHON

    def test_detect_rust(self, tmp_path):
        """Detect Rust from Cargo.toml."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")
        assert detect_language(tmp_path) == Language.RUST

    def test_detect_javascript_package(self, tmp_path):
        """Detect JavaScript from package.json."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        assert detect_language(tmp_path) == Language.JAVASCRIPT

    def test_detect_go(self, tmp_path):
        """Detect Go from go.mod."""
        (tmp_path / "go.mod").write_text("module example.com/test")
        assert detect_language(tmp_path) == Language.GO

    def test_detect_java_maven(self, tmp_path):
        """Detect Java from pom.xml."""
        (tmp_path / "pom.xml").write_text("<project></project>")
        assert detect_language(tmp_path) == Language.JAVA

    def test_detect_java_gradle(self, tmp_path):
        """Detect Java from build.gradle."""
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")
        assert detect_language(tmp_path) == Language.JAVA

    def test_detect_unknown(self, tmp_path):
        """Return UNKNOWN when no language detected."""
        assert detect_language(tmp_path) == Language.UNKNOWN

    def test_detect_by_file_extension(self, tmp_path):
        """Detect language by source file extension as fallback."""
        (tmp_path / "main.py").write_text("print('hello')")
        assert detect_language(tmp_path) == Language.PYTHON

    def test_detect_ignores_venv(self, tmp_path):
        """Don't count files in venv directory."""
        venv = tmp_path / "venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "module.py").write_text("# venv file")
        # Empty project should be UNKNOWN
        assert detect_language(tmp_path) == Language.UNKNOWN


class TestTemplates:
    """Test language templates exist and are valid."""

    def test_all_languages_have_templates(self):
        """All non-UNKNOWN languages have templates."""
        for lang in Language:
            if lang != Language.UNKNOWN:
                assert lang in TEMPLATES

    def test_templates_have_required_fields(self):
        """All templates have required fields."""
        for lang, template in TEMPLATES.items():
            assert template.language == lang
            assert len(template.commands) > 0
            assert len(template.style) > 0
            assert "always" in template.boundaries
            assert "ask_first" in template.boundaries
            assert "never" in template.boundaries

    def test_python_template_commands(self):
        """Python template has expected commands."""
        template = TEMPLATES[Language.PYTHON]
        assert "test" in template.commands
        assert "lint" in template.commands
        assert "format" in template.commands

    def test_rust_template_commands(self):
        """Rust template has expected commands."""
        template = TEMPLATES[Language.RUST]
        assert "build" in template.commands
        assert "test" in template.commands
        assert "lint" in template.commands


class TestAgentsMdGeneration:
    """Test AGENTS.md content generation."""

    def test_generate_has_commands_section(self):
        """Generated content has Commands section."""
        template = TEMPLATES[Language.PYTHON]
        content = generate_agents_md(template, include_idlergear=False)
        assert "## Commands" in content
        assert "pytest" in content

    def test_generate_has_style_section(self):
        """Generated content has Code Style section."""
        template = TEMPLATES[Language.PYTHON]
        content = generate_agents_md(template, include_idlergear=False)
        assert "## Code Style" in content
        assert "PEP 8" in content

    def test_generate_has_boundaries_section(self):
        """Generated content has Boundaries section."""
        template = TEMPLATES[Language.PYTHON]
        content = generate_agents_md(template, include_idlergear=False)
        assert "## Boundaries" in content
        assert "✅ Always" in content
        assert "⚠️ Ask First" in content
        assert "🚫 Never" in content

    def test_generate_with_idlergear(self):
        """Generated content includes IdlerGear section."""
        template = TEMPLATES[Language.PYTHON]
        content = generate_agents_md(template, include_idlergear=True)
        assert "## IdlerGear" in content
        assert "idlergear context" in content

    def test_generate_without_idlergear(self):
        """Generated content excludes IdlerGear section when disabled."""
        template = TEMPLATES[Language.PYTHON]
        content = generate_agents_md(template, include_idlergear=False)
        assert "## IdlerGear" not in content


class TestClaudeMdGeneration:
    """Test CLAUDE.md content generation."""

    def test_generate_shorter_than_agents(self):
        """CLAUDE.md is shorter than AGENTS.md."""
        template = TEMPLATES[Language.PYTHON]
        agents = generate_agents_md(template, include_idlergear=True)
        claude = generate_claude_md(template, include_idlergear=True)
        assert len(claude) < len(agents)

    def test_generate_has_quick_commands(self):
        """CLAUDE.md has Quick Commands section."""
        template = TEMPLATES[Language.PYTHON]
        content = generate_claude_md(template, include_idlergear=False)
        assert "## Quick Commands" in content


class TestValidation:
    """Test AGENTS.md validation."""

    def test_valid_content_no_issues(self):
        """Valid content returns no issues."""
        content = """# AGENTS.md

## Commands

```bash
pytest
```

## Code Style

- Follow conventions
"""
        issues = validate_agents_md(content)
        assert len(issues) == 0

    def test_missing_commands_section(self):
        """Missing Commands section flagged."""
        content = "# AGENTS.md\n\n## Code Style\n- stuff"
        issues = validate_agents_md(content)
        assert any("Commands" in issue for issue in issues)

    def test_missing_style_section(self):
        """Missing Code Style section flagged."""
        content = "# AGENTS.md\n\n## Commands\n```bash\ntest\n```"
        issues = validate_agents_md(content)
        assert any("Style" in issue for issue in issues)

    def test_contains_todo_flagged(self):
        """TODO in content is flagged."""
        content = "## Commands\n\n## Code Style\n\nTODO: add more"
        issues = validate_agents_md(content)
        assert any("TODO" in issue for issue in issues)

    def test_empty_code_block_flagged(self):
        """Empty code blocks are flagged."""
        content = "## Commands\n\n```\n```\n\n## Code Style"
        issues = validate_agents_md(content)
        assert any("empty" in issue.lower() for issue in issues)


class TestUpdate:
    """Test AGENTS.md update with preservation."""

    def test_update_preserves_custom_sections(self):
        """Custom sections are preserved during update."""
        existing = """# AGENTS.md

## Commands

```bash
old-command
```

## My Custom Section

This should be preserved.

## Code Style

- old style
"""
        template = TEMPLATES[Language.PYTHON]
        updated = update_agents_md(existing, template, preserve_custom=True)

        # Custom section should be preserved
        assert "## My Custom Section" in updated
        assert "This should be preserved" in updated

        # Template sections should be updated
        assert "pytest" in updated  # New command from template

    def test_update_no_preserve_replaces_all(self):
        """Without preserve, all content is replaced."""
        existing = """# AGENTS.md

## Commands

```bash
old-command
```

## My Custom Section

This should NOT be preserved.
"""
        template = TEMPLATES[Language.PYTHON]
        updated = update_agents_md(existing, template, preserve_custom=False)

        # Custom section should NOT be preserved
        assert "## My Custom Section" not in updated
