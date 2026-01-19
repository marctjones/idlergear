"""Tests for code symbol populator."""

import tempfile
from pathlib import Path

import pytest

from idlergear.graph import get_database, initialize_schema, GraphDatabase
from idlergear.graph.database import reset_database
from idlergear.graph.populators import CodePopulator


@pytest.fixture
def temp_db():
    """Create a temporary graph database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_graph.db"
        db = GraphDatabase(db_path)
        initialize_schema(db)
        yield db
        db.close()
        reset_database()


@pytest.fixture
def temp_code_repo():
    """Create a temporary directory with Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create source directory
        src_dir = repo_path / "src"
        src_dir.mkdir()

        # Create simple module
        simple_file = src_dir / "simple.py"
        simple_file.write_text("""
def hello():
    '''Say hello.'''
    return "hello"

def world():
    return "world"

class Greeter:
    '''A simple greeter class.'''

    def greet(self, name):
        '''Greet someone by name.'''
        return f"Hello, {name}!"

    def farewell(self, name):
        return f"Goodbye, {name}!"
""")

        # Create another module
        utils_file = src_dir / "utils.py"
        utils_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
""")

        yield repo_path


class TestCodePopulator:
    """Tests for CodePopulator."""

    def test_populate_directory_basic(self, temp_db, temp_code_repo):
        """populate_directory() creates symbol nodes."""
        populator = CodePopulator(temp_db, temp_code_repo)
        stats = populator.populate_directory("src")

        # Should have processed 2 files
        assert stats["files"] == 2

        # Should have created symbols
        assert stats["symbols"] > 0

        # Should have created relationships
        assert stats["relationships"] > 0

    def test_function_symbols_extracted(self, temp_db, temp_code_repo):
        """Functions are extracted as symbols."""
        populator = CodePopulator(temp_db, temp_code_repo)
        populator.populate_directory("src")

        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (s:Symbol {type: 'function'})
            RETURN s.name, s.docstring, s.line_start
        """)

        functions = []
        while result.has_next():
            row = result.get_next()
            functions.append({
                "name": row[0],
                "docstring": row[1],
                "line_start": row[2],
            })

        # Should have found hello() and world() functions
        function_names = [f["name"] for f in functions]
        assert "hello" in function_names
        assert "world" in function_names

        # Check docstring extraction
        hello_func = next(f for f in functions if f["name"] == "hello")
        assert "Say hello" in hello_func["docstring"]

    def test_class_symbols_extracted(self, temp_db, temp_code_repo):
        """Classes are extracted as symbols."""
        populator = CodePopulator(temp_db, temp_code_repo)
        populator.populate_directory("src")

        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (s:Symbol {type: 'class'})
            RETURN s.name, s.docstring
        """)

        classes = []
        while result.has_next():
            row = result.get_next()
            classes.append({"name": row[0], "docstring": row[1]})

        # Should have found Greeter and Calculator classes
        class_names = [c["name"] for c in classes]
        assert "Greeter" in class_names
        assert "Calculator" in class_names

    def test_method_symbols_extracted(self, temp_db, temp_code_repo):
        """Methods are extracted as symbols."""
        populator = CodePopulator(temp_db, temp_code_repo)
        populator.populate_directory("src")

        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (s:Symbol {type: 'method'})
            RETURN s.name, s.docstring
        """)

        methods = []
        while result.has_next():
            row = result.get_next()
            methods.append({"name": row[0], "docstring": row[1]})

        # Should have found methods
        method_names = [m["name"] for m in methods]
        assert "Greeter.greet" in method_names
        assert "Greeter.farewell" in method_names
        assert "Calculator.add" in method_names
        assert "Calculator.subtract" in method_names

        # Check docstring extraction for method
        greet_method = next(m for m in methods if m["name"] == "Greeter.greet")
        assert "Greet someone" in greet_method["docstring"]

    def test_contains_relationships_created(self, temp_db, temp_code_repo):
        """CONTAINS relationships link files to symbols."""
        populator = CodePopulator(temp_db, temp_code_repo)
        populator.populate_directory("src")

        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (f:File {path: 'src/simple.py'})-[:CONTAINS]->(s:Symbol)
            RETURN s.name, s.type
        """)

        symbols = []
        while result.has_next():
            row = result.get_next()
            symbols.append({"name": row[0], "type": row[1]})

        # Should have relationships for functions, class, and methods
        symbol_names = [s["name"] for s in symbols]
        assert "hello" in symbol_names
        assert "world" in symbol_names
        assert "Greeter" in symbol_names
        assert "Greeter.greet" in symbol_names
        assert "Greeter.farewell" in symbol_names

    def test_populate_single_file(self, temp_db, temp_code_repo):
        """populate_file() processes a single file."""
        populator = CodePopulator(temp_db, temp_code_repo)
        stats = populator.populate_file("src/utils.py")

        # Should have created symbols
        assert stats["symbols"] > 0
        assert stats["relationships"] > 0

        # Verify Calculator class and methods exist
        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (s:Symbol)
            WHERE s.file_path = 'src/utils.py'
            RETURN s.name
        """)

        symbols = []
        while result.has_next():
            symbols.append(result.get_next()[0])

        assert "Calculator" in symbols
        assert "Calculator.add" in symbols
        assert "Calculator.subtract" in symbols

    def test_incremental_population(self, temp_db, temp_code_repo):
        """populate_directory() with incremental=True skips unchanged files."""
        populator = CodePopulator(temp_db, temp_code_repo)

        # First population
        stats1 = populator.populate_directory("src")
        assert stats1["files"] == 2

        # Second population (incremental)
        stats2 = populator.populate_directory("src", incremental=True)
        assert stats2["files"] == 0  # No files processed

    def test_file_nodes_created(self, temp_db, temp_code_repo):
        """File nodes are created for Python files."""
        populator = CodePopulator(temp_db, temp_code_repo)
        populator.populate_directory("src")

        conn = temp_db.get_connection()
        result = conn.execute("""
            MATCH (f:File)
            WHERE f.language = 'python'
            RETURN f.path, f.lines
        """)

        files = []
        while result.has_next():
            row = result.get_next()
            files.append({"path": row[0], "lines": row[1]})

        # Should have created file nodes
        file_paths = [f["path"] for f in files]
        assert "src/simple.py" in file_paths
        assert "src/utils.py" in file_paths

        # Check line counts
        simple_file = next(f for f in files if f["path"] == "src/simple.py")
        assert simple_file["lines"] > 0

    def test_skip_syntax_errors(self, temp_db, temp_code_repo):
        """Files with syntax errors are skipped gracefully."""
        # Create file with syntax error
        bad_file = temp_code_repo / "src" / "bad.py"
        bad_file.write_text("def broken(:\n    return 'broken'")

        populator = CodePopulator(temp_db, temp_code_repo)
        stats = populator.populate_directory("src")

        # Should still process the other files
        assert stats["files"] >= 2
