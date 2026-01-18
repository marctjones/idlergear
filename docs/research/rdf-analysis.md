# RDF for IdlerGear: Analysis and Recommendations

**Date:** 2026-01-18
**Context:** Following Kuzu recommendation for knowledge graph
**Question:** Should we also use RDF? How would we use it?

## Executive Summary

**Recommendation:** **No, do not use RDF as primary storage.** Use Kuzu property graph as planned.

**However:** Consider **RDFLib for export/import** capabilities in a future release (v0.7.0+) to enable:
- Data portability and interoperability
- Integration with semantic web tools
- Standard knowledge exchange format

## What is RDF?

**RDF (Resource Description Framework)** is a W3C standard for representing information as triples:
- **Subject** - The resource being described
- **Predicate** - The property or relationship
- **Object** - The value or related resource

**Example RDF Triple:**
```turtle
<Task#278> <modifies> <src/idlergear/tui/enricher.py> .
```

**Query Language:** SPARQL (instead of Cypher for property graphs)

## RDF vs Property Graphs: Key Differences

| Aspect | RDF Triples | Property Graphs (Kuzu) |
|--------|-------------|------------------------|
| **Data Model** | Subject-Predicate-Object | Nodes + Relationships with properties |
| **Standards** | W3C standard (RDF, SPARQL, OWL) | ISO GQL, Cypher (most common) |
| **Primary Use** | Data integration, semantic web | Application performance, traversal |
| **Relationships** | Can't have properties | Can have rich properties |
| **Multiple Edges** | Limited (same type between nodes) | Fully supported with distinct IDs |
| **Performance** | Logarithmic edge traversal cost | Optimized for fast traversal |
| **Reasoning** | Strong (OWL, RDFS) | Limited (pattern matching) |
| **Interoperability** | Excellent (global URIs) | Good (app-specific) |
| **Developer UX** | More complex, semantic focus | Simpler, application focus |
| **Query Language** | SPARQL (semantic queries) | Cypher (pattern matching) |

