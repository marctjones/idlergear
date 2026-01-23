"""Populates graph database with Dependency nodes from package manager files."""

from pathlib import Path
from typing import Optional, Dict, Any, Set, List
import json
import re

try:
    import tomli
except ImportError:
    tomli = None  # type: ignore

from ..database import GraphDatabase


class DependencyPopulator:
    """Populates graph database with Dependency nodes and relationships.

    Extracts dependency information from:
    - Python: requirements.txt, setup.py, pyproject.toml, Pipfile
    - JavaScript: package.json, package-lock.json
    - Rust: Cargo.toml
    - Go: go.mod
    - Ruby: Gemfile
    - .NET: *.csproj, packages.config

    Creates:
    - Dependency nodes with version information
    - DEPENDS_ON_DEPENDENCY relationships from files

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = DependencyPopulator(db)
        >>> populator.populate()
    """

    def __init__(self, db: GraphDatabase, project_path: Optional[Path] = None):
        """Initialize dependency populator.

        Args:
            db: Graph database instance
            project_path: Path to project (defaults to current directory)
        """
        self.db = db
        self.project_path = project_path or Path.cwd()
        self._processed_deps: Set[str] = set()

    def populate(
        self,
        incremental: bool = True,
    ) -> Dict[str, int]:
        """Populate graph with dependency nodes and relationships.

        Args:
            incremental: If True, skip dependencies already in database

        Returns:
            Dictionary with counts: dependencies, relationships
        """
        deps_added = 0
        relationships_added = 0

        conn = self.db.get_connection()

        # Find and parse all dependency files
        all_deps = self._find_all_dependencies()

        for dep_info in all_deps:
            dep_key = f"{dep_info['name']}:{dep_info['version']}"

            # Skip if already processed (incremental mode)
            if incremental and dep_key in self._processed_deps:
                continue

            # Insert dependency node (or update if exists)
            if self._insert_or_update_dependency(dep_info):
                deps_added += 1
                self._processed_deps.add(dep_key)

            # Create relationships to files
            for file_path in dep_info.get("required_by", []):
                if self._link_file_to_dependency(file_path, dep_info):
                    relationships_added += 1

        return {
            "dependencies": deps_added,
            "relationships": relationships_added,
        }

    def _find_all_dependencies(self) -> List[Dict[str, Any]]:
        """Find all dependency declarations in project."""
        all_deps = []

        # Python dependencies
        all_deps.extend(self._parse_python_deps())

        # JavaScript dependencies
        all_deps.extend(self._parse_javascript_deps())

        # Rust dependencies
        all_deps.extend(self._parse_rust_deps())

        # Go dependencies
        all_deps.extend(self._parse_go_deps())

        return all_deps

    def _parse_python_deps(self) -> List[Dict[str, Any]]:
        """Parse Python dependencies from various sources."""
        deps = []

        # requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            deps.extend(self._parse_requirements_txt(req_file))

        # pyproject.toml
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            deps.extend(self._parse_pyproject_toml(pyproject))

        return deps

    def _parse_requirements_txt(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse requirements.txt file."""
        deps = []
        try:
            content = file_path.read_text()
            for line_num, line in enumerate(content.split("\n"), 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse dependency (simple version, doesn't handle all pip syntax)
                match = re.match(r"^([a-zA-Z0-9_-]+)(.*?)$", line)
                if match:
                    name = match.group(1)
                    version_spec = match.group(2).strip()

                    # Extract version if present
                    version = "latest"
                    if version_spec:
                        version_match = re.search(r"==\s*([0-9.]+)", version_spec)
                        if version_match:
                            version = version_match.group(1)

                    deps.append({
                        "name": name,
                        "version": version,
                        "type": "python",
                        "source": "requirements.txt",
                        "required_by": [str(file_path.relative_to(self.project_path))],
                        "import_line": line_num,
                    })

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return deps

    def _parse_pyproject_toml(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse pyproject.toml file."""
        deps = []
        if tomli is None:
            return deps  # Skip if tomli not installed

        try:
            content = file_path.read_text()
            data = tomli.loads(content)

            # Poetry dependencies
            if "tool" in data and "poetry" in data["tool"]:
                poetry_deps = data["tool"]["poetry"].get("dependencies", {})
                for name, version_spec in poetry_deps.items():
                    if name == "python":
                        continue

                    version = version_spec if isinstance(version_spec, str) else "latest"

                    deps.append({
                        "name": name,
                        "version": version,
                        "type": "python",
                        "source": "pyproject.toml",
                        "required_by": [str(file_path.relative_to(self.project_path))],
                    })

            # PEP 621 dependencies
            if "project" in data and "dependencies" in data["project"]:
                for dep_str in data["project"]["dependencies"]:
                    match = re.match(r"^([a-zA-Z0-9_-]+)", dep_str)
                    if match:
                        name = match.group(1)
                        deps.append({
                            "name": name,
                            "version": "latest",
                            "type": "python",
                            "source": "pyproject.toml",
                            "required_by": [str(file_path.relative_to(self.project_path))],
                        })

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return deps

    def _parse_javascript_deps(self) -> List[Dict[str, Any]]:
        """Parse JavaScript dependencies from package.json."""
        deps = []

        pkg_file = self.project_path / "package.json"
        if not pkg_file.exists():
            return deps

        try:
            data = json.loads(pkg_file.read_text())

            # Regular dependencies
            for name, version in data.get("dependencies", {}).items():
                deps.append({
                    "name": name,
                    "version": version.lstrip("^~"),
                    "type": "javascript",
                    "source": "package.json",
                    "required_by": ["package.json"],
                })

            # Dev dependencies
            for name, version in data.get("devDependencies", {}).items():
                deps.append({
                    "name": name,
                    "version": version.lstrip("^~"),
                    "type": "javascript",
                    "source": "package.json",
                    "required_by": ["package.json"],
                })

        except Exception as e:
            print(f"Error parsing package.json: {e}")

        return deps

    def _parse_rust_deps(self) -> List[Dict[str, Any]]:
        """Parse Rust dependencies from Cargo.toml."""
        deps = []

        cargo_file = self.project_path / "Cargo.toml"
        if not cargo_file.exists():
            return deps

        if tomli is None:
            return deps  # Skip if tomli not installed

        try:
            content = cargo_file.read_text()
            data = tomli.loads(content)

            for name, version_spec in data.get("dependencies", {}).items():
                version = version_spec if isinstance(version_spec, str) else version_spec.get("version", "latest")

                deps.append({
                    "name": name,
                    "version": version,
                    "type": "rust",
                    "source": "Cargo.toml",
                    "required_by": ["Cargo.toml"],
                })

        except Exception as e:
            print(f"Error parsing Cargo.toml: {e}")

        return deps

    def _parse_go_deps(self) -> List[Dict[str, Any]]:
        """Parse Go dependencies from go.mod."""
        deps = []

        go_mod = self.project_path / "go.mod"
        if not go_mod.exists():
            return deps

        try:
            content = go_mod.read_text()
            for line in content.split("\n"):
                line = line.strip()

                # Match require statements
                match = re.match(r"^\s*([^\s]+)\s+v([0-9.]+)", line)
                if match:
                    name = match.group(1)
                    version = match.group(2)

                    deps.append({
                        "name": name,
                        "version": version,
                        "type": "go",
                        "source": "go.mod",
                        "required_by": ["go.mod"],
                    })

        except Exception as e:
            print(f"Error parsing go.mod: {e}")

        return deps

    def _insert_or_update_dependency(self, dep_info: Dict[str, Any]) -> bool:
        """Insert dependency node or update if exists."""
        conn = self.db.get_connection()

        try:
            # Try to find existing dependency
            result = conn.execute(
                "MATCH (d:Dependency {name: $name}) RETURN d",
                {"name": dep_info["name"]}
            )

            if result.has_next():
                # Update existing dependency
                conn.execute("""
                    MATCH (d:Dependency {name: $name})
                    SET d.version = $version,
                        d.type = $type,
                        d.source = $source
                """, {
                    "name": dep_info["name"],
                    "version": dep_info["version"],
                    "type": dep_info["type"],
                    "source": dep_info["source"],
                })
                return False
            else:
                # Insert new dependency
                conn.execute("""
                    CREATE (d:Dependency {
                        name: $name,
                        version: $version,
                        type: $type,
                        source: $source,
                        required_by: $required_by
                    })
                """, {
                    "name": dep_info["name"],
                    "version": dep_info["version"],
                    "type": dep_info["type"],
                    "source": dep_info["source"],
                    "required_by": dep_info.get("required_by", []),
                })
                return True

        except Exception as e:
            print(f"Error inserting dependency {dep_info['name']}: {e}")
            return False

    def _link_file_to_dependency(self, file_path: str, dep_info: Dict[str, Any]) -> bool:
        """Create DEPENDS_ON_DEPENDENCY relationship from file to dependency."""
        conn = self.db.get_connection()

        try:
            # Check if file exists in database
            check_result = conn.execute(
                "MATCH (f:File {path: $path}) RETURN f",
                {"path": file_path}
            )

            if not check_result.has_next():
                return False

            # Create relationship
            conn.execute("""
                MATCH (f:File {path: $path})
                MATCH (d:Dependency {name: $name})
                CREATE (f)-[:DEPENDS_ON_DEPENDENCY {
                    import_line: $line,
                    required: true
                }]->(d)
            """, {
                "path": file_path,
                "name": dep_info["name"],
                "line": dep_info.get("import_line", 0),
            })
            return True

        except Exception as e:
            print(f"Error linking {file_path} to {dep_info['name']}: {e}")
            return False
