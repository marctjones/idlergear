# File Registry Guide

The File Registry tracks file status (current/deprecated/archived/problematic) to prevent AI assistants from accessing outdated files during development sessions.

## Problem Statement

During development, engineers commonly create multiple versions of files:
- `api.py` → `api_v2.py` → `api_new.py`
- `handler.py` → `handler_old.py` (keeping old version as reference)
- `util.py` → `util_backup.py` (safety backup before refactor)

This leads to bugs when:
1. AI assistants reference old versions instead of current ones
2. Code imports mix old and new versions
3. Old versions accumulate without anyone knowing which is current

The File Registry solves this by explicitly tracking which files are current, deprecated, archived, or problematic.

## Quick Start

### Using MCP Tools (Recommended for AI Assistants)

```python
# Register a new file as current
idlergear_file_register(path="api_v2.py", status="current")

# Deprecate old version
idlergear_file_deprecate(
    path="api.py",
    successor="api_v2.py",
    reason="Refactored to use async/await"
)

# Check file status
result = idlergear_file_status(path="api.py")
# Returns: {"status": "deprecated", "current_version": "api_v2.py", ...}

# List all deprecated files
result = idlergear_file_list(status="deprecated")
```

### Using Python API

```python
from idlergear.file_registry import FileRegistry, FileStatus

# Initialize registry
registry = FileRegistry()  # Uses .idlergear/file_registry.json

# Register files
registry.register_file("api_v2.py", FileStatus.CURRENT)
registry.deprecate_file("api.py", successor="api_v2.py", reason="Old version")

# Check status
status = registry.get_status("api.py")
if status == FileStatus.DEPRECATED:
    current = registry.get_current_version("api.py")
    print(f"Use {current} instead")

# List files
for entry in registry.list_files(FileStatus.DEPRECATED):
    print(f"{entry.path} → {entry.current_version}")
```

## File Status Types

### CURRENT
Files that are actively maintained and should be used.

**When to use:**
- New files you just created
- Files that replaced deprecated versions
- Active code in use

**Example:**
```python
registry.register_file("api_v2.py", FileStatus.CURRENT)
```

### DEPRECATED
Files that are outdated but kept for reference. Should not be used in new code.

**When to use:**
- Old versions of files that have been replaced
- Files with known issues that have been fixed elsewhere
- Code that's being phased out

**Example:**
```python
registry.deprecate_file(
    "api.py",
    successor="api_v2.py",
    reason="Refactored to use FastAPI"
)
```

### ARCHIVED
Files kept for historical purposes. No longer relevant to current development.

**When to use:**
- Old experiments that didn't work out
- Prototypes that were replaced
- Code from previous iterations

**Example:**
```python
registry.register_file(
    "prototype_v1.py",
    FileStatus.ARCHIVED,
    reason="Initial prototype, replaced by api_v2.py"
)
```

### PROBLEMATIC
Files with known issues that need attention.

**When to use:**
- Files with security vulnerabilities
- Code that causes bugs
- Files that need refactoring

**Example:**
```python
registry.register_file(
    "auth.py",
    FileStatus.PROBLEMATIC,
    reason="SQL injection vulnerability - DO NOT USE"
)
```

## Pattern-Based Rules

Register patterns to automatically mark multiple files:

```python
# Mark all backup files as deprecated
registry.add_pattern("*.bak", FileStatus.DEPRECATED, reason="Backup files")

# Archive everything in old directories
registry.add_pattern("archive/**/*", FileStatus.ARCHIVED)

# Mark temporary files as problematic
registry.add_pattern("tmp_*.py", FileStatus.PROBLEMATIC, reason="Temporary file")
```

### Pattern Syntax

- `*` - Matches any characters except `/` within a path segment
  - `*.py` matches `test.py` and `dir/test.py`
  - `tmp_*` matches `tmp_file.txt` anywhere

- `**` - Matches zero or more directories
  - `archive/**/*` matches `archive/file.txt` and `archive/deep/path/file.txt`
  - `src/**/*.py` matches all Python files under `src/`

- `?` - Matches single character
  - `file?.txt` matches `file1.txt` and `fileA.txt`

- Patterns without `/` match anywhere in the tree (basename matching)
- Patterns with `/` match from the start of the path

## Common Workflows

### 1. Creating a New Version

