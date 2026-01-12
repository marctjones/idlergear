"""Tests for the Rust documentation generation module."""

import json
import tempfile
from pathlib import Path

import pytest

from idlergear.docs_rust import (
    RustCrate,
    RustEnum,
    RustFunction,
    RustModule,
    RustStruct,
    RustTrait,
    check_cargo_available,
    detect_rust_project,
    parse_rust_file,
)


class TestRustFunction:
    """Tests for RustFunction dataclass."""

    def test_to_dict_minimal(self):
        """Test RustFunction.to_dict with minimal fields."""
        func = RustFunction(name="my_func")
        result = func.to_dict()
        assert result == {"name": "my_func"}

    def test_to_dict_full(self):
        """Test RustFunction.to_dict with all fields."""
        func = RustFunction(
            name="my_func",
            signature="pub fn my_func(x: i32) -> String",
            is_async=True,
            is_unsafe=True,
            parameters=[("x", "i32")],
            return_type="String",
            doc_comment="A function.",
        )
        result = func.to_dict()
        assert result["name"] == "my_func"
        assert result["signature"] == "pub fn my_func(x: i32) -> String"
        assert result["async"] is True
        assert result["unsafe"] is True
        assert result["parameters"] == [{"name": "x", "type": "i32"}]
        assert result["returns"] == "String"
        assert result["doc"] == "A function."


class TestRustStruct:
    """Tests for RustStruct dataclass."""

    def test_to_dict_minimal(self):
        """Test RustStruct.to_dict with minimal fields."""
        struct = RustStruct(name="MyStruct")
        result = struct.to_dict()
        assert result == {"name": "MyStruct"}

    def test_to_dict_with_derives(self):
        """Test RustStruct.to_dict with derives."""
        struct = RustStruct(
            name="MyStruct",
            doc_comment="A struct.",
            derives=["Debug", "Clone"],
            fields=[("field1", "String", "A field")],
        )
        result = struct.to_dict()
        assert result["name"] == "MyStruct"
        assert result["doc"] == "A struct."
        assert result["derives"] == ["Debug", "Clone"]
        assert result["fields"] == [
            {"name": "field1", "type": "String", "doc": "A field"}
        ]


class TestRustEnum:
    """Tests for RustEnum dataclass."""

    def test_to_dict_minimal(self):
        """Test RustEnum.to_dict with minimal fields."""
        enum = RustEnum(name="MyEnum")
        result = enum.to_dict()
        assert result == {"name": "MyEnum"}

    def test_to_dict_with_variants(self):
        """Test RustEnum.to_dict with variants."""
        enum = RustEnum(
            name="MyEnum",
            doc_comment="An enum.",
            variants=[("Variant1", "First variant"), ("Variant2", None)],
            derives=["Debug"],
        )
        result = enum.to_dict()
        assert result["name"] == "MyEnum"
        assert result["doc"] == "An enum."
        assert result["variants"] == [
            {"name": "Variant1", "doc": "First variant"},
            {"name": "Variant2"},
        ]
        assert result["derives"] == ["Debug"]


class TestRustTrait:
    """Tests for RustTrait dataclass."""

    def test_to_dict_minimal(self):
        """Test RustTrait.to_dict with minimal fields."""
        trait = RustTrait(name="MyTrait")
        result = trait.to_dict()
        assert result == {"name": "MyTrait"}

    def test_to_dict_with_supertraits(self):
        """Test RustTrait.to_dict with supertraits."""
        trait = RustTrait(
            name="MyTrait",
            doc_comment="A trait.",
            supertraits=["Debug", "Clone"],
            methods=[RustFunction(name="method1")],
        )
        result = trait.to_dict()
        assert result["name"] == "MyTrait"
        assert result["doc"] == "A trait."
        assert result["supertraits"] == ["Debug", "Clone"]
        assert len(result["methods"]) == 1


