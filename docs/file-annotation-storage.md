# File Annotation Storage Architecture

## Overview

IdlerGear uses a **one-file-per-annotation** storage architecture for file annotations, providing git-friendly diffs, zero merge conflicts, and infinite scalability.

## Storage Structure

```
.idlergear/
  file_annotations/
    src/
      api/
        auth.py.json           # Annotation for src/api/auth.py
        routes.py.json
      models/
        user.py.json
    tests/
      test_api.py.json
    patterns.json              # Pattern rules (separate file)
```

## Annotation File Format

Each annotation is stored as a separate JSON file:

```json
{
  "path": "src/api/auth.py",
  "status": "current",
  "description": "REST API endpoints for user authentication",
  "tags": ["api", "auth", "jwt"],
  "components": ["AuthController", "TokenManager"],
  "related_files": ["src/models/user.py"],
  "reason": null,
  "deprecated_at": null,
  "current_version": null,
  "replaces": [],
  "deprecated_versions": [],
  "metadata": {},
  "created": "2026-02-01T20:00:00Z",
  "updated": "2026-02-01T20:00:00Z"
}
```

## Benefits

### 1. Git-Friendly Diffs

Only changed annotations appear in git diffs:

```diff
# Developer 1 annotates auth.py
+ .idlergear/file_annotations/src/api/auth.py.json

# Developer 2 annotates routes.py (different file)
+ .idlergear/file_annotations/src/api/routes.py.json

# No conflicts! ✅
```

### 2. Zero Merge Conflicts

Different files = different annotations = no conflicts:

```bash
# Developer 1 branch
git checkout feature/auth
idlergear file annotate src/api/auth.py -d "Auth endpoints"

# Developer 2 branch
git checkout feature/routes
idlergear file annotate src/api/routes.py -d "Route handlers"

# Merge both - NO CONFLICTS!
git merge feature/auth
git merge feature/routes
```

### 3. Infinite Scalability

- **Small codebases:** 10 files = 10 JSON files (~1 KB each)
- **Medium codebases:** 1,000 files = 1,000 JSON files (~100 KB total)
- **Large codebases:** 50,000 files = 50,000 JSON files (~5 MB total)

No performance degradation - only load what you need.

### 4. Selective Version Control

```bash
# Track all source file annotations
git add .idlergear/file_annotations/src/

# Ignore test file annotations
echo '.idlergear/file_annotations/tests/' >> .gitignore

# Track patterns
git add .idlergear/file_annotations/patterns.json
```

### 5. On-Demand Loading

**Old architecture (monolithic JSON):**
- Load ALL 10,000 annotations on startup
- 12.63ms for 1,000 annotations
- Required complex caching to hit <10ms target

**New architecture (one-file-per-annotation):**
- Load only annotations you access
- 0.0098ms initialization (1293x faster)
- No bulk loading needed

## Migration from Legacy Format

### Automatic Migration

IdlerGear auto-detects and migrates legacy `file_registry.json`:

```python
# First access after upgrade
registry = FileRegistry()
# Automatically migrates legacy format
# Creates backup: .idlergear/file_registry.json.backup
```

### Manual Migration

```python
from idlergear.file_annotation_storage import (
    FileAnnotationStorage,
    migrate_from_legacy
)
from pathlib import Path

# Setup storage
storage = FileAnnotationStorage(
    Path(".idlergear/file_annotations")
)

# Migrate
report = migrate_from_legacy(
    Path(".idlergear/file_registry.json"),
    storage,
    backup=True  # Creates .json.backup
)

print(f"Migrated {report['files_migrated']} files")
print(f"Migrated {report['patterns_migrated']} patterns")
```

### Migration Report

```python
{
    "success": True,
    "files_migrated": 163,
    "patterns_migrated": 2,
    "backup_path": ".idlergear/file_registry.json.backup"
}
```

## Performance Characteristics

### Lazy Loading

```python
# Registry initialization (no I/O)
registry = FileRegistry()  # 0.01ms

# First annotation access (lazy load)
entry = registry.get_annotation("src/api/auth.py")  # Load 1 file

# Subsequent access (cached)
entry = registry.get_annotation("src/api/auth.py")  # 0.001ms (cache hit)
```

### TTL-Based Caching

- **Cache TTL:** 60 seconds
- **Cache invalidation:** Automatic after writes
- **Memory usage:** Only accessed files cached

### Batch Operations

```python
# List all annotations (walks directory)
all_files = registry.list_files()  # Loads all files

# Search (loads all, filters)
results = registry.search_files(query="authentication")

# Get single annotation (loads one)
entry = registry.get_annotation("src/api/auth.py")  # Fast
```

## API Usage

### Annotate File

```python
registry.annotate_file(
    "src/api/auth.py",
    description="REST API endpoints for authentication",
    tags=["api", "auth", "jwt"],
    components=["AuthController", "TokenManager"],
    related_files=["src/models/user.py"]
)
```

**Storage:** `.idlergear/file_annotations/src/api/auth.py.json`

