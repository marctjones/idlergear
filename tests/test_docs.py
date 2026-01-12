"""Tests for the documentation generation module."""

import json

import pytest

from idlergear.docs import (
    ClassDoc,
    FunctionDoc,
    ModuleDoc,
    ParameterDoc,
    check_pdoc_available,
    generate_docs_json,
    generate_docs_markdown,
    generate_module_docs,
    generate_package_docs,
)


class TestParameterDoc:
    """Tests for ParameterDoc dataclass."""

    def test_to_dict_minimal(self):
        """Test ParameterDoc.to_dict with only name."""
        param = ParameterDoc(name="arg1")
        result = param.to_dict()
        assert result == {"name": "arg1"}

    def test_to_dict_full(self):
        """Test ParameterDoc.to_dict with all fields."""
        param = ParameterDoc(
            name="arg1",
            annotation="str",
            default="'default'",
            description="An argument",
        )
        result = param.to_dict()
        assert result == {
            "name": "arg1",
            "type": "str",
            "default": "'default'",
            "description": "An argument",
        }


class TestFunctionDoc:
    """Tests for FunctionDoc dataclass."""

    def test_to_dict_minimal(self):
        """Test FunctionDoc.to_dict with minimal fields."""
        func = FunctionDoc(name="my_func", signature="()")
        result = func.to_dict()
        assert result == {"name": "my_func", "signature": "()"}

    def test_to_dict_full(self):
        """Test FunctionDoc.to_dict with all fields."""
        func = FunctionDoc(
            name="my_func",
            signature="(x: int) -> str",
            docstring="A function.",
            parameters=[ParameterDoc(name="x", annotation="int")],
            return_type="str",
            return_description="The result",
            is_async=True,
            decorators=["@staticmethod"],
        )
        result = func.to_dict()
        assert result["name"] == "my_func"
        assert result["signature"] == "(x: int) -> str"
        assert result["docstring"] == "A function."
        assert result["parameters"] == [{"name": "x", "type": "int"}]
        assert result["returns"] == {"type": "str", "description": "The result"}
        assert result["async"] is True
        assert result["decorators"] == ["@staticmethod"]


class TestClassDoc:
    """Tests for ClassDoc dataclass."""

    def test_to_dict_minimal(self):
        """Test ClassDoc.to_dict with minimal fields."""
        cls = ClassDoc(name="MyClass")
        result = cls.to_dict()
        assert result == {"name": "MyClass"}

    def test_to_dict_with_bases(self):
        """Test ClassDoc.to_dict with base classes."""
        cls = ClassDoc(
            name="MyClass",
            docstring="A class.",
            bases=["BaseClass", "Mixin"],
        )
        result = cls.to_dict()
        assert result["name"] == "MyClass"
        assert result["docstring"] == "A class."
        assert result["bases"] == ["BaseClass", "Mixin"]


class TestModuleDoc:
    """Tests for ModuleDoc dataclass."""

    def test_to_dict_minimal(self):
        """Test ModuleDoc.to_dict with minimal fields."""
        mod = ModuleDoc(name="mymodule")
        result = mod.to_dict()
        assert result == {"name": "mymodule"}

    def test_to_dict_full(self):
        """Test ModuleDoc.to_dict with all fields."""
        mod = ModuleDoc(
            name="mymodule",
            docstring="A module.",
            functions=[FunctionDoc(name="func1", signature="()")],
            classes=[ClassDoc(name="Class1")],
            submodules=["sub1", "sub2"],
            variables=[("VAR1", "int"), ("VAR2", None)],
        )
        result = mod.to_dict()
        assert result["name"] == "mymodule"
        assert result["docstring"] == "A module."
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "func1"
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Class1"
        assert result["submodules"] == ["sub1", "sub2"]
        assert result["variables"] == [
            {"name": "VAR1", "type": "int"},
            {"name": "VAR2"},
        ]

    def test_to_json(self):
        """Test ModuleDoc.to_json."""
        mod = ModuleDoc(name="mymodule", docstring="A module.")
        result = mod.to_json()
        data = json.loads(result)
        assert data["name"] == "mymodule"
        assert data["docstring"] == "A module."


class TestCheckPdocAvailable:
    """Tests for check_pdoc_available function."""

    def test_pdoc_available(self):
        """Test that pdoc is detected when installed."""
        # pdoc is installed as a dev dependency
        assert check_pdoc_available() is True


