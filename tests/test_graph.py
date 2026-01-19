"""Tests for knowledge graph module."""

import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from idlergear.graph import (
    get_database,
    GraphDatabase,
    initialize_schema,
    query_task_context,
    query_file_context,
    query_recent_changes,
    query_related_files,
)
from idlergear.graph.database import reset_database
from idlergear.graph.schema import get_schema_info


@pytest.fixture
def temp_db():
    """Create a temporary graph database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_graph.db"
        db = GraphDatabase(db_path)
        yield db
        db.close()
        # Reset global instance to avoid test interference
        reset_database()


class TestGraphDatabase:
    """Tests for GraphDatabase connection management."""

    def test_database_creates_successfully(self, temp_db):
        """Database initializes without errors."""
        assert temp_db.db is not None
        assert temp_db.conn is not None
        assert temp_db.db_path.exists()

    def test_get_connection(self, temp_db):
        """get_connection() returns active connection."""
        conn = temp_db.get_connection()
        assert conn is not None
        # Verify connection works
        result = conn.execute("RETURN 1 AS test")
        assert result.get_next()[0] == 1

    def test_execute_query(self, temp_db):
        """execute() runs Cypher queries."""
        result = temp_db.execute("RETURN 42 AS answer")
        assert result.get_next()[0] == 42

    def test_context_manager(self):
        """Database works as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "ctx_test.db"
            with GraphDatabase(db_path) as db:
                result = db.execute("RETURN 1 AS test")
                assert result.get_next()[0] == 1
            # Connection should be closed after exit


class TestSchemaInitialization:
    """Tests for schema creation and validation."""

    def test_initialize_schema_creates_tables(self, temp_db):
        """initialize_schema() creates all node and relationship tables."""
        initialize_schema(temp_db)

        # Verify schema file_exists by checking schema info
        info = get_schema_info(temp_db)

        # Check node types created
        expected_nodes = ["Task", "File", "Commit", "Symbol", "Note", "Reference", "Plan", "Branch"]
        assert set(info["node_types"]) == set(expected_nodes)

        # Check relationship types created
        expected_rels = ["MODIFIES", "IMPORTS", "CHANGES", "IMPLEMENTED_IN", "CONTAINS"]
        for rel in expected_rels:
            assert rel in info["relationship_types"]

    def test_drop_existing_schema(self, temp_db):
        """initialize_schema() with drop_existing=True rebuilds schema."""
        # Create schema
        initialize_schema(temp_db)

        # Add a node
        conn = temp_db.get_connection()
        conn.execute("""
            CREATE (t:Task {
                id: 1,
                title: 'Test Task',
                body: '',
                state: 'open',
                priority: '',
                labels: [],
                created_at: timestamp('2025-01-18T12:00:00'),
                updated_at: timestamp('2025-01-18T12:00:00'),
                closed_at: timestamp('1970-01-01T00:00:00'),
                source: 'local'
            })
        """)

        # Verify node file_exists
        result = conn.execute("MATCH (t:Task {id: 1}) RETURN t.title")
        assert result.get_next()[0] == "Test Task"

        # Drop and recreate
        initialize_schema(temp_db, drop_existing=True)

        # Verify node is gone
        result = conn.execute("MATCH (t:Task {id: 1}) RETURN COUNT(t) AS count")
        assert result.get_next()[0] == 0

    def test_schema_info_returns_counts(self, temp_db):
        """get_schema_info() returns correct counts."""
        initialize_schema(temp_db)

        info = get_schema_info(temp_db)

        # Initially empty
        assert info["total_nodes"] == 0
        assert info["total_relationships"] == 0

        # All node types should have 0 count
        for node_type in ["Task", "File", "Commit", "Symbol"]:
            assert info["node_counts"][node_type] == 0