### Get Annotation

```python
entry = registry.get_annotation("src/api/auth.py")
# Loads from: .idlergear/file_annotations/src/api/auth.py.json

print(entry.description)
print(entry.tags)
```

### Search Annotations

```python
# Full-text search
results = registry.search_files(query="authentication")

# Tag search
results = registry.search_files(tags=["api"])

# Component search
results = registry.search_files(components=["AuthController"])
```

### Delete Annotation

```python
registry.unregister("src/api/auth.py")
# Deletes: .idlergear/file_annotations/src/api/auth.py.json
# Cleans up empty directories
```

## Patterns

Pattern rules remain in a single file for simplicity:

**Storage:** `.idlergear/file_annotations/patterns.json`

```json
{
  "*.bak": {
    "status": "deprecated",
    "reason": "Backup file",
    "metadata": {}
  },
  "*.tmp": {
    "status": "deprecated",
    "reason": "Temporary file",
    "metadata": {}
  }
}
```

## Backward Compatibility

### Reading Legacy Format

```python
# Old format detected automatically
registry = FileRegistry(Path(".idlergear/file_registry.json"))

# Auto-migrates on first access
entry = registry.get_annotation("file.py")  # Triggers migration
```

### Version Detection

```python
# Check if legacy format exists
legacy_path = Path(".idlergear/file_registry.json")
new_storage = Path(".idlergear/file_annotations")

if legacy_path.exists() and not new_storage.exists():
    print("Legacy format detected - will auto-migrate")
```

## Best Practices

### 1. Version Control Strategy

**Recommended: Track all annotations**
```bash
# .gitignore
# (Don't ignore file_annotations/)

git add .idlergear/file_annotations/
git commit -m "Add file annotations for API layer"
```

**Alternative: Track only curated annotations**
```bash
# .gitignore
.idlergear/file_annotations/tests/
.idlergear/file_annotations/build/

git add .idlergear/file_annotations/src/
git commit -m "Add curated source annotations"
```

### 2. Team Collaboration

```bash
# Developer 1: Annotate auth module
idlergear file annotate src/auth/*.py

# Developer 2: Annotate API module (parallel work)
idlergear file annotate src/api/*.py

# Merge: No conflicts!
git merge feature/auth-annotations
git merge feature/api-annotations
```

### 3. Bulk Annotation

```bash
# Annotate all Python files in src/
for file in src/**/*.py; do
  idlergear file annotate "$file" --auto
done
```

### 4. Cleanup

```bash
# Remove annotations for deleted files
idlergear file audit --cleanup-deleted
```

## Troubleshooting

### Orphaned Annotations

Files deleted but annotations remain:

```bash
# List orphaned annotations
idlergear file audit --show-orphans

# Clean up orphans
idlergear file audit --cleanup-orphans
```

### Corrupted Annotation Files

```python
# Corrupted files are skipped automatically
entry = registry.get_annotation("corrupted.py")
# Returns: None (logs warning)
```

### Migration Issues

```bash
# Check migration status
ls .idlergear/file_registry.json.backup

# Rollback migration (if needed)
mv .idlergear/file_registry.json.backup .idlergear/file_registry.json
rm -rf .idlergear/file_annotations/
```

## Implementation Details

### FileAnnotationStorage Class

```python
class FileAnnotationStorage:
    def save_annotation(self, entry: FileEntry) -> None:
        """Save annotation to individual file."""

    def load_annotation(self, file_path: str) -> Optional[FileEntry]:
        """Load annotation from file."""

    def delete_annotation(self, file_path: str) -> bool:
        """Delete annotation file."""

    def list_annotations(self) -> List[FileEntry]:
        """List all annotations (walks directory)."""

    def save_patterns(self, patterns: Dict[str, PatternRule]) -> None:
        """Save pattern rules."""

    def load_patterns(self) -> Dict[str, PatternRule]:
        """Load pattern rules."""
```

### FileRegistry Integration

```python
class FileRegistry:
    def __init__(self, registry_path=None, storage_backend=None):
        """Initialize with storage backend."""
        self.storage = storage_backend or FileAnnotationStorage(...)

    def annotate_file(self, path, ...):
        """Annotate file (saves to storage)."""
        entry = self.storage.load_annotation(path) or FileEntry(...)
        # Update annotations...
        self.storage.save_annotation(entry)

    def get_annotation(self, path):
        """Get annotation (loads from storage)."""
        return self.storage.load_annotation(path)
```

## Version History

- **v0.7.64** - Refactored to one-file-per-annotation storage
- **v0.7.63** - Fixed lazy loading persistence bug (#399)
- **v0.6.17** - Added performance optimizations (caching, lazy loading)
- **v0.6.0** - Initial file annotation feature (monolithic JSON)

## References

- Issue #399: File annotation persistence bug
- Issue #80: Refactor to one-file-per-annotation
- Issue #384: EPIC - File Annotation Strategy
- Issue #295: Performance optimizations
