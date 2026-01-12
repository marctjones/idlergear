"""Tests for .NET documentation generation module."""

import json
import tempfile
from pathlib import Path

import pytest

from idlergear.docs_dotnet import (
    DotNetAssembly,
    DotNetEvent,
    DotNetField,
    DotNetMethod,
    DotNetNamespace,
    DotNetParameter,
    DotNetProperty,
    DotNetType,
    check_dotnet_available,
    detect_dotnet_project,
    generate_dotnet_summary,
    generate_markdown,
    parse_xml_docs,
)


class TestDotNetParameter:
    """Tests for DotNetParameter dataclass."""

    def test_to_dict_minimal(self):
        """Test DotNetParameter.to_dict with only name."""
        param = DotNetParameter(name="arg1")
        result = param.to_dict()
        assert result == {"name": "arg1"}

    def test_to_dict_full(self):
        """Test DotNetParameter.to_dict with all fields."""
        param = DotNetParameter(
            name="arg1",
            type="string",
            description="An argument",
        )
        result = param.to_dict()
        assert result == {
            "name": "arg1",
            "type": "string",
            "description": "An argument",
        }


class TestDotNetMethod:
    """Tests for DotNetMethod dataclass."""

    def test_to_dict_minimal(self):
        """Test DotNetMethod.to_dict with minimal fields."""
        method = DotNetMethod(name="MyMethod")
        result = method.to_dict()
        assert result == {"name": "MyMethod"}

    def test_to_dict_full(self):
        """Test DotNetMethod.to_dict with all fields."""
        method = DotNetMethod(
            name="MyMethod",
            signature="(string name)",
            summary="A method.",
            parameters=[DotNetParameter(name="name", type="string")],
            return_type="bool",
            return_description="True if success",
            is_static=True,
            is_async=True,
        )
        result = method.to_dict()
        assert result["name"] == "MyMethod"
        assert result["signature"] == "(string name)"
        assert result["summary"] == "A method."
        assert result["parameters"] == [{"name": "name", "type": "string"}]
        assert result["returns"] == {"type": "bool", "description": "True if success"}
        assert result["static"] is True
        assert result["async"] is True


class TestDotNetProperty:
    """Tests for DotNetProperty dataclass."""

    def test_to_dict_minimal(self):
        """Test DotNetProperty.to_dict with minimal fields."""
        prop = DotNetProperty(name="Name")
        result = prop.to_dict()
        assert result == {"name": "Name"}

    def test_to_dict_full(self):
        """Test DotNetProperty.to_dict with all fields."""
        prop = DotNetProperty(
            name="Name",
            type="string",
            summary="The name.",
            has_getter=True,
            has_setter=False,
            is_static=True,
        )
        result = prop.to_dict()
        assert result["name"] == "Name"
        assert result["type"] == "string"
        assert result["summary"] == "The name."
        assert result["static"] is True
        assert result["setter"] is False


class TestDotNetField:
    """Tests for DotNetField dataclass."""

    def test_to_dict_minimal(self):
        """Test DotNetField.to_dict with minimal fields."""
        field = DotNetField(name="value")
        result = field.to_dict()
        assert result == {"name": "value"}

    def test_to_dict_full(self):
        """Test DotNetField.to_dict with all fields."""
        field = DotNetField(
            name="MaxValue",
            type="int",
            summary="Maximum value.",
            is_static=True,
            is_readonly=True,
            is_const=True,
        )
        result = field.to_dict()
        assert result["name"] == "MaxValue"
        assert result["type"] == "int"
        assert result["static"] is True
        assert result["readonly"] is True
        assert result["const"] is True


class TestDotNetEvent:
    """Tests for DotNetEvent dataclass."""

    def test_to_dict_minimal(self):
        """Test DotNetEvent.to_dict with minimal fields."""
        event = DotNetEvent(name="OnClick")
        result = event.to_dict()
        assert result == {"name": "OnClick"}

    def test_to_dict_full(self):
        """Test DotNetEvent.to_dict with all fields."""
        event = DotNetEvent(
            name="OnClick",
            type="EventHandler",
            summary="Fired when clicked.",
        )
        result = event.to_dict()
        assert result == {
            "name": "OnClick",
            "type": "EventHandler",
            "summary": "Fired when clicked.",
        }


class TestDotNetType:
    """Tests for DotNetType dataclass."""

    def test_to_dict_minimal(self):
        """Test DotNetType.to_dict with minimal fields."""
        dtype = DotNetType(name="MyClass")
        result = dtype.to_dict()
        assert result == {"name": "MyClass", "kind": "class"}

    def test_to_dict_with_bases(self):
        """Test DotNetType.to_dict with base classes."""
        dtype = DotNetType(
            name="MyClass",
            kind="class",
            namespace="MyApp",
            summary="A class.",
            bases=["BaseClass", "IDisposable"],
        )
        result = dtype.to_dict()
        assert result["name"] == "MyClass"
        assert result["namespace"] == "MyApp"
        assert result["summary"] == "A class."
        assert result["bases"] == ["BaseClass", "IDisposable"]

    def test_to_dict_with_members(self):
        """Test DotNetType.to_dict with methods and properties."""
        dtype = DotNetType(
            name="MyClass",
            methods=[DotNetMethod(name="DoSomething")],
            properties=[DotNetProperty(name="Value")],
            fields=[DotNetField(name="_value")],
            events=[DotNetEvent(name="OnChange")],
        )
        result = dtype.to_dict()
        assert len(result["methods"]) == 1
        assert len(result["properties"]) == 1
        assert len(result["fields"]) == 1
        assert len(result["events"]) == 1


