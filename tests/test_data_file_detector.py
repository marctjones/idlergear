"""Tests for data file reference detection."""

import ast
import tempfile
from pathlib import Path

import pytest

from idlergear.data_file_detector import (
    detect_stale_data_references,
    extract_file_references,
    group_references_by_file,
    resolve_file_reference,
)
from idlergear.git_version_detector import detect_versioned_files


def test_extract_open_call():
    """Test extraction of file paths from open() calls."""
    code = """
with open("data/old_dataset.csv") as f:
    data = f.read()
"""
    tree = ast.parse(code)
    refs = extract_file_references(tree, "script.py")

    assert len(refs) == 1
    assert refs[0]["path"] == "data/old_dataset.csv"
    assert refs[0]["line"] == 2
    assert refs[0]["function"] == "open"


def test_extract_pandas_read():
    """Test extraction from pandas read functions."""
    code = """
import pandas as pd

df = pd.read_csv("datasets/old_data.csv")
df2 = pd.read_json("output_v1.json")
"""
    tree = ast.parse(code)
    refs = extract_file_references(tree, "analysis.py")

    assert len(refs) == 2
    assert refs[0]["path"] == "datasets/old_data.csv"
    assert refs[0]["function"] == "read_csv"
    assert refs[1]["path"] == "output_v1.json"
    assert refs[1]["function"] == "read_json"


def test_extract_keyword_args():
    """Test extraction from keyword arguments."""
    code = """
df = pd.read_csv(filepath_or_buffer="data/old.csv")
"""
    tree = ast.parse(code)
    refs = extract_file_references(tree, "script.py")

    assert len(refs) == 1
    assert refs[0]["path"] == "data/old.csv"
    assert refs[0]["keyword"] == "filepath_or_buffer"


def test_extract_path_constructor():
    """Test extraction from Path() constructor."""
    code = """
from pathlib import Path

data_file = Path("data/dataset_old.csv")
"""
    tree = ast.parse(code)
    refs = extract_file_references(tree, "script.py")

    assert len(refs) == 1
    assert refs[0]["path"] == "data/dataset_old.csv"
    assert refs[0]["function"] == "Path"


def test_extract_yaml_json():
    """Test extraction of YAML and JSON files."""
    code = """
import yaml
import json

config = yaml.load(open("config_old.yaml"))
data = json.load(open("data_v1.json"))
"""
    tree = ast.parse(code)
    refs = extract_file_references(tree, "script.py")

    assert len(refs) >= 2
    paths = [r["path"] for r in refs]
    assert "config_old.yaml" in paths
    assert "data_v1.json" in paths


def test_ignore_urls():
    """Test that URLs are not treated as file paths."""
    code = """
import requests

response = requests.get("https://example.com/data.csv")
"""
    tree = ast.parse(code)
    refs = extract_file_references(tree, "script.py")

    # Should not extract the URL
    assert len(refs) == 0


def test_ignore_non_file_strings():
    """Test that regular strings are not extracted."""
    code = """
message = "Hello, world!"
name = "test"
"""
    tree = ast.parse(code)
    refs = extract_file_references(tree, "script.py")

    assert len(refs) == 0


def test_resolve_relative_to_repo():
    """Test resolving file path relative to repo root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create file
        (repo_path / "data.csv").write_text("col1,col2\n1,2")

        # Resolve reference
        resolved = resolve_file_reference("data.csv", "script.py", repo_path)

        assert resolved == "data.csv"


def test_resolve_relative_to_source():
    """Test resolving file path relative to source file directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create directory structure
        scripts_dir = repo_path / "scripts"
        scripts_dir.mkdir()
        data_dir = scripts_dir / "data"
        data_dir.mkdir()

        (data_dir / "input.csv").write_text("col1\n1")

        # Resolve from scripts/main.py looking for data/input.csv
        resolved = resolve_file_reference("data/input.csv", "scripts/main.py", repo_path)

        assert resolved == "scripts/data/input.csv"


