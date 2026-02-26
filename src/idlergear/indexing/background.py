"""Background indexing system for opportunistic idle-time processing.

Automatically fills in file annotations and knowledge graph during idle time.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


def _get_state_file() -> Path:
    """Get path to indexing state file."""
    from idlergear.config import find_idlergear_root

    root = find_idlergear_root()
    if root is None:
        return Path.cwd() / ".idlergear" / "indexing_state.json"
    return root / ".idlergear" / "indexing_state.json"


def _load_state() -> Dict[str, Any]:
    """Load indexing state from disk."""
    state_file = _get_state_file()

    if not state_file.exists():
        return {
            "paused": False,
            "last_file_index": 0,
            "last_commit_index": 0,
            "last_symbol_index": 0,
            "last_run": None,
            "total_files_indexed": 0,
            "total_commits_indexed": 0,
            "total_symbols_indexed": 0,
        }

    try:
        with open(state_file, "r") as f:
            return json.load(f)
    except Exception:
        return _load_state.__defaults__[0]  # Return default state


def _save_state(state: Dict[str, Any]) -> None:
    """Save indexing state to disk."""
    state_file = _get_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def get_indexing_status() -> Dict[str, Any]:
    """Get status of what needs indexing.

    Returns:
        Dictionary with indexing status for files, commits, symbols

    Example:
        >>> status = get_indexing_status()
        >>> print(f"{status['file_annotations']['unannotated']} files need annotation")
    """
    from idlergear.config import find_idlergear_root
    from idlergear.graph import get_database
    from idlergear.graph.schema import get_schema_info

    root = find_idlergear_root() or Path.cwd()
    state = _load_state()

    # Get file annotation status
    try:
        from idlergear.file_annotation_storage import FileAnnotationStorage
        storage = FileAnnotationStorage()
        annotations = storage.list_annotations()
        annotated_files = len(annotations)
    except Exception:
        annotated_files = 0

    # Count total Python files in project
    src_dirs = [root / "src", root / "lib", root / "app"]
    total_files = 0
    for src_dir in src_dirs:
        if src_dir.exists():
            total_files += len(list(src_dir.rglob("*.py")))

    # Get knowledge graph status
    try:
        db = get_database()
        schema_info = get_schema_info(db)
        node_counts = schema_info.get("node_counts", {})

        commits_indexed = node_counts.get("Commit", 0)
        symbols_indexed = node_counts.get("Symbol", 0)
        files_in_graph = node_counts.get("File", 0)
        relationships = sum(schema_info.get("relationship_counts", {}).values())
    except Exception:
        commits_indexed = 0
        symbols_indexed = 0
        files_in_graph = 0
        relationships = 0

    # Estimate total commits (read from git)
    total_commits = 100  # Default estimate
    try:
        from idlergear.git import GitServer
        git = GitServer(allowed_repos=[str(root)])
        commits = git.get_commits(limit=1000)
        total_commits = len(commits)
    except Exception:
        pass

    # Estimate total symbols (rough: 20 per file)
    estimated_symbols = total_files * 20

    return {
        "paused": state["paused"],
        "last_run": state["last_run"],
        "file_annotations": {
            "total_files": total_files,
            "annotated": annotated_files,
            "unannotated": total_files - annotated_files,
            "percent_complete": round((annotated_files / total_files * 100) if total_files > 0 else 0, 1),
        },
        "knowledge_graph": {
            "commits": {
                "indexed": commits_indexed,
                "estimated_total": total_commits,
                "remaining": max(0, total_commits - commits_indexed),
                "percent_complete": round((commits_indexed / total_commits * 100) if total_commits > 0 else 0, 1),
            },
            "symbols": {
                "indexed": symbols_indexed,
                "estimated_total": estimated_symbols,
                "remaining": max(0, estimated_symbols - symbols_indexed),
                "percent_complete": round((symbols_indexed / estimated_symbols * 100) if estimated_symbols > 0 else 0, 1),
            },
            "files_in_graph": files_in_graph,
            "relationships": relationships,
        },
        "summary": {
            "total_work_remaining": (total_files - annotated_files) + (total_commits - commits_indexed),
            "estimated_batches_remaining": ((total_files - annotated_files) + (total_commits - commits_indexed)) // 5,
        }
    }


def _index_file_annotations_batch(batch_size: int = 5) -> Dict[str, Any]:
    """Index a batch of unannotated files.

    Args:
        batch_size: Number of files to annotate

    Returns:
        Dictionary with results
    """
    from idlergear.config import find_idlergear_root
    from idlergear.file_annotation_storage import FileAnnotationStorage

    root = find_idlergear_root() or Path.cwd()
    state = _load_state()

    # Get already annotated files
    storage = FileAnnotationStorage()
    existing_annotations = storage.list_annotations()
    annotated_paths = {a.path for a in existing_annotations}

    # Find unannotated Python files
    src_dirs = [root / "src", root / "lib", root / "app"]
    unannotated_files = []

    for src_dir in src_dirs:
        if not src_dir.exists():
            continue

        for py_file in sorted(src_dir.rglob("*.py")):
            rel_path = str(py_file.relative_to(root))
            if rel_path not in annotated_paths:
                unannotated_files.append(py_file)

    # Skip to last index
    start_index = state.get("last_file_index", 0)
    files_to_annotate = unannotated_files[start_index:start_index + batch_size]

    annotated_count = 0
    errors = []

    for file_path in files_to_annotate:
        try:
            # Auto-generate basic annotation from file content
            rel_path = str(file_path.relative_to(root))

            # Extract classes/functions from file (simple approach)
            content = file_path.read_text()
            lines = content.split("\n")

            components = []
            tags = []

            # Extract class names
            for line in lines:
                if line.strip().startswith("class "):
                    class_name = line.split("class ")[1].split("(")[0].split(":")[0].strip()
                    components.append(class_name)
                elif line.strip().startswith("def ") and not line.strip().startswith("def _"):
                    func_name = line.split("def ")[1].split("(")[0].strip()
                    if not func_name.startswith("_"):
                        components.append(func_name)

            # Generate description from module docstring or file name
            description = None
            if '"""' in content:
                docstring_start = content.find('"""')
                docstring_end = content.find('"""', docstring_start + 3)
                if docstring_end > docstring_start:
                    description = content[docstring_start + 3:docstring_end].strip().split("\n")[0]

            if not description:
                # Generate from file name
                file_name = file_path.stem
                description = f"{file_name.replace('_', ' ').title()} module"

            # Determine tags from path
            path_parts = Path(rel_path).parts
            if "test" in path_parts or file_path.stem.startswith("test_"):
                tags.append("test")
            if "api" in path_parts:
                tags.append("api")
            if "graph" in path_parts:
                tags.append("graph")
            if "mcp" in path_parts or "mcp" in file_path.stem:
                tags.append("mcp")

            # Annotate file
            storage.save_annotation(
                path=rel_path,
                description=description[:200] if description else None,  # Limit length
                tags=tags[:5],  # Limit tags
                components=components[:10],  # Limit components
            )

            annotated_count += 1
        except Exception as e:
            errors.append({"file": str(file_path), "error": str(e)})

    # Update state
    state["last_file_index"] = start_index + batch_size
    state["total_files_indexed"] = state.get("total_files_indexed", 0) + annotated_count
    state["last_run"] = datetime.now().isoformat()
    _save_state(state)

    return {
        "files_annotated": annotated_count,
        "errors": errors,
        "files_remaining": len(unannotated_files) - (start_index + batch_size),
    }