class TestGenerateModuleDocs:
    """Tests for generate_module_docs function."""

    def test_generate_docs_for_json(self):
        """Test generating docs for the json module."""
        doc = generate_module_docs("json")
        assert doc.name == "json"
        assert doc.docstring is not None
        assert "JSON" in doc.docstring
        # Check that standard functions are documented
        func_names = [f.name for f in doc.functions]
        assert "dumps" in func_names
        assert "loads" in func_names
        assert "dump" in func_names
        assert "load" in func_names

    def test_generate_docs_for_idlergear_tasks(self):
        """Test generating docs for idlergear.tasks."""
        doc = generate_module_docs("idlergear.tasks")
        assert doc.name == "idlergear.tasks"
        func_names = [f.name for f in doc.functions]
        assert "create_task" in func_names
        assert "list_tasks" in func_names

    def test_function_has_parameters(self):
        """Test that function parameters are extracted."""
        doc = generate_module_docs("json")
        dumps_func = next(f for f in doc.functions if f.name == "dumps")
        param_names = [p.name for p in dumps_func.parameters]
        assert "obj" in param_names

    def test_module_not_found(self):
        """Test that RuntimeError is raised for invalid module."""
        # pdoc wraps ModuleNotFoundError in RuntimeError
        with pytest.raises(RuntimeError):
            generate_module_docs("nonexistent_module_12345")


class TestGeneratePackageDocs:
    """Tests for generate_package_docs function."""

    def test_generate_package_docs_json(self):
        """Test generating docs for json package."""
        docs = generate_package_docs("json", max_depth=0)
        assert "json" in docs
        assert docs["json"].name == "json"

    def test_generate_package_docs_with_submodules(self):
        """Test generating docs for a package with submodules."""
        # Use idlergear since we know it has submodules
        docs = generate_package_docs("idlergear", max_depth=1)
        assert "idlergear" in docs
        # Should have at least some submodules
        assert len(docs) >= 1

    def test_max_depth_limits_recursion(self):
        """Test that max_depth limits submodule depth."""
        docs_depth_0 = generate_package_docs("idlergear", max_depth=0)
        docs_depth_1 = generate_package_docs("idlergear", max_depth=1)
        # depth 1 should have more modules than depth 0
        assert len(docs_depth_1) >= len(docs_depth_0)


class TestGenerateDocsJson:
    """Tests for generate_docs_json function."""

    def test_generate_json_output(self):
        """Test that output is valid JSON."""
        result = generate_docs_json("json", max_depth=0)
        data = json.loads(result)
        assert "package" in data
        assert data["package"] == "json"
        assert "modules" in data
        assert "json" in data["modules"]

    def test_generate_json_with_indent(self):
        """Test JSON output respects indent parameter."""
        result = generate_docs_json("json", max_depth=0, indent=4)
        # Indented JSON should have newlines
        assert "\n" in result


class TestGenerateDocsMarkdown:
    """Tests for generate_docs_markdown function."""

    def test_generate_markdown_output(self):
        """Test that output is valid markdown."""
        result = generate_docs_markdown("json", max_depth=0)
        # Should start with package header
        assert result.startswith("# json API Reference")
        # Should have module section
        assert "## json" in result

    def test_markdown_includes_functions(self):
        """Test that markdown includes function documentation."""
        result = generate_docs_markdown("json", max_depth=0)
        assert "**Functions:**" in result
        assert "`dumps" in result
        assert "`loads" in result


class TestCliIntegration:
    """Tests for CLI integration."""

    def test_docs_check_command(self):
        """Test idlergear docs check command."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "check"])
        assert result.exit_code == 0
        # JSON output by default
        data = json.loads(result.output)
        assert data["available"] is True

    def test_docs_module_command(self):
        """Test idlergear docs module command."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "module", "json"])
        assert result.exit_code == 0
        # JSON output by default
        data = json.loads(result.output)
        assert data["name"] == "json"

    def test_docs_generate_command(self):
        """Test idlergear docs generate command."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "generate", "json", "--depth", "0"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["package"] == "json"

    def test_docs_generate_markdown(self):
        """Test idlergear docs generate with markdown format."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app, ["docs", "generate", "json", "--format", "markdown", "--depth", "0"]
        )
        assert result.exit_code == 0
        assert "# json API Reference" in result.output

    def test_docs_module_not_found(self):
        """Test docs module command with invalid module."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "module", "nonexistent_12345"])
        assert result.exit_code == 1