def test_resolve_with_dot_slash():
    """Test resolving paths with ./ prefix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        (repo_path / "data.csv").write_text("col1\n1")

        resolved = resolve_file_reference("./data.csv", "script.py", repo_path)

        assert resolved == "data.csv"


def test_resolve_not_found():
    """Test that non-existent files return None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        resolved = resolve_file_reference("nonexistent.csv", "script.py", repo_path)

        assert resolved is None


def test_group_references():
    """Test grouping references by file."""
    refs = [
        {"path": "data.csv", "line": 10, "source_file": "a.py"},
        {"path": "data.csv", "line": 20, "source_file": "b.py"},
        {"path": "other.json", "line": 5, "source_file": "c.py"},
    ]

    grouped = group_references_by_file(refs)

    assert len(grouped) == 2
    assert len(grouped["data.csv"]) == 2
    assert len(grouped["other.json"]) == 1


def test_detect_stale_references():
    """Test detection of stale data file references."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create versioned data files
        (repo_path / "data.csv").write_text("col1\n1")
        (repo_path / "data_old.csv").write_text("col1\n1")

        # Create Python script that references old version
        script_content = """
import pandas as pd

df = pd.read_csv("data_old.csv")
"""
        (repo_path / "script.py").write_text(script_content)

        # Extract references
        tree = ast.parse(script_content)
        refs = extract_file_references(tree, "script.py")

        # Detect versioned files
        from idlergear.git_version_detector import VersionedFile

        versioned_files = {
            "data.csv": [
                VersionedFile(
                    path="data.csv",
                    base_name="data.csv",
                    version_suffix="",
                    is_current=True,
                ),
                VersionedFile(
                    path="data_old.csv",
                    base_name="data.csv",
                    version_suffix="_old",
                    is_current=False,
                ),
            ]
        }

        # Detect stale references
        warnings = detect_stale_data_references(refs, versioned_files, repo_path)

        assert len(warnings) == 1
        assert warnings[0]["source_file"] == "script.py"
        assert warnings[0]["stale_file"] == "data_old.csv"
        assert warnings[0]["current_file"] == "data.csv"
        assert warnings[0]["line"] == 4


def test_detect_multiple_stale_references():
    """Test detection of multiple stale references in one file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create versioned files
        (repo_path / "input.csv").write_text("col1\n1")
        (repo_path / "input_old.csv").write_text("col1\n1")
        (repo_path / "config.json").write_text("{}")
        (repo_path / "config_v1.json").write_text("{}")

        # Create script with multiple stale references
        script_content = """
import pandas as pd
import json

df = pd.read_csv("input_old.csv")
with open("config_v1.json") as f:
    config = json.load(f)
"""
        (repo_path / "script.py").write_text(script_content)

        tree = ast.parse(script_content)
        refs = extract_file_references(tree, "script.py")

        from idlergear.git_version_detector import VersionedFile

        versioned_files = {
            "input.csv": [
                VersionedFile("input.csv", "input.csv", "", True),
                VersionedFile("input_old.csv", "input.csv", "_old", False),
            ],
            "config.json": [
                VersionedFile("config.json", "config.json", "", True),
                VersionedFile("config_v1.json", "config.json", "_v1", False),
            ],
        }

        warnings = detect_stale_data_references(refs, versioned_files, repo_path)

        assert len(warnings) == 2
        stale_files = {w["stale_file"] for w in warnings}
        assert "input_old.csv" in stale_files
        assert "config_v1.json" in stale_files


def test_no_warnings_for_current_files():
    """Test that current versions don't generate warnings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create versioned files
        (repo_path / "data.csv").write_text("col1\n1")
        (repo_path / "data_old.csv").write_text("col1\n1")

        # Script uses CURRENT version
        script_content = """
import pandas as pd

df = pd.read_csv("data.csv")
"""
        (repo_path / "script.py").write_text(script_content)

        tree = ast.parse(script_content)
        refs = extract_file_references(tree, "script.py")

        from idlergear.git_version_detector import VersionedFile

        versioned_files = {
            "data.csv": [
                VersionedFile("data.csv", "data.csv", "", True),
                VersionedFile("data_old.csv", "data.csv", "_old", False),
            ]
        }

        warnings = detect_stale_data_references(refs, versioned_files, repo_path)

        assert len(warnings) == 0
