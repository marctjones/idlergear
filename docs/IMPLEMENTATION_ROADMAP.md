# IdlerGear Code Intelligence Enhancements - Implementation Roadmap

**Status**: Ready for implementation
**Issues**: #400, #401, #402, #403
**Estimated effort**: 4-6 weeks
**Priority**: High (enables patent mining and general AI coding improvements)

---

## Summary

This document outlines the practical implementation roadmap for enhancing IdlerGear with:
1. Tree-sitter multi-language parsing (#400)
2. Vector embeddings & semantic search (#401)
3. RAG capabilities (#402)
4. Code summarization (#403)

**Total Impact**: Push token efficiency from 95-98% to 99%+ for specific tasks

---

## Phase 1: Tree-sitter Foundation (Week 1-2)

### Goal
Replace Python AST parsing with tree-sitter for robust, multi-language code indexing.

### Files to Modify
- `pyproject.toml` - Add dependencies
- `src/idlergear/graph/populators/code_populator.py` - Enhance with tree-sitter
- `src/idlergear/mcp_server.py` - Update MCP tools (if needed)

### Dependencies to Add
```toml
dependencies = [
    # ... existing ...
    "tree-sitter>=0.21.0",
    "tree-sitter-languages>=1.10.0",
]
```

### Implementation Steps

#### 1.1 Install Dependencies
```bash
cd ~/Projects/idlergear
pip install tree-sitter tree-sitter-languages
```

#### 1.2 Create Language Support Module
**File**: `src/idlergear/graph/parsers/treesitter_parser.py`

```python
"""Tree-sitter based code parser for multiple languages."""

import tree_sitter_languages
from typing import Dict, List, Any, Optional
from pathlib import Path

class TreeSitterParser:
    """Multi-language code parser using tree-sitter."""

    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".c": "c",
        ".cpp": "cpp",
        ".java": "java",
    }

    def __init__(self):
        self._parsers = {}

    def get_parser(self, language: str):
        """Get or create parser for language."""
        if language not in self._parsers:
            self._parsers[language] = tree_sitter_languages.get_parser(language)
        return self._parsers[language]

    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse file and extract symbols.

        Returns:
            {
                "symbols": [...],
                "imports": [...],
                "comments": [...],  # NEW: tree-sitter preserves comments!
            }
        """
        # Detect language from extension
        ext = file_path.suffix
        language = self.SUPPORTED_LANGUAGES.get(ext)

        if not language:
            return None  # Unsupported language

        try:
            code = file_path.read_text()
            parser = self.get_parser(language)
            tree = parser.parse(bytes(code, "utf8"))

            # Extract symbols based on language
            return self._extract_symbols(tree, code, language)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _extract_symbols(self, tree, code: str, language: str) -> Dict:
        """Extract symbols from tree-sitter parse tree."""

        if language == "python":
            return self._extract_python_symbols(tree, code)
        elif language in ("javascript", "typescript"):
            return self._extract_js_symbols(tree, code)
        elif language == "rust":
            return self._extract_rust_symbols(tree, code)
        # ... etc for other languages

        return {"symbols": [], "imports": [], "comments": []}

    def _extract_python_symbols(self, tree, code: str) -> Dict:
        """Extract Python functions, classes, methods."""
        symbols = []
        imports = []
        comments = []

        # Query for function definitions
        query = tree_sitter_languages.get_language("python").query("""
            (function_definition
                name: (identifier) @func_name) @func
        """)

        captures = query.captures(tree.root_node)

        for node, tag in captures:
            if tag == "func":
                func_name_node = [n for n, t in captures if t == "func_name"
                                 and n.start_byte >= node.start_byte
                                 and n.end_byte <= node.end_byte][0]

                symbols.append({
                    "name": code[func_name_node.start_byte:func_name_node.end_byte],
                    "type": "function",
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1,
                    "code": code[node.start_byte:node.end_byte],
                })

        # Similar queries for classes, imports, comments...

        return {
            "symbols": symbols,
            "imports": imports,
            "comments": comments,
        }

    # ... implement _extract_js_symbols, _extract_rust_symbols, etc.
```

#### 1.3 Update CodePopulator
**File**: `src/idlergear/graph/populators/code_populator.py`

Add at top:
```python
from ..parsers.treesitter_parser import TreeSitterParser
```

Replace AST parsing (line ~136):
```python
# OLD (AST):
tree = ast.parse(content, filename=str(full_path))
symbols, imports = self._extract_symbols_and_imports(tree, rel_path)

# NEW (Tree-sitter):
parser = TreeSitterParser()
result = parser.parse_file(full_path)
if result:
    symbols = result["symbols"]
    imports = result["imports"]
    comments = result.get("comments", [])  # NEW!
else:
    return None  # Couldn't parse
```

#### 1.4 Testing
```bash
# Test on IdlerGear itself
cd ~/Projects/idlergear
python -c "
from idlergear.graph import get_database
from idlergear.graph.populators.code_populator import CodePopulator

db = get_database()
populator = CodePopulator(db)
result = populator.populate_directory('src/')
print(f'Indexed: {result}')
"
```

### Acceptance Criteria
- [ ] Tree-sitter dependencies installed
- [ ] TreeSitterParser supports Python, JS, TS, Rust, Go
- [ ] CodePopulator uses tree-sitter instead of AST
- [ ] Comments preserved in symbol data
- [ ] Backward compatible (existing graph queries still work)
- [ ] Performance: <60s to index IdlerGear codebase

---

## Phase 2: Vector Embeddings & Semantic Search (Week 3-4)

### Goal
Add vector embeddings to code chunks, enable semantic search via MCP tools.

### Files to Create
- `src/idlergear/graph/embeddings/vector_store.py` - Chroma integration
- `src/idlergear/graph/embeddings/embedder.py` - Sentence transformer wrapper

### Files to Modify
- `src/idlergear/graph/populators/code_populator.py` - Add embedding generation
- `src/idlergear/mcp_server.py` - Add new MCP tools

### Dependencies to Add
```toml
dependencies = [
    # ... existing + tree-sitter ...
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
]
```

### Implementation (Simplified)

See `docs/IMPLEMENTATION_PHASE2.md` (to be created) for full details.

**Key new MCP tools**:
```python
@server.call_tool()
async def idlergear_code_search(query: str, limit: int = 10):
    """Semantic code search using natural language."""
    # Use Chroma to find similar code chunks
    pass

@server.call_tool()
async def idlergear_find_similar(code_snippet: str, limit: int = 10):
    """Find similar code to given snippet."""
    # Use vector similarity
    pass
```

---

## Phase 3: RAG Pipeline (Week 5-6)

### Goal
Full RAG implementation with 2-stage retrieval and context assembly.

### Implementation
See `docs/IMPLEMENTATION_PHASE3.md` (to be created)

**Key new MCP tools**:
```python
@server.call_tool()
async def idlergear_rag_query(question: str, max_tokens: int = 3000):
    """Ask questions, get relevant code context."""
    pass
```

---

## Phase 4: Code Summarization (Week 7-8)

### Goal
Multi-level code summaries for fast onboarding.

### Implementation
See `docs/IMPLEMENTATION_PHASE4.md` (to be created)

**Key new MCP tools**:
```python
@server.call_tool()
async def idlergear_code_summarize(level: str = "overview"):
    """Get codebase summary at different levels."""
    pass
```

---

## Quick Start (For Contributors)

### Option 1: Implement Phase 1 Only (Recommended First Step)
```bash
# 1. Install dependencies
cd ~/Projects/idlergear
pip install tree-sitter tree-sitter-languages

# 2. Create TreeSitterParser (see Phase 1.2 above)
# 3. Update CodePopulator (see Phase 1.3 above)
# 4. Test
# 5. Submit PR for Phase 1
```

### Option 2: Full Implementation
Work through all 4 phases sequentially. Each phase builds on the previous.

---

## Testing Strategy

### Unit Tests
```python
# tests/graph/test_treesitter_parser.py
def test_parse_python_file():
    parser = TreeSitterParser()
    result = parser.parse_file(Path("tests/fixtures/sample.py"))
    assert len(result["symbols"]) > 0
    assert "comments" in result  # NEW!

# tests/graph/test_semantic_search.py (Phase 2)
def test_code_search():
    # Test semantic search
    pass
```

### Integration Tests
```bash
# Test on real codebases
pytest tests/integration/test_code_intelligence.py
```

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Index 10K LOC | <60s | ~30s (AST) |
| Semantic search | <100ms | N/A |
| RAG retrieval | <1s | N/A |
| Summary generation | <30s | N/A |

---

## Migration Path

### For Existing Users
1. Upgrade IdlerGear: `pip install --upgrade idlergear`
2. Re-populate graph: `idlergear graph populate-all`
   - New: Multi-language support
   - New: Comments preserved
   - New: Vector embeddings (if Phase 2 complete)
3. Use new MCP tools (backward compatible)

### Backward Compatibility
- Existing `idlergear_graph_query_symbols` still works
- New tools supplement, don't replace
- Graph schema extended, not changed

---

## Success Metrics

- [ ] Phase 1: Tree-sitter indexing works for 5+ languages
- [ ] Phase 2: Semantic search returns relevant results (>80% accuracy)
- [ ] Phase 3: RAG retrieval <1s, 95%+ token reduction
- [ ] Phase 4: Summaries generated, 99%+ token reduction

---

## Next Steps

### Immediate (This Week)
1. **Review this roadmap** - Is phasing correct?
2. **Prioritize phases** - Can we skip any? Reorder?
3. **Assign Phase 1** - Who implements tree-sitter?

### Short Term (This Month)
1. Implement Phase 1 (tree-sitter)
2. Test on IdlerGear and Patent Mining codebases
3. Gather feedback, iterate

### Long Term (Next 2 Months)
1. Implement Phases 2-4
2. Document new MCP tools
3. Update Patent Mining to use new capabilities

---

## References

- GitHub Issues: #400-403
- Patent Mining integration: `~/Projects/patent-mining-mcp/docs/CODE_REVIEW_INTEGRATION_PLAN.md`
- Tree-sitter docs: https://tree-sitter.github.io/tree-sitter/
- Chroma docs: https://docs.trychroma.com/
- LlamaIndex docs: https://docs.llamaindex.ai/

---

**Status**: Ready for Phase 1 implementation
**Owner**: TBD
**Target**: Complete Phase 1 by [DATE]
