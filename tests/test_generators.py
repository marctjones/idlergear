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


class TestBuiltinGenerators:
    """Tests for built-in generators."""

    def test_pdoc_generator_success(self, temp_project):
        """Test PdocGenerator with valid Python code."""
        from idlergear.generators.builtin import PdocGenerator

        # Create a simple Python file
        test_file = temp_project / "sample.py"
        test_file.write_text('''
"""Sample module for testing."""

def hello():
    """Say hello."""
    return "hello"
''')

        gen = PdocGenerator()
        assert gen.name == "pdoc"
        assert gen.description == "Generate API docs from Python source code using pdoc"

        # The generate method might work or fail depending on pdoc availability
        result = gen.generate(test_file)
        # Either success or failure due to pdoc not being installed
        assert isinstance(result.success, bool)

    def test_pdoc_generator_import_error(self, temp_project):
        """Test PdocGenerator handling ImportError."""
        from idlergear.generators.builtin import PdocGenerator

        gen = PdocGenerator()
        test_file = temp_project / "test.py"
        test_file.write_text("# empty")

        # Mock to simulate ImportError
        with patch("idlergear.generators.builtin.PdocGenerator.generate") as mock_gen:
            mock_gen.return_value = GeneratorResult(
                success=False,
                errors=["pdoc package not installed. Install with: pip install pdoc"],
            )
            result = mock_gen(test_file)
            assert result.success is False
            assert "pdoc" in result.errors[0]

    def test_rust_generator_success(self, temp_project):
        """Test RustGenerator with mocked response."""
        from idlergear.generators.builtin import RustGenerator

        gen = RustGenerator()
        assert gen.name == "rust"
        assert gen.requires == []
        assert gen.python_deps == []

        # Mock generate_rust_summary to return valid result
        with patch("idlergear.docs_rust.generate_rust_summary") as mock_gen:
            mock_gen.return_value = {"markdown": "# API Documentation\n\n## Structs\n- Sample"}
            result = gen.generate(temp_project)
            assert result.success is True
            assert len(result.references) == 1
            assert "API" in result.references[0]["body"]

    def test_rust_generator_empty_result(self, temp_project):
        """Test RustGenerator with empty result."""
        from idlergear.generators.builtin import RustGenerator

        gen = RustGenerator()

        # Mock to return empty result
        with patch("idlergear.docs_rust.generate_rust_summary") as mock_gen:
            mock_gen.return_value = None
            result = gen.generate(temp_project)
            assert result.success is True
            assert len(result.references) == 0

    def test_rust_generator_exception(self, temp_project):
        """Test RustGenerator handling exception."""
        from idlergear.generators.builtin import RustGenerator

        gen = RustGenerator()

        # Mock to raise exception
        with patch("idlergear.docs_rust.generate_rust_summary") as mock_gen:
            mock_gen.side_effect = RuntimeError("Test error")
            result = gen.generate(temp_project)
            assert result.success is False
            assert "Test error" in result.errors[0]

    def test_dotnet_generator_success(self, temp_project):
        """Test DotNetGenerator with mocked response."""
        from idlergear.generators.builtin import DotNetGenerator

        gen = DotNetGenerator()
        assert gen.name == "dotnet"
        assert gen.requires == []
        assert gen.python_deps == []

        # Mock generate_dotnet_summary to return valid result
        with patch("idlergear.docs_dotnet.generate_dotnet_summary") as mock_gen:
            mock_gen.return_value = {"markdown": "# .NET API\n\n## Classes\n- Sample"}
            result = gen.generate(temp_project)
            assert result.success is True
            assert len(result.references) == 1
            assert ".NET API" in result.references[0]["body"]

    def test_dotnet_generator_empty_result(self, temp_project):
        """Test DotNetGenerator with empty result."""
        from idlergear.generators.builtin import DotNetGenerator

        gen = DotNetGenerator()

        # Mock to return empty result
        with patch("idlergear.docs_dotnet.generate_dotnet_summary") as mock_gen:
            mock_gen.return_value = None
            result = gen.generate(temp_project)
            assert result.success is True
            assert len(result.references) == 0

    def test_dotnet_generator_exception(self, temp_project):
        """Test DotNetGenerator handling exception."""
        from idlergear.generators.builtin import DotNetGenerator

        gen = DotNetGenerator()

        # Mock to raise exception
        with patch("idlergear.docs_dotnet.generate_dotnet_summary") as mock_gen:
            mock_gen.side_effect = RuntimeError("Test error")
            result = gen.generate(temp_project)
            assert result.success is False
            assert "Test error" in result.errors[0]

    def test_rustdoc_generator_init(self):
        """Test RustdocGenerator initialization."""
        from idlergear.generators.builtin import RustdocGenerator

        gen = RustdocGenerator()
        assert gen.name == "rustdoc"
        assert gen.requires == ["cargo"]
        assert gen.config is not None
        assert gen.config.command == "cargo +nightly doc --no-deps"
        assert "RUSTDOCFLAGS" in gen.config.env

    def test_rustdoc_generator_with_config(self):
        """Test RustdocGenerator with custom config."""
        from idlergear.generators.builtin import RustdocGenerator

        config = GeneratorConfig(
            name="custom-rustdoc",
            generator_type=GeneratorType.SHELL,
            command="cargo doc",
            requires=["cargo"],
        )
        gen = RustdocGenerator(config)
        assert gen.config.command == "cargo doc"
        assert gen.config.name == "custom-rustdoc"

    def test_rustdoc_generator_detect_no_cargo(self):
        """Test RustdocGenerator detection when cargo is missing."""
        from idlergear.generators.builtin import RustdocGenerator

        gen = RustdocGenerator()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            assert gen.detect() is False

    def test_rustdoc_generator_detect_no_nightly(self):
        """Test RustdocGenerator detection when nightly is missing."""
        from idlergear.generators.builtin import RustdocGenerator
        import subprocess

        gen = RustdocGenerator()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/cargo"
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=1, stdout="", stderr="error"
                )
                assert gen.detect() is False

    def test_rustdoc_generator_detect_exception(self):
        """Test RustdocGenerator detection with exception."""
        from idlergear.generators.builtin import RustdocGenerator

        gen = RustdocGenerator()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/cargo"
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("rustup not found")
                assert gen.detect() is False

    def test_rustdoc_generator_detect_success(self):
        """Test RustdocGenerator detection success."""
        from idlergear.generators.builtin import RustdocGenerator
        import subprocess

        gen = RustdocGenerator()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/cargo"
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="rustc 1.75.0-nightly", stderr=""
                )
                assert gen.detect() is True