def _index_commits_batch(batch_size: int = 5) -> Dict[str, Any]:
    """Index a batch of commits into knowledge graph.

    Args:
        batch_size: Number of commits to index

    Returns:
        Dictionary with results
    """
    from idlergear.graph import get_database
    from idlergear.graph.database import reset_database
    from idlergear.graph.populators import GitPopulator
    from idlergear.graph.schema import initialize_schema

    state = _load_state()

    # Release lock before populate
    reset_database()

    try:
        db = get_database()

        # Ensure schema exists
        try:
            from idlergear.graph.schema import get_schema_info
            get_schema_info(db)
        except Exception:
            initialize_schema(db)

        # Index next batch of commits
        populator = GitPopulator(db)
        result = populator.populate(
            max_commits=batch_size,
            incremental=True,  # Skip already indexed
        )

        # Update state
        state["last_commit_index"] = state.get("last_commit_index", 0) + batch_size
        state["total_commits_indexed"] = state.get("total_commits_indexed", 0) + result.get("commits", 0)
        state["last_run"] = datetime.now().isoformat()
        _save_state(state)

        return {
            "commits_indexed": result.get("commits", 0),
            "files_indexed": result.get("files", 0),
            "relationships_created": result.get("relationships", 0),
        }
    except Exception as e:
        return {
            "commits_indexed": 0,
            "error": str(e),
        }