class TestBasicOperations:
    """Tests for basic graph operations."""

    def test_insert_task_node(self, temp_db):
        """Can insert a Task node."""
        initialize_schema(temp_db)
        conn = temp_db.get_connection()

        conn.execute("""
            CREATE (t:Task {
                id: 278,
                title: 'Implement knowledge graph',
                body: 'Add Kuzu integration',
                state: 'open',
                priority: 'high',
                labels: ['feature'],
                created_at: timestamp('2025-01-18T12:00:00'),
                updated_at: timestamp('2025-01-18T12:00:00'),
                closed_at: timestamp('1970-01-01T00:00:00'),
                source: 'local'
            })
        """)

        # Query it back
        result = conn.execute("MATCH (t:Task {id: 278}) RETURN t.title, t.state")
        row = result.get_next()
        assert row[0] == "Implement knowledge graph"
        assert row[1] == "open"

    def test_insert_file_node(self, temp_db):
        """Can insert a File node."""
        initialize_schema(temp_db)
        conn = temp_db.get_connection()

        conn.execute("""
            CREATE (f:File {
                path: 'src/idlergear/graph/database.py',
                language: 'python',
                size: 2450,
                lines: 115,
                last_modified: timestamp('2025-01-18T12:00:00'),
                file_exists: true,
                hash: 'abc123'
            })
        """)

        result = conn.execute("MATCH (f:File {path: 'src/idlergear/graph/database.py'}) RETURN f.language, f.lines")
        row = result.get_next()
        assert row[0] == "python"
        assert row[1] == 115

    def test_create_relationship(self, temp_db):
        """Can create relationships between nodes."""
        initialize_schema(temp_db)
        conn = temp_db.get_connection()

        # Create task and file
        conn.execute("""
            CREATE (t:Task {
                id: 278,
                title: 'Test',
                body: '',
                state: 'open',
                priority: '',
                labels: [],
                created_at: timestamp('2025-01-18T12:00:00'),
                updated_at: timestamp('2025-01-18T12:00:00'),
                closed_at: timestamp('1970-01-01T00:00:00'),
                source: 'local'
            })
        """)

        conn.execute("""
            CREATE (f:File {
                path: 'test.py',
                language: 'python',
                size: 100,
                lines: 10,
                last_modified: timestamp('2025-01-18T12:00:00'),
                file_exists: true,
                hash: 'abc'
            })
        """)

        # Create relationship
        conn.execute("""
            MATCH (t:Task {id: 278})
            MATCH (f:File {path: 'test.py'})
            CREATE (t)-[:MODIFIES {change_type: 'edit'}]->(f)
        """)

        # Query relationship
        result = conn.execute("""
            MATCH (t:Task {id: 278})-[:MODIFIES]->(f:File)
            RETURN f.path
        """)
        assert result.get_next()[0] == "test.py"


class TestQueryFunctions:
    """Tests for common query patterns."""

    def test_query_task_context_empty(self, temp_db):
        """query_task_context() returns empty dict for non-existent task."""
        initialize_schema(temp_db)
        result = query_task_context(temp_db, 999)
        assert result == {}

    def test_query_task_context_with_data(self, temp_db):
        """query_task_context() returns task info with related data."""
        initialize_schema(temp_db)
        conn = temp_db.get_connection()

        # Create task
        conn.execute("""
            CREATE (t:Task {
                id: 278,
                title: 'Implement graph',
                body: '',
                state: 'open',
                priority: 'high',
                labels: [],
                created_at: timestamp('2025-01-18T12:00:00'),
                updated_at: timestamp('2025-01-18T12:00:00'),
                closed_at: timestamp('1970-01-01T00:00:00'),
                source: 'local'
            })
        """)

        # Create file
        conn.execute("""
            CREATE (f:File {
                path: 'src/graph/database.py',
                language: 'python',
                size: 100,
                lines: 10,
                last_modified: timestamp('2025-01-18T12:00:00'),
                file_exists: true,
                hash: 'abc'
            })
        """)

        # Create relationship
        conn.execute("""
            MATCH (t:Task {id: 278})
            MATCH (f:File {path: 'src/graph/database.py'})
            CREATE (t)-[:MODIFIES]->(f)
        """)

        # Query task context
        context = query_task_context(temp_db, 278)

        assert context["task_id"] == 278
        assert context["title"] == "Implement graph"
        assert context["state"] == "open"
        assert "src/graph/database.py" in context["files"]
        assert context["commits"] == []
        assert context["symbols"] == []

    def test_query_file_context_empty(self, temp_db):
        """query_file_context() returns empty dict for non-existent file."""
        initialize_schema(temp_db)
        result = query_file_context(temp_db, "nonexistent.py")
        assert result == {}

    def test_query_file_context_with_data(self, temp_db):
        """query_file_context() returns file info with related data."""
        initialize_schema(temp_db)
        conn = temp_db.get_connection()

        # Create file
        conn.execute("""
            CREATE (f:File {
                path: 'src/api.py',
                language: 'python',
                size: 2500,
                lines: 120,
                last_modified: timestamp('2025-01-18T12:00:00'),
                file_exists: true,
                hash: 'def456'
            })
        """)

        # Query file context
        context = query_file_context(temp_db, "src/api.py")

        assert context["file_path"] == "src/api.py"
        assert context["language"] == "python"
        assert context["lines"] == 120
        assert context["tasks"] == []
        assert context["imports"] == []
        assert context["symbols"] == []

    def test_query_recent_changes_empty(self, temp_db):
        """query_recent_changes() returns empty list when no commits."""
        initialize_schema(temp_db)
        result = query_recent_changes(temp_db, limit=5)
        assert result == []

    def test_query_related_files_empty(self, temp_db):
        """query_related_files() returns empty list when no imports."""
        initialize_schema(temp_db)
        conn = temp_db.get_connection()

        # Create file without imports
        conn.execute("""
            CREATE (f:File {
                path: 'src/main.py',
                language: 'python',
                size: 100,
                lines: 10,
                last_modified: timestamp('2025-01-18T12:00:00'),
                file_exists: true,
                hash: 'abc'
            })
        """)

        result = query_related_files(temp_db, "src/main.py")
        assert result == []