class TestDotNetNamespace:
    """Tests for DotNetNamespace dataclass."""

    def test_to_dict_minimal(self):
        """Test DotNetNamespace.to_dict with minimal fields."""
        ns = DotNetNamespace(name="MyApp")
        result = ns.to_dict()
        assert result == {"name": "MyApp"}

    def test_to_dict_with_types(self):
        """Test DotNetNamespace.to_dict with types."""
        ns = DotNetNamespace(
            name="MyApp",
            types=[DotNetType(name="MyClass")],
            child_namespaces=["MyApp.Core", "MyApp.Util"],
        )
        result = ns.to_dict()
        assert result["name"] == "MyApp"
        assert len(result["types"]) == 1
        assert result["child_namespaces"] == ["MyApp.Core", "MyApp.Util"]


class TestDotNetAssembly:
    """Tests for DotNetAssembly dataclass."""

    def test_to_dict_minimal(self):
        """Test DotNetAssembly.to_dict with minimal fields."""
        assembly = DotNetAssembly(name="MyApp")
        result = assembly.to_dict()
        assert result == {"name": "MyApp"}

    def test_to_dict_full(self):
        """Test DotNetAssembly.to_dict with all fields."""
        assembly = DotNetAssembly(
            name="MyApp",
            version="1.0.0",
            target_framework="net8.0",
            namespaces=[DotNetNamespace(name="MyApp")],
        )
        result = assembly.to_dict()
        assert result["name"] == "MyApp"
        assert result["version"] == "1.0.0"
        assert result["target_framework"] == "net8.0"
        assert len(result["namespaces"]) == 1


class TestCheckDotnetAvailable:
    """Tests for check_dotnet_available function."""

    def test_check_dotnet_available(self):
        """Test that function returns a boolean."""
        result = check_dotnet_available()
        assert isinstance(result, bool)


class TestParseXmlDocs:
    """Tests for parse_xml_docs function."""

    def test_parse_simple_xml(self):
        """Test parsing a simple XML documentation file."""
        xml_content = """<?xml version="1.0"?>
<doc>
    <assembly>
        <name>TestAssembly</name>
    </assembly>
    <members>
        <member name="T:TestNamespace.TestClass">
            <summary>A test class.</summary>
        </member>
        <member name="M:TestNamespace.TestClass.DoSomething(System.String)">
            <summary>Does something.</summary>
            <param name="input">The input string.</param>
            <returns>The result.</returns>
        </member>
        <member name="P:TestNamespace.TestClass.Name">
            <summary>Gets or sets the name.</summary>
        </member>
    </members>
</doc>"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            f.flush()

            result = parse_xml_docs(f.name)

            assert result.name == "TestAssembly"
            assert len(result.namespaces) == 1
            ns = result.namespaces[0]
            assert ns.name == "TestNamespace"
            assert len(ns.types) == 1
            dtype = ns.types[0]
            assert dtype.name == "TestClass"
            assert dtype.summary == "A test class."

    def test_parse_interface(self):
        """Test parsing interface documentation."""
        xml_content = """<?xml version="1.0"?>
<doc>
    <assembly><name>TestAssembly</name></assembly>
    <members>
        <member name="T:TestNamespace.IService">
            <summary>A service interface.</summary>
        </member>
    </members>
</doc>"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            f.flush()

            result = parse_xml_docs(f.name)

            ns = result.namespaces[0]
            dtype = ns.types[0]
            assert dtype.name == "IService"
            assert dtype.kind == "interface"

    def test_parse_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_xml_docs("/nonexistent/path/docs.xml")


class TestDetectDotnetProject:
    """Tests for detect_dotnet_project function."""

    def test_detect_no_project(self):
        """Test detection in directory without .NET project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = detect_dotnet_project(tmpdir)
            assert result["detected"] is False

    def test_detect_csproj(self):
        """Test detection of .csproj file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csproj_path = Path(tmpdir) / "MyApp.csproj"
            csproj_path.write_text(
                """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
</Project>"""
            )

            result = detect_dotnet_project(tmpdir)
            assert result["detected"] is True
            assert result["name"] == "MyApp"
            assert result["config_file"] == "MyApp.csproj"
            assert "net8.0" in result["target_frameworks"]

    def test_detect_sln(self):
        """Test detection of .sln file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sln_path = Path(tmpdir) / "MySolution.sln"
            sln_path.write_text("Microsoft Visual Studio Solution File")

            result = detect_dotnet_project(tmpdir)
            assert result["detected"] is True
            assert result["name"] == "MySolution"
            assert result["config_file"] == "MySolution.sln"

    def test_detect_xml_docs(self):
        """Test detection of existing XML documentation files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csproj_path = Path(tmpdir) / "MyApp.csproj"
            csproj_path.write_text(
                """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
</Project>"""
            )

            # Create XML docs file
            xml_path = Path(tmpdir) / "MyApp.xml"
            xml_path.write_text(
                """<?xml version="1.0"?>
<doc>
    <assembly><name>MyApp</name></assembly>
    <members></members>
</doc>"""
            )

            result = detect_dotnet_project(tmpdir)
            assert result["detected"] is True
            assert len(result["xml_docs"]) == 1