When you create a better version of a file:

```python
# 1. Register new version as current
registry.register_file("api_v2.py", FileStatus.CURRENT)

# 2. Deprecate old version
registry.deprecate_file(
    "api.py",
    successor="api_v2.py",
    reason="Refactored to use async/await"
)
```

### 2. Archiving Old Code

When cleaning up old experiments:

```python
# Archive single file
registry.register_file(
    "prototype.py",
    FileStatus.ARCHIVED,
    reason="Initial prototype, no longer needed"
)

# Archive entire directory
registry.add_pattern(
    "experiments/**/*",
    FileStatus.ARCHIVED,
    reason="Old experiments"
)
```

### 3. Marking Problematic Files

When you find security issues or bugs:

```python
registry.register_file(
    "auth_old.py",
    FileStatus.PROBLEMATIC,
    reason="SQL injection vulnerability - use auth_v2.py instead"
)
```

### 4. Checking Before Use

AI assistants should check file status before accessing:

```python
path = "api.py"
status = registry.get_status(path)

if status == FileStatus.DEPRECATED:
    current = registry.get_current_version(path)
    reason = registry.get_reason(path)
    print(f"Warning: {path} is deprecated")
    print(f"Reason: {reason}")
    print(f"Use {current} instead")

elif status == FileStatus.PROBLEMATIC:
    reason = registry.get_reason(path)
    print(f"Error: {path} has issues: {reason}")
    # Don't use this file!
```

## MCP Tools Reference

### idlergear_file_register

Register a file with explicit status.

**Parameters:**
- `path` (required): File path relative to project root
- `status` (required): One of "current", "deprecated", "archived", "problematic"
- `reason` (optional): Reason for this status

**Example:**
```python
idlergear_file_register(
    path="api_v2.py",
    status="current"
)
```

### idlergear_file_deprecate

Mark a file as deprecated with optional successor.

**Parameters:**
- `path` (required): File to deprecate
- `successor` (optional): Path to current version
- `reason` (optional): Reason for deprecation

**Example:**
```python
idlergear_file_deprecate(
    path="api.py",
    successor="api_v2.py",
    reason="Refactored for async"
)
```

### idlergear_file_status

Get status of a file.

**Parameters:**
- `path` (required): File path to check

**Returns:**
- `registered`: Boolean, whether file is in registry
- `status`: File status (if registered)
- `reason`: Reason for status (if provided)
- `current_version`: Path to current version (if deprecated)
- `deprecated_at`: Timestamp when deprecated
- `replaces`: List of files this replaces
- `deprecated_versions`: List of deprecated versions of this file

**Example:**
```python
result = idlergear_file_status(path="api.py")
# {
#   "registered": true,
#   "status": "deprecated",
#   "reason": "Refactored for async",
#   "current_version": "api_v2.py",
#   "deprecated_at": "2026-01-19T10:30:00"
# }
```

### idlergear_file_list

List all registered files, optionally filtered by status.

**Parameters:**
- `status` (optional): Filter by "current", "deprecated", "archived", or "problematic"

**Returns:**
- `count`: Number of files
- `files`: Array of file entries

**Example:**
```python
result = idlergear_file_list(status="deprecated")
# {
#   "count": 3,
#   "files": [
#     {"path": "api.py", "status": "deprecated", "current_version": "api_v2.py", ...},
#     {"path": "handler_old.py", "status": "deprecated", ...},
#     ...
#   ]
# }
```

## Storage

### Location

File registry is stored in `.idlergear/file_registry.json` in your project root.

### Format

```json
{
  "files": {
    "api.py": {
      "status": "deprecated",
      "reason": "Refactored for async",
      "deprecated_at": "2026-01-19T10:30:00",
      "current_version": "api_v2.py",
      "replaces": [],
      "deprecated_versions": [],
      "metadata": {}
    },
    "api_v2.py": {
      "status": "current",
      "reason": null,
      "deprecated_at": null,
      "current_version": null,
      "replaces": ["api.py"],
      "deprecated_versions": ["api.py"],
      "metadata": {}
    }
  },
  "patterns": {
    "*.bak": {
      "status": "deprecated",
      "reason": "Backup files",
      "metadata": {}
    }
  }
}
```

### Version Control

**Recommended:** Commit `.idlergear/file_registry.json` to version control so all team members and AI assistants see the same file status.

