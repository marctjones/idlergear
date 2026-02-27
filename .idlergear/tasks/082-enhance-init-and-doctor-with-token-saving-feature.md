---
id: 82
title: Enhance init and doctor with token-saving feature checks
state: open
created: '2026-02-13T23:56:02.784516Z'
accessed: '2026-02-13T23:58:26.580181Z'
access_count: 1
relevance_score: 1.0
labels:
- enhancement
priority: high
---
# Enhance init and doctor commands with token-saving feature checks

## Problem

Users miss out on 95-98% token savings because initialization doesn't:
- Create file_annotations directory (93% token savings lost)
- Populate knowledge graph (95-98% token savings lost)
- Check/report on token-saving features

Current `idlergear doctor` checks installation health but doesn't check the features that provide the most value.

## Solution

### Phase 1: Enhance `idlergear doctor` (HIGH PRIORITY)

Add health checks for token-saving features:

**New checks:**
```python
def check_file_annotations() -> HealthCheck:
    """Check if file_annotations directory exists"""
    dir_path = schema.idlergear_dir / "file_annotations"
    
    if dir_path.exists():
        count = len(list(dir_path.glob("**/*.json")))
        return HealthCheck(
            name="file_annotations",
            status="ok",
            message=f"File annotations ready ({count} files)",
            impact="Enables 93% token savings",
        )
    else:
        return HealthCheck(
            name="file_annotations",
            status="error",
            message="File annotations directory missing",
            fix="mkdir -p .idlergear/file_annotations",
            impact="Missing 93% token savings",
        )

def check_knowledge_graph() -> HealthCheck:
    """Check knowledge graph status"""
    graph_db = Path.home() / ".idlergear" / "graph.db"
    
    if not graph_db.exists():
        return HealthCheck(
            name="knowledge_graph",
            status="error",
            message="Knowledge graph not initialized",
            fix="idlergear graph populate",
            impact="Missing 95-98% token savings",
        )
    
    size_mb = graph_db.stat().st_size / (1024 * 1024)
    return HealthCheck(
        name="knowledge_graph",
        status="ok",
        message=f"Knowledge graph populated ({size_mb:.0f} MB)",
        impact="Enables 95-98% token savings",
    )

def check_rag_index() -> HealthCheck:
    """Check RAG index status"""
    # Check if rag extras installed
    # Check if index exists
    # Return status with token savings impact
```

**Enhanced output:**
```bash
$ idlergear doctor -v

⚡ Token-Saving Features
  ❌ File annotations: Directory missing
      Impact: Missing 93% token savings
      Fix: mkdir -p .idlergear/file_annotations
      
  ✅ Knowledge graph: Populated (2,003 nodes, 172 MB)
      Impact: Enables 95-98% token savings ✨
      
  ⚠️  RAG index: Not installed (optional)
      Impact: Missing 90%+ token savings

📊 Total Token Savings: 95% active, 5% missing
```

### Phase 2: Enhance `idlergear init` (MEDIUM PRIORITY)

**Always create file_annotations directory:**
```python
def init_project(path: str = ".") -> None:
    # ... existing code ...
    
    # NEW: Always create file_annotations
    file_annotations_dir = schema.idlergear_dir / "file_annotations"
    file_annotations_dir.mkdir(exist_ok=True)
    
    # NEW: Offer to populate graph (interactive)
    if not skip_interactive:
        if typer.confirm(
            "\nPopulate knowledge graph? (Enables 95-98% token savings)",
            default=True
        ):
            from idlergear.graph import populate_all
            populate_all(max_commits=100, incremental=True)
    
    # NEW: Show initialization summary
    show_init_summary(schema)
```

**Example output:**
```bash
$ idlergear init

✅ Created .idlergear/ directory structure
✅ Created config.toml
✅ Created file_annotations/ (93% token savings enabled!)

Populate knowledge graph? (Enables 95-98% token savings) [Y/n]: y

⏳ Populating knowledge graph...
   Indexing commits: 100 ████████████ 100%
   Parsing symbols: 247 files ████████████ 100%
   
✅ Knowledge graph ready!

📊 INITIALIZATION SUMMARY:
   ✅ File annotations ready (93% savings)
   ✅ Knowledge graph ready (95-98% savings)
   ⏭️  RAG: Optional (install: pip install 'idlergear[rag]')
   
   Total token savings enabled: 95-98%! ✨
```

### Phase 3: Make `doctor --fix` handle new checks

Existing `--fix` flag should fix the new checks:
- Create file_annotations directory if missing
- Offer to populate/update knowledge graph
- Show how to install RAG

## Implementation

**Files to modify:**
- `src/idlergear/doctor.py` - Add new health checks
- `src/idlergear/init.py` - Create file_annotations, offer graph populate
- `src/idlergear/health_checks.py` (new?) - Reusable check functions

**Effort:** 3-4 hours total
- Phase 1 (doctor): 2-3 hours
- Phase 2 (init): 1 hour
- Phase 3 (fix): 30 minutes (reuse existing logic)

## Success Criteria

- ✅ `doctor` reports file_annotations status with token savings impact
- ✅ `doctor` reports knowledge graph status with node count
- ✅ `doctor` reports RAG status (optional)
- ✅ `doctor` shows total token savings enabled
- ✅ `init` always creates file_annotations directory
- ✅ `init` offers to populate knowledge graph
- ✅ `init` shows token savings summary at end
- ✅ `doctor --fix` creates missing directories
- ✅ `doctor --fix` offers to populate/update graph

## Impact

**User onboarding:**
- New users get full token savings setup automatically
- Clear visibility into which features are enabled
- Understand the value (95-98% token savings)

**Existing users:**
- `doctor` shows what they're missing
- Easy fix with `--fix` flag
- Awareness of token-saving features

**Adoption:**
- Reduces "why is this slow?" questions
- Makes high-value features discoverable
- Better first-run experience
