# IdlerGear Knowledge Graph Schema

**Version:** 1.0
**Date:** 2026-01-18
**Technology:** Kuzu Graph Database
**Query Language:** Cypher

## Overview

This schema defines the knowledge graph structure for IdlerGear, representing relationships between tasks, code, git history, and documentation.

## Node Types

### Knowledge Nodes

#### Task
Represents actionable work items tracked in IdlerGear.

```cypher
CREATE NODE TABLE Task(
    id INT64 PRIMARY KEY,
    title STRING NOT NULL,
    body STRING,
    state STRING NOT NULL,  -- 'open', 'closed'
    priority STRING,        -- 'high', 'medium', 'low'
    labels STRING[],
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    closed_at TIMESTAMP,
    source STRING           -- 'local', 'github'
);
```

**Properties:**
- `id`: Unique task identifier
- `title`: Short description
- `body`: Detailed description (markdown)
- `state`: Current status (open/closed)
- `priority`: Importance level
- `labels`: Tags (e.g., 'bug', 'enhancement', 'tech-debt')
- `created_at`, `updated_at`, `closed_at`: Timestamps
- `source`: Backend source (local vs GitHub)

#### Note
Represents transient thoughts and ideas.

```cypher
CREATE NODE TABLE Note(
    id INT64 PRIMARY KEY,
    content STRING NOT NULL,
    tags STRING[],
    created_at TIMESTAMP,
    promoted BOOLEAN DEFAULT false
);
```

**Properties:**
- `id`: Unique note identifier
- `content`: Note text (markdown)
- `tags`: Tags like 'explore', 'idea'
- `created_at`: When note was created
- `promoted`: Whether note was promoted to task/reference

#### Reference
Represents permanent documentation.

```cypher
CREATE NODE TABLE Reference(
    id INT64 PRIMARY KEY,
    title STRING NOT NULL,
    body STRING NOT NULL,
    tags STRING[],
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    pinned BOOLEAN DEFAULT false
);
```

**Properties:**
- `id`: Unique reference identifier
- `title`: Document title
- `body`: Full documentation (markdown)
- `tags`: Categorization tags
- `pinned`: Whether reference is pinned to context

#### Plan
Represents implementation roadmaps.

