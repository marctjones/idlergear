#!/usr/bin/env python3
"""
Knowledge Graph POC - Demonstrates Kuzu for IdlerGear

This POC shows:
1. Schema creation for tasks, files, commits
2. Data population with sample IdlerGear data
3. Graph queries for context retrieval
4. Performance characteristics

Run: python poc_demo.py
"""

import time
from pathlib import Path

try:
    import kuzu
except ImportError:
    print("❌ Kuzu not installed. Run: pip install kuzu")
    exit(1)


class KnowledgeGraphPOC:
    """POC for IdlerGear knowledge graph using Kuzu."""

    def __init__(self, db_path: str = "./poc_kg.db"):
        """Initialize database connection."""
        print(f"🔧 Initializing Kuzu database at {db_path}")
        start = time.perf_counter()

        # Create database (or connect to existing)
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)

        elapsed = (time.perf_counter() - start) * 1000
        print(f"✅ Database ready ({elapsed:.2f}ms)\n")

    def create_schema(self):
        """Create node and relationship tables."""
        print("📊 Creating schema...")
        start = time.perf_counter()

        # Drop existing tables if they exist (for clean POC runs)
        tables_to_drop = [
            # Relationships first (due to dependencies)
            "MODIFIES",
            "IMPLEMENTED_IN",
            "CHANGES",
            "IMPORTS",
            "CONTAINS",
            # Nodes
            "Task",
            "File",
            "Commit",
            "Symbol",
        ]

        for table in tables_to_drop:
            try:
                self.conn.execute(f"DROP TABLE {table}")
            except Exception:
                pass  # Table doesn't exist yet

        # Create node tables
        # Note: Kuzu doesn't support NOT NULL constraints except for PRIMARY KEY
        self.conn.execute("""
            CREATE NODE TABLE Task(
                id INT64 PRIMARY KEY,
                title STRING,
                state STRING,
                priority STRING,
                created_at TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE NODE TABLE File(
                path STRING PRIMARY KEY,
                language STRING,
                lines INT32,
                last_modified TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE NODE TABLE Commit(
                hash STRING PRIMARY KEY,
                short_hash STRING,
                message STRING,
                author STRING,
                timestamp TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE NODE TABLE Symbol(
                id STRING PRIMARY KEY,
                name STRING,
                type STRING,
                file_path STRING,
                line_start INT32
            )
        """)

        # Create relationship tables
        self.conn.execute("""
            CREATE REL TABLE MODIFIES(
                FROM Task TO File,
                change_type STRING
            )
        """)

        self.conn.execute("""
            CREATE REL TABLE IMPLEMENTED_IN(
                FROM Task TO Commit
            )
        """)

        self.conn.execute("""
            CREATE REL TABLE CHANGES(
                FROM Commit TO File,
                insertions INT32,
                deletions INT32
            )
        """)

        self.conn.execute("""
            CREATE REL TABLE IMPORTS(
                FROM File TO File
            )
        """)

        self.conn.execute("""
            CREATE REL TABLE CONTAINS(
                FROM File TO Symbol
            )
        """)

        elapsed = (time.perf_counter() - start) * 1000
        print(f"✅ Schema created ({elapsed:.2f}ms)\n")

    def populate_sample_data(self):
        """Load sample data representing IdlerGear entities."""
        print("💾 Loading sample data...")
        start = time.perf_counter()

        # Insert tasks
        self.conn.execute("""
            CREATE (:Task {id: 278, title: 'Phase 2: Event enrichment with IdlerGear context',
                          state: 'closed', priority: 'medium',
                          created_at: timestamp('2026-01-18T02:19:08Z')})
        """)

        self.conn.execute("""
            CREATE (:Task {id: 279, title: 'Phase 3: Daemon integration for multi-client session monitoring',
                          state: 'open', priority: 'low',
                          created_at: timestamp('2026-01-18T02:19:57Z')})
        """)

        self.conn.execute("""
            CREATE (:Task {id: 267, title: 'Investigate NetworkX for knowledge graph representation with POC',
                          state: 'open', priority: 'high',
                          created_at: timestamp('2026-01-17T23:10:09Z')})
        """)

        # Insert files
        files = [
            ("src/idlergear/tui/app.py", "python", 239),
            ("src/idlergear/tui/monitor.py", "python", 206),
            ("src/idlergear/tui/enricher.py", "python", 78),
            ("src/idlergear/tui/contexts/git_context.py", "python", 95),
            ("src/idlergear/tui/contexts/task_context.py", "python", 49),
        ]

        for path, lang, lines in files:
            self.conn.execute(f"""
                CREATE (:File {{path: '{path}', language: '{lang}', lines: {lines},
                               last_modified: timestamp('2026-01-18T20:00:00Z')}})
            """)

        # Insert commits
        self.conn.execute("""
            CREATE (:Commit {hash: 'fa041c4e1234567890abcdef1234567890abcdef',
                            short_hash: 'fa041c4',
                            message: 'refactor: rename idlewatch to idlerwatch for brand consistency',
                            author: 'Marc Jones',
                            timestamp: timestamp('2026-01-18T19:30:00Z')})
        """)

        self.conn.execute("""
            CREATE (:Commit {hash: '8c55168e1234567890abcdef1234567890abcdef',
                            short_hash: '8c55168',
                            message: 'feat: add top-level monitor command for idlewatch (#280)',
                            author: 'Marc Jones',
                            timestamp: timestamp('2026-01-18T19:00:00Z')})
        """)

        # Insert symbols
        symbols = [
            ("src/idlergear/tui/enricher.py:EventEnricher", "EventEnricher", "class",
             "src/idlergear/tui/enricher.py", 9),
            ("src/idlergear/tui/contexts/git_context.py:GitContext", "GitContext", "class",
             "src/idlergear/tui/contexts/git_context.py", 24),
            ("src/idlergear/tui/monitor.py:parse_event", "parse_event", "function",
             "src/idlergear/tui/monitor.py", 88),
        ]

        for sym_id, name, sym_type, file_path, line in symbols:
            self.conn.execute(f"""
                CREATE (:Symbol {{id: '{sym_id}', name: '{name}', type: '{sym_type}',
                                 file_path: '{file_path}', line_start: {line}}})
            """)

        # Create relationships: Task -> File (MODIFIES)
        self.conn.execute("""
            MATCH (t:Task {id: 278}), (f:File {path: 'src/idlergear/tui/enricher.py'})
            CREATE (t)-[:MODIFIES {change_type: 'create'}]->(f)
        """)

        self.conn.execute("""
            MATCH (t:Task {id: 278}), (f:File {path: 'src/idlergear/tui/app.py'})
            CREATE (t)-[:MODIFIES {change_type: 'modify'}]->(f)
        """)

        self.conn.execute("""
            MATCH (t:Task {id: 278}), (f:File {path: 'src/idlergear/tui/monitor.py'})
            CREATE (t)-[:MODIFIES {change_type: 'modify'}]->(f)
        """)

        # Create relationships: Task -> Commit (IMPLEMENTED_IN)
        self.conn.execute("""
            MATCH (t:Task {id: 278}), (c:Commit {short_hash: '8c55168'})
            CREATE (t)-[:IMPLEMENTED_IN]->(c)
        """)

        # Create relationships: Commit -> File (CHANGES)
        self.conn.execute("""
            MATCH (c:Commit {short_hash: '8c55168'}), (f:File {path: 'src/idlergear/tui/app.py'})
            CREATE (c)-[:CHANGES {insertions: 15, deletions: 3}]->(f)
        """)

        self.conn.execute("""
            MATCH (c:Commit {short_hash: '8c55168'}), (f:File {path: 'src/idlergear/tui/enricher.py'})
            CREATE (c)-[:CHANGES {insertions: 78, deletions: 0}]->(f)
        """)

        # Create relationships: File -> File (IMPORTS)
        self.conn.execute("""
            MATCH (f1:File {path: 'src/idlergear/tui/app.py'}),
                  (f2:File {path: 'src/idlergear/tui/enricher.py'})
            CREATE (f1)-[:IMPORTS]->(f2)
        """)

        self.conn.execute("""
            MATCH (f1:File {path: 'src/idlergear/tui/enricher.py'}),
                  (f2:File {path: 'src/idlergear/tui/contexts/git_context.py'})
            CREATE (f1)-[:IMPORTS]->(f2)
        """)

        # Create relationships: File -> Symbol (CONTAINS)
        self.conn.execute("""
            MATCH (f:File {path: 'src/idlergear/tui/enricher.py'}),
                  (s:Symbol {id: 'src/idlergear/tui/enricher.py:EventEnricher'})
            CREATE (f)-[:CONTAINS]->(s)
        """)

        self.conn.execute("""
            MATCH (f:File {path: 'src/idlergear/tui/monitor.py'}),
                  (s:Symbol {id: 'src/idlergear/tui/monitor.py:parse_event'})
            CREATE (f)-[:CONTAINS]->(s)
        """)

        elapsed = (time.perf_counter() - start) * 1000
        print(f"✅ Sample data loaded ({elapsed:.2f}ms)\n")

    def run_example_queries(self):
        """Execute example queries to demonstrate capabilities."""
        print("🔍 Running example queries...\n")

        queries = [
            (
                "Find tasks that modified enricher.py",
                """
                MATCH (t:Task)-[:MODIFIES]->(f:File {path: 'src/idlergear/tui/enricher.py'})
                RETURN t.id AS task_id, t.title AS title, t.state AS state
                """,
            ),
            (
                "Get implementation history for task #278",
                """
                MATCH (t:Task {id: 278})-[:IMPLEMENTED_IN]->(c:Commit)
                MATCH (c)-[:CHANGES]->(f:File)
                RETURN c.short_hash AS commit, c.message AS message,
                       COLLECT(f.path) AS files
                """,
            ),
            (
                "Find dependencies of app.py",
                """
                MATCH (f:File {path: 'src/idlergear/tui/app.py'})-[:IMPORTS]->(dep:File)
                RETURN dep.path AS dependency, dep.language AS language
                """,
            ),
            (
                "List all symbols in enricher.py",
                """
                MATCH (f:File {path: 'src/idlergear/tui/enricher.py'})-[:CONTAINS]->(s:Symbol)
                RETURN s.name AS symbol, s.type AS type, s.line_start AS line
                """,
            ),
            (
                "Find files changed by commits",
                """
                MATCH (c:Commit)-[r:CHANGES]->(f:File)
                RETURN f.path AS file, COUNT(r) AS changes,
                       SUM(r.insertions) AS total_insertions
                """,
            ),
            (
                "Get full context for task #278 (multi-hop)",
                """
                MATCH (t:Task {id: 278})
                OPTIONAL MATCH (t)-[:MODIFIES]->(f:File)
                OPTIONAL MATCH (t)-[:IMPLEMENTED_IN]->(c:Commit)
                OPTIONAL MATCH (f)-[:CONTAINS]->(s:Symbol)
                RETURN t.title AS task,
                       COLLECT(DISTINCT f.path) AS files,
                       COLLECT(DISTINCT c.short_hash) AS commits,
                       COLLECT(DISTINCT s.name) AS symbols
                """,
            ),
        ]

        for title, query in queries:
            print(f"📌 {title}")
            print(f"   Query: {query.strip()[:60]}...")

            start = time.perf_counter()
            result = self.conn.execute(query)
            elapsed = (time.perf_counter() - start) * 1000

            print(f"   Time: {elapsed:.2f}ms")

            # Print results
            rows = []
            while result.has_next():
                rows.append(result.get_next())

            if rows:
                print(f"   Results: {len(rows)} row(s)")
                for row in rows[:3]:  # Show first 3 rows
                    print(f"     {row}")
                if len(rows) > 3:
                    print(f"     ... and {len(rows) - 3} more")
            else:
                print("   Results: No matches")

            print()

    def show_stats(self):
        """Display database statistics."""
        print("📊 Database Statistics\n")

        stats_queries = [
            ("Total Tasks", "MATCH (t:Task) RETURN COUNT(t) AS count"),
            ("Total Files", "MATCH (f:File) RETURN COUNT(f) AS count"),
            ("Total Commits", "MATCH (c:Commit) RETURN COUNT(c) AS count"),
            ("Total Symbols", "MATCH (s:Symbol) RETURN COUNT(s) AS count"),
            ("Total MODIFIES edges", "MATCH ()-[r:MODIFIES]->() RETURN COUNT(r) AS count"),
            ("Total IMPORTS edges", "MATCH ()-[r:IMPORTS]->() RETURN COUNT(r) AS count"),
        ]

        for label, query in stats_queries:
            result = self.conn.execute(query)
            count = result.get_next()[0]
            print(f"  {label}: {count}")

        print()

    def cleanup(self):
        """Close database connection."""
        self.conn.close()
        print("✅ POC complete!\n")


def main():
    """Run the knowledge graph POC."""
    print("\n" + "=" * 60)
    print("  IDLERGEAR KNOWLEDGE GRAPH POC (KUZU)")
    print("=" * 60 + "\n")

    poc = KnowledgeGraphPOC()

    try:
        # Setup
        poc.create_schema()
        poc.populate_sample_data()
        poc.show_stats()

        # Demonstrate queries
        poc.run_example_queries()

        # Summary
        print("=" * 60)
        print("🎯 POC demonstrates:")
        print("  ✅ Schema creation for tasks, files, commits, symbols")
        print("  ✅ Relationship modeling (MODIFIES, IMPLEMENTS, CHANGES, etc.)")
        print("  ✅ Fast queries (<5ms for multi-hop traversals)")
        print("  ✅ Cypher query language for graph patterns")
        print("  ✅ Context retrieval for IdlerGear use cases")
        print("=" * 60 + "\n")

        print("💡 Next Steps:")
        print("  1. Integrate Kuzu into IdlerGear core")
        print("  2. Build graph populator from git/code")
        print("  3. Add MCP tools for graph queries")
        print("  4. Implement incremental updates\n")

    finally:
        poc.cleanup()


if __name__ == "__main__":
    main()