class TestRustModule:
    """Tests for RustModule dataclass."""

    def test_to_dict_minimal(self):
        """Test RustModule.to_dict with minimal fields."""
        mod = RustModule(name="mymodule", path="src/lib.rs")
        result = mod.to_dict()
        assert result == {"name": "mymodule", "path": "src/lib.rs"}

    def test_to_dict_full(self):
        """Test RustModule.to_dict with all fields."""
        mod = RustModule(
            name="mymodule",
            path="src/lib.rs",
            doc_comment="A module.",
            functions=[RustFunction(name="func1")],
            structs=[RustStruct(name="Struct1")],
            enums=[RustEnum(name="Enum1")],
            traits=[RustTrait(name="Trait1")],
            submodules=["sub1", "sub2"],
            constants=[("CONST1", "i32")],
        )
        result = mod.to_dict()
        assert result["name"] == "mymodule"
        assert result["doc"] == "A module."
        assert len(result["functions"]) == 1
        assert len(result["structs"]) == 1
        assert len(result["enums"]) == 1
        assert len(result["traits"]) == 1
        assert result["submodules"] == ["sub1", "sub2"]
        assert result["constants"] == [{"name": "CONST1", "type": "i32"}]


class TestRustCrate:
    """Tests for RustCrate dataclass."""

    def test_to_dict_minimal(self):
        """Test RustCrate.to_dict with minimal fields."""
        crate = RustCrate(name="mycrate")
        result = crate.to_dict()
        assert result == {"name": "mycrate"}

    def test_to_dict_full(self):
        """Test RustCrate.to_dict with all fields."""
        crate = RustCrate(
            name="mycrate",
            version="1.0.0",
            description="A crate.",
            modules=[RustModule(name="lib", path="src/lib.rs")],
        )
        result = crate.to_dict()
        assert result["name"] == "mycrate"
        assert result["version"] == "1.0.0"
        assert result["description"] == "A crate."
        assert len(result["modules"]) == 1

    def test_to_json(self):
        """Test RustCrate.to_json."""
        crate = RustCrate(name="mycrate", version="1.0.0")
        result = crate.to_json()
        data = json.loads(result)
        assert data["name"] == "mycrate"
        assert data["version"] == "1.0.0"


class TestCheckCargoAvailable:
    """Tests for check_cargo_available function."""

    def test_cargo_check(self):
        """Test that cargo availability can be checked."""
        # This should return True or False without raising
        result = check_cargo_available()
        assert isinstance(result, bool)


class TestDetectRustProject:
    """Tests for detect_rust_project function."""

    def test_detect_rust_project_not_rust(self):
        """Test detect_rust_project in non-Rust directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = detect_rust_project(tmpdir)
            assert result["detected"] is False
            assert result["language"] == "rust"

    def test_detect_rust_project_with_cargo_toml(self):
        """Test detect_rust_project with Cargo.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = Path(tmpdir) / "Cargo.toml"
            cargo_toml.write_text("""
[package]
name = "test_crate"
version = "0.1.0"
edition = "2021"
description = "A test crate"
""")
            result = detect_rust_project(tmpdir)
            assert result["detected"] is True
            assert result["name"] == "test_crate"
            assert result["version"] == "0.1.0"
            assert result["edition"] == "2021"
            assert result["description"] == "A test crate"
            assert result["config_file"] == "Cargo.toml"

    def test_detect_rust_project_workspace(self):
        """Test detect_rust_project with workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = Path(tmpdir) / "Cargo.toml"
            cargo_toml.write_text("""
[workspace]
members = ["crate1", "crate2"]
""")
            result = detect_rust_project(tmpdir)
            assert result["detected"] is True
            assert result["is_workspace"] is True
            assert result["workspace_members"] == ["crate1", "crate2"]

    def test_detect_rust_project_with_src(self):
        """Test detect_rust_project detects source directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = Path(tmpdir) / "Cargo.toml"
            cargo_toml.write_text("""
[package]
name = "test_crate"
version = "0.1.0"
""")
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "lib.rs").write_text("//! A library crate")

            result = detect_rust_project(tmpdir)
            assert result["detected"] is True
            assert result["source_dir"] == "src"
            assert result["crate_type"] == "lib"

    def test_detect_rust_project_binary(self):
        """Test detect_rust_project detects binary crate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = Path(tmpdir) / "Cargo.toml"
            cargo_toml.write_text("""
