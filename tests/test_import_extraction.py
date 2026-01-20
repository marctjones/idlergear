"""Tests for AST import extraction."""

import ast
import tempfile
from pathlib import Path

import pytest

from idlergear.graph import get_database
from idlergear.graph.populators.code_populator import CodePopulator


def test_extract_simple_import():
    """Test extraction of simple import statements."""
    code = """
import os
import sys
"""
    tree = ast.parse(code)
    populator = CodePopulator(get_database())
    symbols, imports = populator._extract_symbols_and_imports(tree, "test.py")

    assert len(imports) == 2
    assert imports[0]["module"] == "os"
    assert imports[0]["type"] == "import"
    assert imports[1]["module"] == "sys"


def test_extract_from_import():
    """Test extraction of from...import statements."""
    code = """
from api_old import get_user, post_data
from utils import helper
"""
    tree = ast.parse(code)
    populator = CodePopulator(get_database())
    symbols, imports = populator._extract_symbols_and_imports(tree, "test.py")

    assert len(imports) == 2
    assert imports[0]["module"] == "api_old"
    assert imports[0]["names"] == ["get_user", "post_data"]
    assert imports[0]["type"] == "from_import"
    assert imports[1]["module"] == "utils"
    assert imports[1]["names"] == ["helper"]


def test_extract_relative_import():
    """Test extraction of relative imports."""
    code = """
from . import sibling
from ..parent import util
"""
    tree = ast.parse(code)
    populator = CodePopulator(get_database())
    symbols, imports = populator._extract_symbols_and_imports(tree, "src/module/test.py")

    assert len(imports) == 2
    assert imports[0]["level"] == 1  # Single dot
    assert imports[1]["level"] == 2  # Double dot


def test_extract_mixed():
    """Test extraction of mixed code with imports and symbols."""
    code = """
import os
from api import get_user

def process_data():
    pass

class Handler:
    def handle(self):
        pass
"""
    tree = ast.parse(code)
    populator = CodePopulator(get_database())
    symbols, imports = populator._extract_symbols_and_imports(tree, "test.py")

    assert len(imports) == 2
    assert len(symbols) == 3  # function, class, method


def test_resolve_import_path_simple():
    """Test resolving simple import paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create files
        (repo_path / "api.py").write_text("# API")
        (repo_path / "api_old.py").write_text("# Old API")
        (repo_path / "service.py").write_text("from api_old import get_user")

        populator = CodePopulator(get_database(), repo_path=repo_path)

        # Resolve import from service.py
        resolved = populator._resolve_import_path("api_old", "service.py")

        assert resolved == "api_old.py"


def test_resolve_import_path_dotted():
    """Test resolving dotted import paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create package structure
        utils_dir = repo_path / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text("")
        (utils_dir / "helper.py").write_text("# Helper")

        populator = CodePopulator(get_database(), repo_path=repo_path)

        # Resolve dotted import
        resolved = populator._resolve_import_path("utils.helper", "main.py")

        assert resolved == "utils/helper.py"


def test_resolve_import_path_same_directory():
    """Test resolving imports from same directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create directory structure
        src_dir = repo_path / "src"
        src_dir.mkdir()
        (src_dir / "api.py").write_text("# API")
        (src_dir / "api_old.py").write_text("# Old API")
        (src_dir / "service.py").write_text("from api_old import get_user")

        populator = CodePopulator(get_database(), repo_path=repo_path)

        # Resolve import from service.py
        resolved = populator._resolve_import_path("api_old", "src/service.py")

        assert resolved == "src/api_old.py"


def test_resolve_import_path_not_found():
    """Test that unresolvable imports return None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        populator = CodePopulator(get_database(), repo_path=repo_path)

        # Try to resolve non-existent module
        resolved = populator._resolve_import_path("nonexistent", "test.py")

        assert resolved is None


def test_full_import_extraction_workflow():
    """Test complete workflow of extracting and storing imports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create files
        (repo_path / "api.py").write_text("""
def get_user():
    pass
""")

        (repo_path / "api_old.py").write_text("""
def get_user():
    # Old implementation
    pass
""")

        (repo_path / "service.py").write_text("""
from api_old import get_user

def process():
    return get_user()
""")

        # Populate database
        db = get_database()

        # Reinitialize schema to ensure IMPORTS table has line property
        from idlergear.graph.schema import initialize_schema
        initialize_schema(db, drop_existing=True)

        populator = CodePopulator(db, repo_path=repo_path)

        # Process all files
        populator.populate_file("api.py")
        populator.populate_file("api_old.py")
        result = populator.populate_file("service.py")

        # Verify results
        assert result["symbols"] > 0
        assert result["relationships"] > 0

        # Query database for IMPORTS relationship
        conn = db.get_connection()
        imports_result = conn.execute("""
            MATCH (f1:File {path: 'service.py'})-[r:IMPORTS]->(f2:File {path: 'api_old.py'})
            RETURN r.line AS line
        """)

        assert imports_result.has_next()
        line = imports_result.get_next()[0]
        assert line > 0