```cypher
CREATE NODE TABLE Plan(
    id INT64 PRIMARY KEY,
    name STRING NOT NULL,
    title STRING,
    body STRING,
    state STRING NOT NULL,  -- 'active', 'completed', 'archived'
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Code Nodes

#### File
Represents source code files.

```cypher
CREATE NODE TABLE File(
    path STRING PRIMARY KEY,
    language STRING,
    size INT64,
    lines INT32,
    last_modified TIMESTAMP,
    exists BOOLEAN DEFAULT true
);
```

**Properties:**
- `path`: Relative file path (e.g., 'src/cli.py')
- `language`: Programming language
- `size`: File size in bytes
- `lines`: Line count
- `last_modified`: Last modification timestamp
- `exists`: Whether file currently exists

#### Symbol
Represents functions, classes, methods in code.

```cypher
CREATE NODE TABLE Symbol(
    id STRING PRIMARY KEY,  -- file:symbol_name
    name STRING NOT NULL,
    type STRING NOT NULL,   -- 'function', 'class', 'method'
    file_path STRING NOT NULL,
    line_start INT32,
    line_end INT32,
    docstring STRING
);
```

**Properties:**
- `id`: Unique identifier (file_path:symbol_name)
- `name`: Symbol name (e.g., 'GitContext', 'parse_event')
- `type`: Symbol kind (function, class, method)
- `file_path`: Containing file
- `line_start`, `line_end`: Location in file
- `docstring`: Documentation string

### Git Nodes

#### Commit
Represents git commits.

```cypher
CREATE NODE TABLE Commit(
    hash STRING PRIMARY KEY,
    short_hash STRING NOT NULL,
    message STRING NOT NULL,
    author STRING,
    timestamp TIMESTAMP,
    branch STRING
);
```

**Properties:**
- `hash`: Full commit SHA
- `short_hash`: Short SHA (7 chars)
- `message`: Commit message
- `author`: Author name/email
- `timestamp`: Commit time
- `branch`: Branch name (at time of commit)

#### Branch
Represents git branches.

```cypher
CREATE NODE TABLE Branch(
    name STRING PRIMARY KEY,
    current BOOLEAN DEFAULT false,
    head_commit STRING,
    created_at TIMESTAMP
);
```

## Relationships

### Knowledge Relationships

#### DEPENDS_ON
One task depends on another.

```cypher
CREATE REL TABLE DEPENDS_ON(
    FROM Task TO Task,
    created_at TIMESTAMP
);
```

**Example:**
```cypher
MATCH (t1:Task {title: "Phase 2"}), (t2:Task {title: "Phase 1"})
CREATE (t1)-[:DEPENDS_ON]->(t2)
```

#### BLOCKS
One task blocks another.

```cypher
CREATE REL TABLE BLOCKS(
    FROM Task TO Task,
    reason STRING
);
```

#### PROMOTED_TO_TASK
Note was promoted to a task.

```cypher
CREATE REL TABLE PROMOTED_TO_TASK(
    FROM Note TO Task,
    promoted_at TIMESTAMP
);
```

#### PROMOTED_TO_REFERENCE
Note was promoted to a reference.

```cypher
CREATE REL TABLE PROMOTED_TO_REFERENCE(
    FROM Note TO Reference,
    promoted_at TIMESTAMP
);
```

#### PART_OF_PLAN
Task is part of a plan.

```cypher
CREATE REL TABLE PART_OF_PLAN(
    FROM Task TO Plan,
    order INT32
);
```

### Code Relationships

#### MODIFIES
Task modifies a file.

```cypher
CREATE REL TABLE MODIFIES(
    FROM Task TO File,
    change_type STRING  -- 'create', 'modify', 'delete'
);
```

**Example:**
```cypher
MATCH (t:Task {id: 278}), (f:File {path: "src/idlergear/tui/enricher.py"})
CREATE (t)-[:MODIFIES {change_type: 'create'}]->(f)
```

#### CONTAINS
File contains a symbol.

```cypher
CREATE REL TABLE CONTAINS(
    FROM File TO Symbol
);
```

#### IMPORTS
File imports another file/module.

```cypher
CREATE REL TABLE IMPORTS(
    FROM File TO File,
    import_type STRING  -- 'direct', 'indirect'
);
```

#### CALLS
Symbol calls another symbol.

```cypher
CREATE REL TABLE CALLS(
    FROM Symbol TO Symbol,
    call_count INT32 DEFAULT 1
);
```

### Git Relationships

#### IMPLEMENTED_IN
Task was implemented in a commit.

```cypher
CREATE REL TABLE IMPLEMENTED_IN(
    FROM Task TO Commit
);
```

**Example:**
```cypher
// Link task #278 to commit that closed it
MATCH (t:Task {id: 278}), (c:Commit {hash: "fa041c4..."})
CREATE (t)-[:IMPLEMENTED_IN]->(c)
```

#### CHANGES
Commit changes a file.

```cypher
CREATE REL TABLE CHANGES(
    FROM Commit TO File,
    insertions INT32,
    deletions INT32,
    status STRING  -- 'added', 'modified', 'deleted', 'renamed'
);
```

#### ON_BRANCH
Commit is on a branch.

```cypher
CREATE REL TABLE ON_BRANCH(
    FROM Commit TO Branch
);
```

#### PARENT_OF
Commit parent relationship.

```cypher
CREATE REL TABLE PARENT_OF(
    FROM Commit TO Commit
);
```

### Documentation Relationships

#### DOCUMENTS
Reference documents a code element.

```cypher
CREATE REL TABLE DOCUMENTS(
    FROM Reference TO Symbol
);
```

#### DOCUMENTS_FILE
Reference documents a file.

```cypher
CREATE REL TABLE DOCUMENTS_FILE(
    FROM Reference TO File
);
```

#### RELATED_TO
General relationship for loose connections.

```cypher
CREATE REL TABLE RELATED_TO(
    FROM Task TO File,
    FROM Note TO File,
    FROM Reference TO Task,
    relationship_type STRING
);
```

## Example Queries

### Context Retrieval

#### Get all tasks for a file

```cypher
MATCH (t:Task)-[:MODIFIES]->(f:File {path: $file_path})
RETURN t.id, t.title, t.state
ORDER BY t.updated_at DESC
LIMIT 10
```

#### Find related files for a task

```cypher
MATCH (t:Task {id: $task_id})-[:MODIFIES]->(f:File)
OPTIONAL MATCH (f)-[:IMPORTS]->(imported:File)
RETURN f.path, imported.path
```

#### Get task implementation history

```cypher
MATCH (t:Task {id: $task_id})-[:IMPLEMENTED_IN]->(c:Commit)
MATCH (c)-[:CHANGES]->(f:File)
RETURN c.short_hash, c.message, c.timestamp, COLLECT(f.path) AS files
ORDER BY c.timestamp DESC
```

### Code Navigation

#### Find all symbols in a file

```cypher
MATCH (f:File {path: $file_path})-[:CONTAINS]->(s:Symbol)
RETURN s.name, s.type, s.line_start
ORDER BY s.line_start
```

#### Find where a function is called

```cypher
MATCH (caller:Symbol)-[:CALLS]->(callee:Symbol {name: $function_name})
MATCH (f:File)-[:CONTAINS]->(caller)
RETURN f.path, caller.name, caller.line_start
```

#### Get file dependencies

```cypher
MATCH (f:File {path: $file_path})-[:IMPORTS]->(dep:File)
RETURN dep.path, dep.language
```

### Knowledge Discovery

#### Find tasks without tests

```cypher
MATCH (t:Task)-[:MODIFIES]->(f:File)
WHERE f.path STARTS WITH 'src/' AND NOT EXISTS {
    MATCH (t)-[:MODIFIES]->(test:File)
    WHERE test.path STARTS WITH 'tests/'
}
RETURN t.id, t.title, f.path
```

#### Find undocumented symbols

```cypher
MATCH (s:Symbol)
WHERE s.docstring IS NULL AND NOT EXISTS {
    MATCH (r:Reference)-[:DOCUMENTS]->(s)
}
RETURN s.name, s.type, s.file_path
LIMIT 20
```

#### Find orphaned files (no task references)

```cypher
MATCH (f:File)
WHERE f.path STARTS WITH 'src/' AND NOT EXISTS {
    MATCH (t:Task)-[:MODIFIES]->(f)
}
RETURN f.path, f.last_modified
ORDER BY f.last_modified DESC
```

### Git Analysis

#### Find files changed most frequently

```cypher
MATCH (c:Commit)-[r:CHANGES]->(f:File)
RETURN f.path, COUNT(r) AS change_count
ORDER BY change_count DESC
LIMIT 10
```

#### Find commits by task

```cypher
MATCH (t:Task {id: $task_id})-[:IMPLEMENTED_IN]->(c:Commit)
RETURN c.short_hash, c.message, c.timestamp
ORDER BY c.timestamp
```

#### Find hotspot files (many commits, many tasks)

```cypher
MATCH (c:Commit)-[:CHANGES]->(f:File)
WITH f, COUNT(DISTINCT c) AS commit_count
MATCH (t:Task)-[:MODIFIES]->(f)
WITH f, commit_count, COUNT(DISTINCT t) AS task_count
WHERE commit_count > 5 OR task_count > 3
RETURN f.path, commit_count, task_count
ORDER BY commit_count + task_count DESC
```

### Plan Tracking

#### Get tasks in current plan

```cypher
MATCH (p:Plan {state: 'active'})<-[r:PART_OF_PLAN]-(t:Task)
RETURN t.id, t.title, t.state, r.order
ORDER BY r.order
```

#### Find completed tasks not in any plan

```cypher
MATCH (t:Task {state: 'closed'})
WHERE NOT EXISTS {
    MATCH (t)-[:PART_OF_PLAN]->(:Plan)
}
RETURN t.id, t.title, t.closed_at
LIMIT 20
```

## Token-Efficient Queries

For IdlerGear's `context` command, return minimal projections:

```cypher
// Minimal task context
MATCH (t:Task {state: 'open'})
RETURN t.id, t.title, t.priority
LIMIT 5