```gitignore
# Don't ignore file registry
!.idlergear/file_registry.json
```

## Performance

The File Registry is highly optimized:

- **Status lookups**: 0.0003ms per lookup (with cache)
- **Pattern matching**: 0.0001ms per match
- **Regex caching**: Patterns compiled once, reused
- **Status caching**: Repeated lookups are instant
- **Cache invalidation**: Automatic on any modification

Benchmark results (1000 status lookups):
- Cold cache: 0.40ms total
- Warm cache: 0.32ms total
- Well below 10ms target ✓

## Best Practices

### 1. Deprecate Immediately

When creating a new version, deprecate the old one right away:

```python
# Create new version
registry.register_file("api_v2.py", FileStatus.CURRENT)

# Immediately deprecate old version
registry.deprecate_file("api.py", successor="api_v2.py")
```

### 2. Always Provide Reasons

Help future developers understand why files are deprecated:

```python
registry.deprecate_file(
    "auth.py",
    successor="auth_v2.py",
    reason="Fixed SQL injection vulnerability (CVE-2026-1234)"
)
```

### 3. Use Patterns for Common Cases

Don't register backup files individually:

```python
# Good: Use pattern
registry.add_pattern("*.bak", FileStatus.DEPRECATED, reason="Backup files")

# Bad: Register each file
registry.register_file("file1.bak", FileStatus.DEPRECATED)
registry.register_file("file2.bak", FileStatus.DEPRECATED)
# ...
```

### 4. Clean Up Periodically

Archive truly obsolete files:

```python
# Check what's deprecated
for entry in registry.list_files(FileStatus.DEPRECATED):
    age = compute_age(entry.deprecated_at)
    if age > timedelta(days=90):
        # If not referenced anywhere, archive it
        registry.register_file(entry.path, FileStatus.ARCHIVED)
```

### 5. Check Status Before Reading

AI assistants should check file status:

```python
path = "api.py"
status = registry.get_status(path)

if status in (FileStatus.DEPRECATED, FileStatus.PROBLEMATIC):
    current = registry.get_current_version(path)
    if current:
        path = current  # Use current version instead
```

## Troubleshooting

### Registry Not Found

If `.idlergear/file_registry.json` doesn't exist:

```python
# Initialize creates it on first save
registry = FileRegistry()
registry.register_file("example.py", FileStatus.CURRENT)
# Now .idlergear/file_registry.json exists
```

### Pattern Not Matching

Debug pattern matching:

```python
from idlergear.file_registry import PatternRule, FileStatus

rule = PatternRule(pattern="*.bak", status=FileStatus.DEPRECATED)
print(rule.matches("file.bak"))        # True
print(rule.matches("dir/file.bak"))    # True (no / in pattern matches anywhere)
print(rule._glob_to_regex("*.bak"))    # See regex pattern
```

### Cache Not Clearing

Cache clears automatically on modifications. If you suspect stale data:

```python
registry._clear_cache()  # Manual clear
registry.load()          # Reload from disk (clears cache)
```

## Advanced Usage

### Custom Registry Path

```python
from pathlib import Path

registry = FileRegistry(Path("/custom/path/registry.json"))
```

### Metadata

Store additional information:

```python
registry.register_file(
    "api.py",
    FileStatus.DEPRECATED,
    metadata={
        "last_used": "2026-01-15",
        "references": 3,
        "migration_guide": "docs/migration.md"
    }
)
```

### Accessing Entry Details

```python
entry = registry.get_entry("api.py")
if entry:
    print(f"Path: {entry.path}")
    print(f"Status: {entry.status.value}")
    print(f"Reason: {entry.reason}")
    print(f"Deprecated: {entry.deprecated_at}")
    print(f"Current: {entry.current_version}")
    print(f"Replaces: {entry.replaces}")
    print(f"Metadata: {entry.metadata}")
```

## Related Features

- **Watch System**: Detects stale file version references in code
- **MCP Interception**: (Coming soon) Blocks AI access to deprecated files
- **Git Integration**: (Coming soon) Tracks file renames and version chains

## See Also

- [API Reference](../api/file_registry.md)
- [Performance Benchmarks](../../tests/benchmark_file_registry.py)
- [MCP Tools Documentation](../mcp/tools.md)
