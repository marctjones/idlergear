"""
Data file reference detection from Python code.

Analyzes Python AST to find string literals that reference data files
(CSV, JSON, etc.) and tracks which versions are being used.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# Common data file extensions
DATA_FILE_EXTENSIONS = {
    ".csv",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".txt",
    ".tsv",
    ".parquet",
    ".pkl",
    ".pickle",
    ".h5",
    ".hdf5",
    ".npz",
    ".npy",
    ".feather",
    ".arrow",
    ".xml",
    ".sql",
    ".db",
    ".sqlite",
    ".dat",
}

# Function names that commonly take file paths as arguments
FILE_OPERATION_FUNCTIONS = {
    "open",
    "read_csv",
    "read_json",
    "read_parquet",
    "read_excel",
    "read_pickle",
    "read_table",
    "read_feather",
    "read_hdf",
    "load",
    "loads",
    "load_json",
    "load_yaml",
    "dump",
    "dumps",
    "dump_json",
    "dump_yaml",
    "to_csv",
    "to_json",
    "to_parquet",
    "to_pickle",
    "to_excel",
    "to_feather",
    "to_hdf",
    "Path",
}


def extract_file_references(
    tree: ast.AST, source_file: str
) -> List[Dict[str, any]]:
    """
    Extract file path references from Python AST.

    Args:
        tree: Parsed AST tree
        source_file: Path of the Python file being analyzed

    Returns:
        List of file references with metadata
    """
    references = []
    seen_locations = set()  # Track (path, line) to avoid duplicates

    for node in ast.walk(tree):
        # Look for function calls with string arguments
        if isinstance(node, ast.Call):
            func_name = _get_function_name(node.func)

            if func_name in FILE_OPERATION_FUNCTIONS:
                # Check arguments for file paths
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if _looks_like_file_path(arg.value):
                            location_key = (arg.value, node.lineno)
                            if location_key not in seen_locations:
                                references.append(
                                    {
                                        "path": arg.value,
                                        "line": node.lineno,
                                        "function": func_name,
                                        "source_file": source_file,
                                        "context": "function_arg",
                                    }
                                )
                                seen_locations.add(location_key)

                # Check keyword arguments
                for keyword in node.keywords:
                    if isinstance(keyword.value, ast.Constant) and isinstance(
                        keyword.value.value, str
                    ):
                        if _looks_like_file_path(keyword.value.value):
                            location_key = (keyword.value.value, node.lineno)
                            if location_key not in seen_locations:
                                references.append(
                                    {
                                        "path": keyword.value.value,
                                        "line": node.lineno,
                                        "function": func_name,
                                        "keyword": keyword.arg,
                                        "source_file": source_file,
                                        "context": "keyword_arg",
                                    }
                                )
                                seen_locations.add(location_key)

    return references


def _get_function_name(func_node: ast.AST) -> Optional[str]:
    """Extract function name from call node."""
    if isinstance(func_node, ast.Name):
        return func_node.id
    elif isinstance(func_node, ast.Attribute):
        # Handle method calls like pd.read_csv()
        return func_node.attr
    return None


def _looks_like_file_path(s: str) -> bool:
    """
    Check if string looks like a file path.

    Returns:
        True if string appears to be a file path
    """
    if not s or len(s) < 3:
        return False

    # Exclude URLs first
    if s.startswith(("http://", "https://", "ftp://", "s3://", "gs://", "://")):
        return False

    # Check for file extensions
    if any(s.endswith(ext) for ext in DATA_FILE_EXTENSIONS):
        return True

    # Check for path separators
    if "/" in s or "\\" in s:
        return True

    # Check for common data directory patterns
    data_patterns = [
        r"^data/",
        r"^datasets/",
        r"^input/",
        r"^output/",
        r"^cache/",
        r"^tmp/",
        r"^temp/",
        r"^\./data",
        r"^\./datasets",
    ]

    for pattern in data_patterns:
        if re.match(pattern, s):
            return True

    return False


def resolve_file_reference(
    ref_path: str, source_file: str, repo_path: Path
) -> Optional[str]:
    """
    Resolve a file reference to an actual file path.

    Args:
        ref_path: File path from code (e.g., "data/old_dataset.csv")
        source_file: Path of Python file containing the reference
        repo_path: Repository root path

    Returns:
        Resolved file path relative to repo root, or None if can't resolve
    """
    # Try multiple resolution strategies
    candidates = []

    # 1. Relative to repo root
    candidates.append(ref_path)

    # 2. Relative to source file directory
    source_dir = Path(source_file).parent
    candidates.append(str(source_dir / ref_path))

    # 3. Remove leading ./ if present
    if ref_path.startswith("./"):
        clean_path = ref_path[2:]
        candidates.append(clean_path)
        candidates.append(str(source_dir / clean_path))

    # 4. Try in common data directories
    for data_dir in ["data", "datasets", "input", "output"]:
        if not ref_path.startswith(data_dir):
            candidates.append(f"{data_dir}/{ref_path}")

    # Check which candidate exists
    for candidate in candidates:
        full_path = repo_path / candidate
        if full_path.exists() and full_path.is_file():
            # Return normalized relative path
            try:
                return str(Path(candidate).as_posix())
            except ValueError:
                continue

    return None


def group_references_by_file(
    references: List[Dict[str, any]]
) -> Dict[str, List[Dict[str, any]]]:
    """
    Group file references by the file being referenced.

    Args:
        references: List of file reference dicts

    Returns:
        Dict mapping referenced_file -> [reference dicts]
    """
    grouped = {}

    for ref in references:
        path = ref["path"]
        if path not in grouped:
            grouped[path] = []
        grouped[path].append(ref)

    return grouped


def detect_stale_data_references(
    references: List[Dict[str, any]],
    versioned_files: Dict[str, List],
    repo_path: Path,
) -> List[Dict[str, any]]:
    """
    Detect references to stale (non-current) versions of data files.

    Args:
        references: List of file references from extract_file_references()
        versioned_files: Output from git_version_detector.detect_versioned_files()
        repo_path: Repository root path

    Returns:
        List of stale reference warnings
    """
    warnings = []

    for ref in references:
        ref_path = ref["path"]

        # Resolve to actual file
        resolved_path = resolve_file_reference(
            ref_path, ref["source_file"], repo_path
        )

        if not resolved_path:
            continue

        # Check if this file is part of a versioned group
        for base_name, versions in versioned_files.items():
            stale_files = [v.path for v in versions if not v.is_current]
            current_files = [v.path for v in versions if v.is_current]

            if resolved_path in stale_files:
                # Found a reference to a stale file!
                warnings.append(
                    {
                        "source_file": ref["source_file"],
                        "line": ref["line"],
                        "stale_file": resolved_path,
                        "current_file": current_files[0] if current_files else None,
                        "reference_path": ref_path,
                        "function": ref.get("function"),
                        "base_name": base_name,
                    }
                )

    return warnings