**Sources:**
- [RDF vs Property Graphs | Neo4j](https://neo4j.com/blog/knowledge-graph/rdf-vs-property-graphs-knowledge-graphs/)
- [Property Graph vs RDF | PuppyGraph](https://www.puppygraph.com/blog/property-graph-vs-rdf)
- [Which Knowledge Graph? | Wisecube AI](https://www.wisecube.ai/blog/knowledge-graphs-rdf-or-property-graphs-which-one-should-you-pick/)

## When to Use Each

### Choose RDF When:

✅ **Data Integration & Interoperability**
- Combining data from multiple external sources
- Need global identifiers (URIs) for resources
- Sharing knowledge graphs across organizations

✅ **Semantic Reasoning**
- Inferring new knowledge from existing facts
- Using ontologies (OWL, RDFS)
- Building taxonomies and hierarchies

✅ **Standards Compliance**
- Semantic web applications
- Linked Open Data projects
- Academic/research contexts

✅ **Open-World Semantics**
- Missing data doesn't mean false
- Incremental knowledge addition

### Choose Property Graphs When:

✅ **Performance-Critical Applications**
- Fast graph traversals (shortest path, degrees of separation)
- Real-time recommendations
- Fraud detection

✅ **Rich Relationship Modeling**
- Relationships need properties (timestamps, weights, metadata)
- Multiple relationships of same type between nodes
- Complex application-specific models

✅ **Developer Experience**
- Quick setup and development
- Pattern-based queries (Cypher)
- Application-first design

✅ **Scalability**
- Large-scale graph analytics
- High-velocity transactional workloads

**Source:** [RDF vs Property Graphs | Milvus](https://milvus.io/ai-quick-reference/what-is-the-difference-between-rdf-and-property-graphs)

## IdlerGear's Requirements Analysis

Let's evaluate IdlerGear against these criteria:

| Requirement | RDF Fit | Property Graph Fit | Winner |
|-------------|---------|-------------------|--------|
| **Fast context retrieval** (<100ms) | ⚠️ Slower | ✅ Optimized | Property Graph |
| **Rich task/commit relationships** | ❌ Limited | ✅ Full support | Property Graph |
| **Application-specific modeling** | ⚠️ Complex | ✅ Simple | Property Graph |
| **Performance at scale** | ⚠️ Logarithmic | ✅ Optimized | Property Graph |
| **Embedded architecture** | ❌ Rare | ✅ Kuzu | Property Graph |
| **Developer experience** | ⚠️ Learning curve | ✅ Cypher | Property Graph |
| **Query pattern matching** | ⚠️ SPARQL | ✅ Cypher | Property Graph |
| **External data integration** | ✅ Excellent | ⚠️ Limited | RDF |
| **Standard export format** | ✅ RDF/XML, Turtle | ⚠️ Custom | RDF |
| **Semantic reasoning** | ✅ OWL/RDFS | ❌ No | RDF |

**Conclusion:** Property graphs (Kuzu) win for IdlerGear's core use case.

## RDF Libraries for Python

If we were to use RDF, here are the main options:

### 1. RDFLib (Recommended)

**[RDFLib](https://github.com/RDFLib/rdflib)** - Pure Python RDF library

**Pros:**
- ✅ Mature and stable (most widely used)
- ✅ Comprehensive format support (RDF/XML, Turtle, N-Triples, JSON-LD, etc.)
- ✅ Built-in SPARQL 1.1 support
- ✅ Multiple storage backends (memory, BerkeleyDB, remote endpoints)
- ✅ Well documented
- ✅ Active community

**Cons:**
- ⚠️ Pure Python (slower than native implementations)
- ⚠️ Not optimized for large graphs

**Installation:**
```bash
pip install rdflib
```

**Example:**
```python
from rdflib import Graph, Namespace, URIRef, Literal

g = Graph()
IG = Namespace("http://idlergear.dev/")

# Add triple
g.add((IG.Task278, IG.modifies, IG["src/tui/enricher.py"]))

# Query with SPARQL
results = g.query("""
    SELECT ?task ?file
    WHERE {
        ?task ig:modifies ?file .
    }
""")
```

**Sources:**
- [RDFLib Documentation](https://rdflib.readthedocs.io/)
- [RDFLib GitHub](https://github.com/RDFLib/rdflib)
- [RDFLib on PyPI](https://pypi.org/project/rdflib/)

### 2. Oxigraph (Fast but Unstable)

**[Oxigraph](https://github.com/oxigraph/oxigraph)** - Rust-based RDF database with Python bindings

**Pros:**
- ✅ Significantly faster than RDFLib (20-30x for SPARQL queries)
- ✅ Written in Rust (performance + safety)
- ✅ Can be used as RDFLib store backend (oxrdflib)
- ✅ SPARQL 1.1 support

**Cons:**
- ❌ Not stable yet (storage format may change)
- ⚠️ Rust/Python conversion overhead for simple operations
- ⚠️ Less mature than RDFLib

**Installation:**
```bash
pip install pyoxigraph
# Or as RDFLib backend:
pip install oxrdflib
```

**Performance (from benchmarks):**
- SPARQL query: 752ms (RDFLib) → 20ms (Oxigraph) = **37x faster**
- Parsing: 59ms → 20ms = **3x faster**
- Serialization: 58ms → 6ms = **10x faster**

**Source:** [Oxigraph Performance Discussion](https://github.com/oxigraph/oxigraph/discussions/1092)

### 3. kuzu-rdflib (Kuzu + RDF Integration)

**[kuzu-rdflib](https://github.com/DerwenAI/kuzu-rdflib)** - RDFLib store plugin for Kuzu

**Pros:**
- ✅ Combines RDFLib API with Kuzu storage
- ✅ Query via SPARQL (RDFLib) or Cypher (Kuzu)
- ✅ Leverages Kuzu's performance

**Cons:**
- ⚠️ Third-party project (not official Kuzu)
- ⚠️ Experimental

**Note:** Kuzu's native RDFGraphs support was removed in v0.7.0, planned to return as extension.

**Source:** [Kuzu RDFGraphs Issue](https://github.com/kuzudb/kuzu/issues/1570)

## Kuzu's RDF Support Status

### Current State (v0.11.3):
- ❌ **RDFGraphs temporarily removed** in v0.7.0
- Reason: Previous implementation not scalable/maintainable
- Plan: Re-implement as optional extension (avoid bloating core binary)

### Future Vision:
- ✅ Kuzu team supports "property graphs + RDF" vision
- ✅ Considering RDF* (RDF-Star) support
- ✅ Will likely return as extension

**Sources:**
- [Kuzu RDFGraphs Support Issue](https://github.com/kuzudb/kuzu/issues/1570)
- [In Praise of RDF | Kuzu Blog](https://blog.kuzudb.com/post/in-praise-of-rdf/)
- [Validating RDF with SHACL in Kuzu](https://kuzudb.github.io/blog/post/rdf-shacl-and-kuzu/)

## Emerging: RDF* (RDF-Star)

**RDF*** extends RDF to include properties on relationships (like property graphs):

```turtle
# Standard RDF (can't add properties to relationship)
:Task278 :modifies :enricher.py .

# RDF* (can add properties!)
<< :Task278 :modifies :enricher.py >> :timestamp "2026-01-18"^^xsd:date .
```

This **bridges the gap** between RDF and property graphs!

**Status:** Emerging standard, not yet widely adopted.

**Source:** [RDF* Ending the Debate | AI Business](https://aibusiness.com/data/ending-the-rdf-vs-property-graph-debate-with-rdf-)

## Recommendations for IdlerGear

### Primary Storage: Kuzu Property Graph ✅

**Use Kuzu as planned** because:
1. ✅ Performance requirements (sub-100ms context retrieval)
2. ✅ Rich relationship properties (commit metadata, task priority, etc.)
3. ✅ Application-specific modeling
4. ✅ Developer-friendly Cypher queries
5. ✅ Embedded architecture (no server)
6. ✅ Proven in POC (<40ms multi-hop queries)

### Optional Future: RDFLib for Export/Import

**Consider adding RDFLib in v0.7.0+** for:

#### 1. **Data Portability**
```python
# Export IdlerGear knowledge to RDF
def export_to_rdf(graph_db, output_path):
    g = Graph()
    IG = Namespace("http://idlergear.dev/")

    # Convert Kuzu graph to RDF triples
    result = graph_db.execute("MATCH (t:Task)-[r:MODIFIES]->(f:File) RETURN t, r, f")
    for task, rel, file in result:
        g.add((IG[f"Task{task.id}"], IG.modifies, IG[file.path]))

    # Export to standard format
    g.serialize(output_path, format="turtle")
```

#### 2. **Interoperability**
- Share knowledge graphs with external tools
- Import from semantic web sources
- Integrate with academic research tools

#### 3. **Standard Exchange**
```turtle
# knowledge-export.ttl
@prefix ig: <http://idlergear.dev/> .
@prefix schema: <http://schema.org/> .

ig:Task278 a schema:Task ;
    schema:name "Phase 2: Event enrichment" ;
    schema:status "closed" ;
    ig:modifies ig:File_enricher_py .

ig:File_enricher_py a schema:SoftwareSourceCode ;
    schema:programmingLanguage "Python" ;
    schema:codeRepository "https://github.com/marctjones/idlergear" .
```

#### 4. **Use Cases**
- Export task knowledge for analysis in external tools
- Import project data from GitHub/GitLab APIs
- Share research findings in standard format
- Integration with LLM knowledge bases (many use RDF)

**Implementation:**
```python
# src/idlergear/export.py
from rdflib import Graph, Namespace

class RDFExporter:
    """Export IdlerGear knowledge graph to RDF."""

    def export_tasks(self, output_file: str, format: str = "turtle"):
        """Export all tasks to RDF."""
        g = Graph()
        IG = Namespace("http://idlergear.dev/")

        # Query Kuzu, convert to RDF
        tasks = self.kuzu_conn.execute("MATCH (t:Task) RETURN t")
        for task in tasks:
            task_uri = IG[f"Task{task.id}"]
            g.add((task_uri, IG.title, Literal(task.title)))
            g.add((task_uri, IG.state, Literal(task.state)))

        g.serialize(output_file, format=format)
```

### What NOT to Do

❌ **Don't replace Kuzu with RDF triple store**
- Performance regression
- Lose relationship properties
- More complex queries
- Worse developer experience

❌ **Don't use RDF for primary storage**
- Not optimized for our use case
- Slower graph traversals
- No embedded options as good as Kuzu

❌ **Don't implement both in parallel**
- Unnecessary complexity
- Data synchronization burden
- Pick one, add export later

## Implementation Timeline

### v0.6.0 (Next)
- ✅ Implement Kuzu property graph (as planned)
- ✅ Build graph populator
- ✅ Add MCP tools for queries
- ❌ No RDF yet

### v0.7.0+ (Future)
- ⏳ Consider adding RDFLib for export
- ⏳ Implement `idlergear export --format rdf`
- ⏳ Support Turtle, JSON-LD, RDF/XML formats
- ⏳ Optional: Import from RDF sources

### v0.8.0+ (Later)
- ⏳ Watch Kuzu RDFGraphs extension
- ⏳ Consider dual-query support (Cypher + SPARQL)
- ⏳ Evaluate RDF* when stable

## Conclusion

**Answer:** No, don't use RDF as primary storage for IdlerGear.

**But yes**, consider RDFLib for **export/import capabilities** in a future release to enable:
- Data portability (standard formats)
- Interoperability with semantic web tools
- Knowledge sharing across platforms
- Integration with LLM knowledge bases

**Priority:** Low (after v0.6.0 core implementation)

**Effort:** Low (~1-2 days for basic export)

**Value:** Medium (nice-to-have for power users, not essential)

## References

### RDF vs Property Graphs
- [RDF vs Property Graphs | Neo4j](https://neo4j.com/blog/knowledge-graph/rdf-vs-property-graphs-knowledge-graphs/)
- [Property Graph vs RDF | PuppyGraph](https://www.puppygraph.com/blog/property-graph-vs-rdf)
- [Which Knowledge Graph? | Wisecube AI](https://www.wisecube.ai/blog/knowledge-graphs-rdf-or-property-graphs-which-one-should-you-pick/)
- [RDF vs Property Graphs | Ontotext](https://www.ontotext.com/knowledgehub/fundamentals/rdf-vs-property-graphs/)
- [Milvus: RDF Differences](https://milvus.io/ai-quick-reference/what-is-the-difference-between-rdf-and-property-graphs)

### RDF Libraries
- [RDFLib Documentation](https://rdflib.readthedocs.io/)
- [RDFLib GitHub](https://github.com/RDFLib/rdflib)
- [Oxigraph GitHub](https://github.com/oxigraph/oxigraph)
- [Oxigraph Performance](https://github.com/oxigraph/oxigraph/discussions/1092)
- [kuzu-rdflib Integration](https://github.com/DerwenAI/kuzu-rdflib)

### Kuzu RDF Support
- [Kuzu RDFGraphs Issue](https://github.com/kuzudb/kuzu/issues/1570)
- [In Praise of RDF | Kuzu](https://blog.kuzudb.com/post/in-praise-of-rdf/)
- [Validating RDF in Kuzu](https://kuzudb.github.io/blog/post/rdf-shacl-and-kuzu/)

### RDF*
- [RDF* Ending the Debate | AI Business](https://aibusiness.com/data/ending-the-rdf-vs-property-graph-debate-with-rdf-)
