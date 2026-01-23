"""Populates graph database with Test nodes from test files."""

from pathlib import Path
from typing import Optional, Dict, Any, Set, List
import re
import ast

from ..database import GraphDatabase


class TestPopulator:
    """Populates graph database with Test nodes and relationships.

    Identifies test files and extracts individual test cases:
    - Python: pytest, unittest test functions/methods
    - JavaScript: jest, mocha test cases
    - Rust: cargo test functions
    - Go: *_test.go functions

    Creates:
    - Test nodes with name, type, file path, line numbers
    - COVERS relationships to symbols/files being tested

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = TestPopulator(db)
        >>> populator.populate()
    """

    def __init__(self, db: GraphDatabase, project_path: Optional[Path] = None):
        """Initialize test populator.

        Args:
            db: Graph database instance
            project_path: Path to project (defaults to current directory)
        """
        self.db = db
        self.project_path = project_path or Path.cwd()
        self._processed_tests: Set[str] = set()

    def populate(
        self,
        incremental: bool = True,
        link_coverage: bool = True,
    ) -> Dict[str, int]:
        """Populate graph with test nodes and relationships.

        Args:
            incremental: If True, skip tests already in database
            link_coverage: If True, create COVERS relationships

        Returns:
            Dictionary with counts: tests, covers_relationships
        """
        tests_added = 0
        covers_added = 0

        conn = self.db.get_connection()

        # Find all test files
        test_files = self._find_test_files()

        for test_file in test_files:
            # Extract tests from file
            tests = self._extract_tests_from_file(test_file)

            for test_info in tests:
                test_id = test_info["id"]

                # Skip if already processed (incremental mode)
                if incremental and test_id in self._processed_tests:
                    continue

                # Insert test node
                if self._insert_test(test_info):
                    tests_added += 1
                    self._processed_tests.add(test_id)

                    # Create COVERS relationships
                    if link_coverage:
                        covers_count = self._link_test_coverage(test_info)
                        covers_added += covers_count

        return {
            "tests": tests_added,
            "covers": covers_added,
        }

    def _find_test_files(self) -> List[Path]:
        """Find all test files in project."""
        test_files = []

        # Python test files
        for pattern in ["**/test_*.py", "**/*_test.py", "**/tests/**/*.py"]:
            test_files.extend(self.project_path.glob(pattern))

        # JavaScript test files
        for pattern in ["**/*.test.js", "**/*.spec.js", "**/*.test.ts", "**/*.spec.ts"]:
            test_files.extend(self.project_path.glob(pattern))

        # Rust test files (tests in src)
        for pattern in ["**/tests/**/*.rs"]:
            test_files.extend(self.project_path.glob(pattern))

        # Go test files
        for pattern in ["**/*_test.go"]:
            test_files.extend(self.project_path.glob(pattern))

        # Remove duplicates and filter out venv/node_modules
        test_files = [
            f for f in set(test_files)
            if "venv" not in f.parts
            and "node_modules" not in f.parts
            and ".tox" not in f.parts
        ]

        return test_files

    def _extract_tests_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract individual test cases from a test file."""
        if file_path.suffix == ".py":
            return self._extract_python_tests(file_path)
        elif file_path.suffix in [".js", ".ts"]:
            return self._extract_javascript_tests(file_path)
        elif file_path.suffix == ".rs":
            return self._extract_rust_tests(file_path)
        elif file_path.suffix == ".go":
            return self._extract_go_tests(file_path)
        return []

    def _extract_python_tests(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract pytest/unittest test functions from Python file."""
        tests = []
        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Test functions (pytest style)
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    tests.append({
                        "id": f"{file_path}::{node.name}",
                        "name": node.name,
                        "type": "pytest",
                        "file_path": str(file_path.relative_to(self.project_path)),
                        "line_start": node.lineno,
                        "line_end": node.end_lineno or node.lineno,
                        "status": "unknown",
                    })

                # Test methods in TestCase classes (unittest style)
                elif isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                            tests.append({
                                "id": f"{file_path}::{node.name}::{item.name}",
                                "name": f"{node.name}.{item.name}",
                                "type": "unittest",
                                "file_path": str(file_path.relative_to(self.project_path)),
                                "line_start": item.lineno,
                                "line_end": item.end_lineno or item.lineno,
                                "status": "unknown",
                            })

        except Exception as e:
            print(f"Error parsing Python tests in {file_path}: {e}")

        return tests

    def _extract_javascript_tests(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract jest/mocha test cases from JavaScript file."""
        tests = []
        try:
            content = file_path.read_text()

            # Match test() or it() calls
            for match in re.finditer(r"^\s*(test|it)\s*\(\s*['\"](.+?)['\"]", content, re.MULTILINE):
                test_name = match.group(2)
                line_num = content[:match.start()].count("\n") + 1

                tests.append({
                    "id": f"{file_path}::{test_name}",
                    "name": test_name,
                    "type": "jest",
                    "file_path": str(file_path.relative_to(self.project_path)),
                    "line_start": line_num,
                    "line_end": line_num,
                    "status": "unknown",
                })

        except Exception as e:
            print(f"Error parsing JavaScript tests in {file_path}: {e}")

        return tests

    def _extract_rust_tests(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract Rust test functions."""
        tests = []
        try:
            content = file_path.read_text()

            # Match #[test] or #[tokio::test] annotations
            for match in re.finditer(r"#\[(tokio::)?test\]\s*\n\s*fn\s+(\w+)", content):
                test_name = match.group(2)
                line_num = content[:match.start()].count("\n") + 1

                tests.append({
                    "id": f"{file_path}::{test_name}",
                    "name": test_name,
                    "type": "cargo_test",
                    "file_path": str(file_path.relative_to(self.project_path)),
                    "line_start": line_num,
                    "line_end": line_num,
                    "status": "unknown",
                })

        except Exception as e:
            print(f"Error parsing Rust tests in {file_path}: {e}")

        return tests

    def _extract_go_tests(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract Go test functions."""
        tests = []
        try:
            content = file_path.read_text()

            # Match func TestXxx(t *testing.T)
            for match in re.finditer(r"^func\s+(Test\w+)\s*\(", content, re.MULTILINE):
                test_name = match.group(1)
                line_num = content[:match.start()].count("\n") + 1

                tests.append({
                    "id": f"{file_path}::{test_name}",
                    "name": test_name,
                    "type": "go_test",
                    "file_path": str(file_path.relative_to(self.project_path)),
                    "line_start": line_num,
                    "line_end": line_num,
                    "status": "unknown",
                })

        except Exception as e:
            print(f"Error parsing Go tests in {file_path}: {e}")

        return tests

    def _insert_test(self, test_info: Dict[str, Any]) -> bool:
        """Insert test node into database."""
        conn = self.db.get_connection()

        try:
            conn.execute("""
                CREATE (t:Test {
                    id: $id,
                    name: $name,
                    type: $type,
                    file_path: $file_path,
                    line_start: $line_start,
                    line_end: $line_end,
                    status: $status,
                    last_run: NULL,
                    duration_ms: NULL
                })
            """, {
                "id": test_info["id"],
                "name": test_info["name"],
                "type": test_info["type"],
                "file_path": test_info["file_path"],
                "line_start": test_info["line_start"],
                "line_end": test_info["line_end"],
                "status": test_info["status"],
            })
            return True

        except Exception as e:
            print(f"Error inserting test {test_info['id']}: {e}")
            return False

    def _link_test_coverage(self, test_info: Dict[str, Any]) -> int:
        """Create COVERS relationships based on test name patterns."""
        conn = self.db.get_connection()
        count = 0

        # Infer what's being tested from test name
        test_name = test_info["name"]
        file_path = test_info["file_path"]

        # Try to find corresponding source file
        source_file = self._infer_source_file(file_path)

        if source_file:
            # Link test to source file
            try:
                check_result = conn.execute(
                    "MATCH (f:File {path: $path}) RETURN f",
                    {"path": source_file}
                )

                if check_result.has_next():
                    conn.execute("""
                        MATCH (t:Test {id: $test_id})
                        MATCH (f:File {path: $path})
                        CREATE (t)-[:COVERS {coverage_percent: NULL}]->(f)
                    """, {
                        "test_id": test_info["id"],
                        "path": source_file,
                    })
                    count += 1

            except Exception as e:
                print(f"Error linking test coverage: {e}")

        return count

    def _infer_source_file(self, test_file_path: str) -> Optional[str]:
        """Infer source file from test file path."""
        # Remove test_ prefix or _test suffix
        source_path = test_file_path.replace("test_", "").replace("_test", "")

        # Remove tests/ directory
        source_path = source_path.replace("/tests/", "/").replace("tests/", "")

        # Check if source file exists
        full_path = self.project_path / source_path
        if full_path.exists():
            return source_path

        return None