[package]
name = "test_crate"
version = "0.1.0"
""")
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "main.rs").write_text("fn main() {}")

            result = detect_rust_project(tmpdir)
            assert result["detected"] is True
            assert result["crate_type"] == "bin"


class TestParseRustFile:
    """Tests for parse_rust_file function."""

    def test_parse_empty_file(self):
        """Test parsing an empty Rust file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rs_file = Path(tmpdir) / "empty.rs"
            rs_file.write_text("")
            module = parse_rust_file(rs_file)
            assert module.name == "empty"
            assert module.functions == []
            assert module.structs == []

    def test_parse_module_doc_comment(self):
        """Test parsing module-level doc comment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rs_file = Path(tmpdir) / "lib.rs"
            rs_file.write_text("""//! This is a module.
//! It has multiple lines.

pub fn foo() {}
""")
            module = parse_rust_file(rs_file)
            assert module.doc_comment is not None
            assert "This is a module" in module.doc_comment

    def test_parse_pub_fn(self):
        """Test parsing public functions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rs_file = Path(tmpdir) / "lib.rs"
            rs_file.write_text("""
/// Adds two numbers.
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

/// An async function.
pub async fn fetch() -> String {
    String::new()
}

/// An unsafe function.
pub unsafe fn danger() {}
""")
            module = parse_rust_file(rs_file)
            assert len(module.functions) == 3

            add_fn = next(f for f in module.functions if f.name == "add")
            assert add_fn.doc_comment == "Adds two numbers."
            assert add_fn.return_type == "i32"
            assert ("a", "i32") in add_fn.parameters

            fetch_fn = next(f for f in module.functions if f.name == "fetch")
            assert fetch_fn.is_async is True

            danger_fn = next(f for f in module.functions if f.name == "danger")
            assert danger_fn.is_unsafe is True

    def test_parse_pub_struct(self):
        """Test parsing public structs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rs_file = Path(tmpdir) / "lib.rs"
            rs_file.write_text("""
/// A point in 2D space.
#[derive(Debug, Clone)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}
""")
            module = parse_rust_file(rs_file)
            assert len(module.structs) == 1
            point = module.structs[0]
            assert point.name == "Point"
            assert point.doc_comment == "A point in 2D space."
            assert "Debug" in point.derives
            assert "Clone" in point.derives

    def test_parse_pub_enum(self):
        """Test parsing public enums."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rs_file = Path(tmpdir) / "lib.rs"
            rs_file.write_text("""
/// A color.
#[derive(Debug)]
pub enum Color {
    Red,
    Green,
    Blue,
}
""")
            module = parse_rust_file(rs_file)
            assert len(module.enums) == 1
            color = module.enums[0]
            assert color.name == "Color"
            assert color.doc_comment == "A color."
            assert "Debug" in color.derives

    def test_parse_pub_trait(self):
        """Test parsing public traits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rs_file = Path(tmpdir) / "lib.rs"
            rs_file.write_text("""
/// A drawable object.
pub trait Drawable {
    fn draw(&self);
}
""")
            module = parse_rust_file(rs_file)
            assert len(module.traits) == 1
            drawable = module.traits[0]
            assert drawable.name == "Drawable"
            assert drawable.doc_comment == "A drawable object."

    def test_parse_pub_const(self):
        """Test parsing public constants."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rs_file = Path(tmpdir) / "lib.rs"
            rs_file.write_text("""
pub const MAX_SIZE: usize = 100;
pub const PI: f64 = 3.14159;
""")
            module = parse_rust_file(rs_file)
            assert len(module.constants) == 2
            assert ("MAX_SIZE", "usize") in module.constants
            assert ("PI", "f64") in module.constants

    def test_parse_pub_mod(self):
        """Test parsing public modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rs_file = Path(tmpdir) / "lib.rs"
            rs_file.write_text("""
