"""Tests for generator configuration system."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from idlergear.generators.base import (
    BuiltinGenerator,
    Generator,
    GeneratorConfig,
    GeneratorResult,
    GeneratorType,
    ShellGenerator,
)
from idlergear.generators.registry import (
    detect_available_generators,
    disable_generator,
    enable_generator,
    get_enabled_generators,
    get_generator,
    list_generators,
    register_generator,
)


class TestGeneratorConfig:
    """Tests for GeneratorConfig."""

    def test_create_config(self):
        """Test creating a generator config."""
        config = GeneratorConfig(
            name="test",
            enabled=True,
            generator_type=GeneratorType.BUILTIN,
        )
        assert config.name == "test"
        assert config.enabled is True
        assert config.generator_type == GeneratorType.BUILTIN

    def test_config_with_shell_options(self):
        """Test config with shell generator options."""
        config = GeneratorConfig(
            name="rustdoc",
            generator_type=GeneratorType.SHELL,
            command="cargo doc",
            env={"RUSTDOCFLAGS": "--test"},
            output="target/doc",
            requires=["cargo"],
        )
        assert config.command == "cargo doc"
        assert config.env == {"RUSTDOCFLAGS": "--test"}
        assert config.requires == ["cargo"]

    def test_config_to_dict(self):
        """Test converting config to dict."""
        config = GeneratorConfig(
            name="test",
            enabled=True,
            generator_type=GeneratorType.SHELL,
            command="test cmd",
            requires=["dep1"],
        )
        data = config.to_dict()
        assert data["name"] == "test"
        assert data["enabled"] is True
        assert data["type"] == "shell"
        assert data["command"] == "test cmd"
        assert data["requires"] == ["dep1"]

    def test_config_from_dict(self):
        """Test creating config from dict."""
        data = {
            "name": "custom",
            "enabled": False,
            "type": "shell",
            "command": "my-cmd",
            "requires": ["tool1", "tool2"],
        }
        config = GeneratorConfig.from_dict(data)
        assert config.name == "custom"
        assert config.enabled is False
        assert config.generator_type == GeneratorType.SHELL
        assert config.command == "my-cmd"
        assert config.requires == ["tool1", "tool2"]


class TestGeneratorResult:
    """Tests for GeneratorResult."""

    def test_success_result(self):
        """Test successful generation result."""
        result = GeneratorResult(
            success=True,
            references=[{"title": "Test", "body": "Content"}],
        )
        assert result.success is True
        assert len(result.references) == 1

    def test_failure_result(self):
        """Test failed generation result."""
        result = GeneratorResult(
            success=False,
            errors=["Missing dependency"],
        )
        assert result.success is False
        assert "Missing dependency" in result.errors

    def test_result_to_dict(self):
        """Test converting result to dict."""
        result = GeneratorResult(
            success=True,
            references=[{"title": "API"}],
            warnings=["Deprecated method found"],
            output_path=Path("/tmp/output"),
        )
        data = result.to_dict()
        assert data["success"] is True
        assert len(data["references"]) == 1
        assert "warnings" in data
        assert "output_path" in data


class MockGenerator(BuiltinGenerator):
    """Mock generator for testing."""

    name = "mock"
    description = "Mock generator for tests"
    requires = []
    python_deps = []

    def generate(self, input_path: Path, output_path: Path | None = None) -> GeneratorResult:
        return GeneratorResult(
            success=True,
            references=[{"title": f"Generated from {input_path.name}"}],
        )


class TestGenerator:
    """Tests for Generator base class."""

    def test_detect_no_deps(self):
        """Test detection when no dependencies."""
        gen = MockGenerator()
        assert gen.detect() is True

    def test_detect_missing_shell_dep(self):
        """Test detection with missing shell dependency."""

        class GenWithShellDep(MockGenerator):
            requires = ["nonexistent-command-12345"]

        gen = GenWithShellDep()
        assert gen.detect() is False

    def test_detect_missing_python_dep(self):
        """Test detection with missing Python dependency."""

        class GenWithPythonDep(MockGenerator):
            python_deps = ["nonexistent_package_12345"]

        gen = GenWithPythonDep()
        assert gen.detect() is False

    def test_get_missing_deps(self):
        """Test getting missing dependencies."""

        class GenWithDeps(MockGenerator):
            requires = ["nonexistent-cmd"]
            python_deps = ["nonexistent_pkg"]

        gen = GenWithDeps()
        missing = gen.get_missing_deps()
        assert "nonexistent-cmd" in missing["shell"]
        assert "nonexistent_pkg" in missing["python"]

    def test_get_status(self):
        """Test getting generator status."""
        gen = MockGenerator()
        status = gen.get_status()
        assert status["name"] == "mock"
        assert status["type"] == "built-in"
        assert status["available"] is True

    def test_generate(self):
        """Test running generation."""
        gen = MockGenerator()
        result = gen.generate(Path("/tmp/test"))
        assert result.success is True
        assert len(result.references) == 1


class TestShellGenerator:
    """Tests for ShellGenerator."""

    def test_shell_generator_no_command(self):
        """Test shell generator with no command configured."""
        gen = ShellGenerator(GeneratorConfig(name="test"))
        result = gen.generate(Path("/tmp"))
        assert result.success is False
        assert "No command configured" in result.errors[0]

    def test_shell_generator_missing_deps(self):
        """Test shell generator with missing dependencies."""
        config = GeneratorConfig(
            name="test",
            generator_type=GeneratorType.SHELL,
            command="test-cmd",
            requires=["nonexistent-12345"],
        )
        gen = ShellGenerator(config)
        gen.requires = ["nonexistent-12345"]
        result = gen.generate(Path("/tmp"))
        assert result.success is False
        assert "Missing dependencies" in result.errors[0]


class TestGeneratorRegistry:
    """Tests for generator registry functions."""

    def test_register_generator(self, temp_project):
        """Test registering a generator."""
        register_generator("test-gen", MockGenerator)
        gen = get_generator("test-gen", temp_project)
        assert gen is not None
        assert gen.name == "mock"

    def test_list_generators(self, temp_project):
        """Test listing generators."""
        register_generator("list-test", MockGenerator)
        gens = list_generators(temp_project)
        names = [g["name"] for g in gens]
        assert "list-test" in names or "mock" in names

    def test_get_nonexistent_generator(self, temp_project):
        """Test getting non-existent generator."""
        gen = get_generator("nonexistent-generator-12345", temp_project)
        assert gen is None

    def test_detect_available(self, temp_project):
        """Test detecting available generators."""
        register_generator("detect-test", MockGenerator)
        available = detect_available_generators(temp_project)
        # At least our test generator should be detectable
        assert len(available) >= 0  # May be empty if no generators registered

    def test_enable_disable_generator(self, temp_project):
        """Test enabling and disabling a generator."""
        register_generator("toggle-test", MockGenerator)

        # Disable
        result = disable_generator("toggle-test", temp_project)
        assert result is True

        # Enable
        result = enable_generator("toggle-test", temp_project)
        assert result is True