class TestGenerateDotnetSummary:
    """Tests for generate_dotnet_summary function."""

    def test_summary_minimal(self):
        """Test generating minimal summary."""
        assembly = DotNetAssembly(
            name="TestAssembly",
            namespaces=[
                DotNetNamespace(
                    name="TestNamespace",
                    types=[
                        DotNetType(name="TestClass", summary="A test class."),
                        DotNetType(name="TestService", summary="A service."),
                    ],
                )
            ],
        )

        result = generate_dotnet_summary(assembly, mode="minimal")
        assert result["assembly"] == "TestAssembly"
        assert result["mode"] == "minimal"
        ns = result["namespaces"]["TestNamespace"]
        assert "TestClass" in ns["types"]
        assert "TestService" in ns["types"]

    def test_summary_standard(self):
        """Test generating standard summary."""
        assembly = DotNetAssembly(
            name="TestAssembly",
            namespaces=[
                DotNetNamespace(
                    name="TestNamespace",
                    types=[
                        DotNetType(
                            name="TestClass",
                            kind="class",
                            summary="A test class. With more details.",
                        ),
                    ],
                )
            ],
        )

        result = generate_dotnet_summary(assembly, mode="standard")
        assert result["mode"] == "standard"
        ns = result["namespaces"]["TestNamespace"]
        type_info = ns["types"][0]
        assert type_info["name"] == "TestClass"
        assert type_info["kind"] == "class"
        # Standard mode should truncate to first sentence
        assert "A test class." in type_info["summary"]

    def test_summary_detailed(self):
        """Test generating detailed summary."""
        assembly = DotNetAssembly(
            name="TestAssembly",
            namespaces=[
                DotNetNamespace(
                    name="TestNamespace",
                    types=[
                        DotNetType(
                            name="TestClass",
                            summary="A test class.",
                            methods=[DotNetMethod(name="DoSomething")],
                        ),
                    ],
                )
            ],
        )

        result = generate_dotnet_summary(assembly, mode="detailed")
        assert result["mode"] == "detailed"
        ns = result["namespaces"]["TestNamespace"]
        type_info = ns["types"][0]
        assert "methods" in type_info


class TestGenerateMarkdown:
    """Tests for generate_markdown function."""

    def test_generate_markdown(self):
        """Test generating markdown documentation."""
        assembly = DotNetAssembly(
            name="TestAssembly",
            version="1.0.0",
            namespaces=[
                DotNetNamespace(
                    name="TestNamespace",
                    types=[
                        DotNetType(
                            name="TestClass",
                            summary="A test class.",
                            methods=[
                                DotNetMethod(
                                    name="DoSomething",
                                    signature="()",
                                    summary="Does something.",
                                )
                            ],
                            properties=[
                                DotNetProperty(name="Name", summary="The name.")
                            ],
                        ),
                    ],
                )
            ],
        )

        result = generate_markdown(assembly)
        assert "# TestAssembly API Reference" in result
        assert "Version: 1.0.0" in result
        assert "## Namespace: TestNamespace" in result
        assert "### Class: TestClass" in result
        assert "**Methods:**" in result
        assert "`DoSomething()`" in result
        assert "**Properties:**" in result
        assert "`Name`" in result


class TestCliIntegration:
    """Tests for CLI integration."""

    def test_docs_check_dotnet(self):
        """Test idlergear docs check command includes dotnet."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "check"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "dotnet" in data

    def test_docs_check_dotnet_only(self):
        """Test idlergear docs check --lang dotnet."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "check", "--lang", "dotnet"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "dotnet" in data
        assert "python" not in data
        assert "rust" not in data

    def test_docs_detect_no_dotnet_project(self):
        """Test docs detect in non-.NET directory."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a Python project instead
            (Path(tmpdir) / "pyproject.toml").write_text("[project]\nname='test'")
            result = runner.invoke(app, ["docs", "detect", tmpdir])
            assert result.exit_code == 0
            # Should detect Python, not .NET
            data = json.loads(result.output)
            assert data.get("language") == "python" or "python" in result.output.lower()

    def test_docs_detect_dotnet_project(self):
        """Test docs detect in .NET directory."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            csproj_path = Path(tmpdir) / "MyApp.csproj"
            csproj_path.write_text(
                """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
</Project>"""
            )
            result = runner.invoke(app, ["docs", "detect", tmpdir])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["detected"] is True
            assert data.get("language") == "dotnet"