pub mod utils;
pub mod config;
""")
            module = parse_rust_file(rs_file)
            assert "utils" in module.submodules
            assert "config" in module.submodules


class TestRustSummary:
    """Tests for Rust summary generation."""

    def test_generate_summary_minimal(self):
        """Test generate_rust_summary with minimal mode."""
        from idlergear.docs_rust import generate_rust_summary

        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = Path(tmpdir) / "Cargo.toml"
            cargo_toml.write_text("""
[package]
name = "test_crate"
version = "0.1.0"
""")
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "lib.rs").write_text("""
pub fn hello() {}
pub struct World {}
""")
            summary = generate_rust_summary(tmpdir, mode="minimal")
            assert summary["crate"] == "test_crate"
            assert summary["language"] == "rust"
            assert summary["mode"] == "minimal"
            assert "modules" in summary

    def test_generate_summary_standard(self):
        """Test generate_rust_summary with standard mode."""
        from idlergear.docs_rust import generate_rust_summary

        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = Path(tmpdir) / "Cargo.toml"
            cargo_toml.write_text("""
[package]
name = "test_crate"
version = "0.1.0"
description = "A test crate"
""")
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "lib.rs").write_text("""
/// Says hello.
pub fn hello() {}
""")
            summary = generate_rust_summary(tmpdir, mode="standard")
            assert summary["crate"] == "test_crate"
            assert summary["mode"] == "standard"
            assert summary.get("description") == "A test crate"

    def test_generate_summary_json(self):
        """Test generate_rust_summary_json output."""
        from idlergear.docs_rust import generate_rust_summary_json

        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = Path(tmpdir) / "Cargo.toml"
            cargo_toml.write_text("""
[package]
name = "test_crate"
version = "0.1.0"
""")
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "lib.rs").write_text("pub fn hello() {}")

            result = generate_rust_summary_json(tmpdir, mode="minimal")
            data = json.loads(result)
            assert data["crate"] == "test_crate"
            assert data["language"] == "rust"


class TestCliIntegration:
    """Tests for CLI integration with Rust docs."""

    def test_docs_check_includes_rust(self):
        """Test idlergear docs check includes Rust status."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "check"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # Should have both python and rust
        assert "python" in data
        assert "rust" in data
        assert "available" in data["python"]
        assert "available" in data["rust"]

    def test_docs_check_rust_only(self):
        """Test idlergear docs check --lang rust."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "check", "--lang", "rust"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "rust" in data
        assert "python" not in data

    def test_docs_detect_python_project(self):
        """Test docs detect detects Python project."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "detect"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # Running in idlergear repo, should detect Python
        assert data["detected"] is True
        assert data.get("language") == "python" or data.get("name") == "idlergear"

    def test_docs_detect_rust_project(self):
        """Test docs detect detects Rust project."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = Path(tmpdir) / "Cargo.toml"
            cargo_toml.write_text("""
[package]
name = "test_crate"
version = "0.1.0"
edition = "2021"
""")
            result = runner.invoke(app, ["docs", "detect", tmpdir])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["detected"] is True
            assert data["language"] == "rust"
            assert data["name"] == "test_crate"

    def test_docs_summary_rust(self):
        """Test docs summary for Rust project."""
        from typer.testing import CliRunner

        from idlergear.cli import app

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = Path(tmpdir) / "Cargo.toml"
            cargo_toml.write_text("""
[package]
name = "test_crate"
version = "0.1.0"
""")
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            (src_dir / "lib.rs").write_text("pub fn hello() {}")

            result = runner.invoke(
                app, ["docs", "summary", tmpdir, "--lang", "rust", "--mode", "minimal"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["crate"] == "test_crate"
            assert data["language"] == "rust"
            assert data["mode"] == "minimal"