def _index_symbols_batch(batch_size: int = 5) -> Dict[str, Any]:
    """Index code symbols from a batch of files.

    Args:
        batch_size: Number of files to process

    Returns:
        Dictionary with results
    """
    from idlergear.graph import get_database
    from idlergear.graph.database import reset_database
    from idlergear.graph.populators import CodePopulator
    from idlergear.graph.schema import initialize_schema

    # Release lock before populate
    reset_database()

    try:
        db = get_database()

        # Ensure schema exists
        try:
            from idlergear.graph.schema import get_schema_info
            get_schema_info(db)
        except Exception:
            initialize_schema(db)

        # Index code symbols (incremental - skips already indexed files)
        populator = CodePopulator(db)
        result = populator.populate_directory(
            directory="src",
            incremental=True,
        )

        return {
            "symbols_indexed": result.get("symbols", 0),
            "files_processed": result.get("files", 0),
            "relationships_created": result.get("relationships", 0),
        }
    except Exception as e:
        return {
            "symbols_indexed": 0,
            "error": str(e),
        }


def index_next_batch(batch_size: int = 5, target: str = "auto") -> Dict[str, Any]:
    """Index next batch of items during idle time.

    Intelligently chooses what to index based on priority:
    1. File annotations (fastest, most useful)
    2. Recent commits (git history)
    3. Code symbols (Python parsing)

    Args:
        batch_size: Number of items to process (default: 5)
        target: What to index ("auto", "files", "commits", "symbols")

    Returns:
        Dictionary with indexing results

    Example:
        >>> result = index_next_batch(batch_size=5)
        >>> print(f"Annotated {result['files_annotated']} files")
    """
    state = _load_state()

    if state["paused"]:
        return {"skipped": True, "reason": "Indexing paused"}

    status = get_indexing_status()

    # Determine what to index
    if target == "auto":
        # Priority: files > commits > symbols
        if status["file_annotations"]["unannotated"] > 0:
            target = "files"
        elif status["knowledge_graph"]["commits"]["remaining"] > 0:
            target = "commits"
        elif status["knowledge_graph"]["symbols"]["remaining"] > 0:
            target = "symbols"
        else:
            return {"completed": True, "message": "All indexing complete"}

    # Execute batch
    if target == "files":
        return {"target": "files", **_index_file_annotations_batch(batch_size)}
    elif target == "commits":
        return {"target": "commits", **_index_commits_batch(batch_size)}
    elif target == "symbols":
        return {"target": "symbols", **_index_symbols_batch(batch_size)}
    else:
        return {"error": f"Unknown target: {target}"}


def should_run_indexing() -> bool:
    """Check if background indexing should run.

    Returns:
        True if there's work to do and indexing is not paused
    """
    state = _load_state()

    if state["paused"]:
        return False

    status = get_indexing_status()

    # Check if any work remaining
    work_remaining = (
        status["file_annotations"]["unannotated"] > 0 or
        status["knowledge_graph"]["commits"]["remaining"] > 0 or
        status["knowledge_graph"]["symbols"]["remaining"] > 0
    )

    return work_remaining


def pause_indexing() -> Dict[str, str]:
    """Pause background indexing.

    Returns:
        Status message
    """
    state = _load_state()
    state["paused"] = True
    _save_state(state)

    return {"status": "paused", "message": "Background indexing paused"}


def resume_indexing() -> Dict[str, str]:
    """Resume background indexing.

    Returns:
        Status message
    """
    state = _load_state()
    state["paused"] = False
    _save_state(state)

    return {"status": "resumed", "message": "Background indexing resumed"}