// Task with related files (compact)
MATCH (t:Task {id: $task_id})-[:MODIFIES]->(f:File)
RETURN t.title, COLLECT(f.path) AS files

// Recent activity
MATCH (c:Commit)-[:CHANGES]->(f:File)
WHERE c.timestamp > $since
RETURN c.short_hash, f.path, c.message
ORDER BY c.timestamp DESC
LIMIT 10
```

## Indexing Strategy

For performance, create indexes on frequently queried fields:

```cypher
-- Task lookups
CREATE INDEX ON Task(state);
CREATE INDEX ON Task(priority);

-- File lookups
CREATE INDEX ON File(language);
CREATE INDEX ON File(exists);

-- Git lookups
CREATE INDEX ON Commit(timestamp);
CREATE INDEX ON Commit(branch);

-- Symbol lookups
CREATE INDEX ON Symbol(file_path);
CREATE INDEX ON Symbol(type);
```

## Future Extensions

### Vector Search

Add embeddings for semantic search:

```cypher
-- Task embeddings
ALTER TABLE Task ADD COLUMN embedding FLOAT[768];

-- Semantic search
MATCH (t:Task)
WHERE vector_cosine_similarity(t.embedding, $query_embedding) > 0.8
RETURN t.id, t.title
ORDER BY vector_cosine_similarity(t.embedding, $query_embedding) DESC
LIMIT 5
```

### Full-Text Search

```cypher
-- Full-text index on task titles/bodies
CREATE FTS INDEX task_fts ON Task(title, body);

-- Search tasks
MATCH (t:Task)
WHERE fts_search(t, 'graph database')
RETURN t.id, t.title
```

## Next Steps

1. Implement schema in Kuzu
2. Build graph populator:
   - Index git commits
   - Parse Python files for symbols
   - Extract relationships from task backend
3. Add MCP tools for graph queries
4. Integrate with `idlergear context`
5. Add incremental updates on file changes
