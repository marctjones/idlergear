# Recommended Tools for LLM Coding Assistants

**Tools to enhance LLM coding assistant effectiveness through better context and information access.**

---

## Table of Contents

1. [Knowledge & Documentation Tools](#knowledge--documentation-tools)
2. [Code Discovery & Examples](#code-discovery--examples)
3. [API & Service Integration](#api--service-integration)
4. [Security & Compliance](#security--compliance)
5. [Performance & Debugging](#performance--debugging)
6. [Database & Data Tools](#database--data-tools)
7. [Visualization & Diagrams](#visualization--diagrams)
8. [Collaboration & Communication](#collaboration--communication)
9. [Implementation Guide](#implementation-guide)

---

## Knowledge & Documentation Tools

### 1. Web Search (Technical Content)

**Purpose:** Access current technical information, papers, and documentation

**Sources to integrate:**

#### arXiv (Academic Papers)
```python
# MCP Tool: search_arxiv
search_arxiv(
    query="transformer architecture optimization",
    category="cs.LG",  # Machine Learning
    max_results=5
)

# Returns:
# - Paper titles
# - Authors
# - Abstracts
# - PDF URLs
# - Publication dates
```

**Use cases:**
- Latest research on algorithms
- Understanding cutting-edge techniques
- Implementing recent papers
- Citation for technical decisions

#### Wikipedia (Technical Concepts)
```python
# MCP Tool: wikipedia_lookup
wikipedia_lookup(
    topic="Byzantine fault tolerance",
    summary_length="medium"
)

# Returns:
# - Summary of concept
# - Key points
# - Related topics
# - References
```

**Use cases:**
- Quick technical concept explanations
- Algorithm background
- Historical context
- Terminology clarification

#### Stack Overflow
```python
# MCP Tool: search_stackoverflow
search_stackoverflow(
    query="python asyncio performance",
    tags=["python", "asyncio"],
    sort="votes"
)

# Returns:
# - Top voted answers
# - Code snippets
# - Community solutions
# - Common pitfalls
```

**Use cases:**
- Common error solutions
- Best practices from community
- Code examples
- Edge cases and gotchas

#### Official Documentation
```python
# MCP Tool: fetch_docs
fetch_docs(
    library="pandas",
    function="DataFrame.merge",
    version="2.0"
)

# Returns:
# - Function signature
# - Parameters
# - Examples
# - Version-specific notes
```

**Use cases:**
- Accurate API usage
- Version compatibility
- Parameter options
- Migration guides

### 2. Package Registry Search

**Purpose:** Find, evaluate, and understand libraries

#### PyPI (Python)
```python
# MCP Tool: search_pypi
search_pypi(
    query="async http client",
    classifiers=["Development Status :: 5 - Production/Stable"]
)

# Returns:
# - Package names
# - Descriptions
# - Downloads/week
# - Last update
# - License
# - GitHub stars
```

#### npm (JavaScript)
```python
# MCP Tool: search_npm
search_npm(
    query="react state management",
    quality_threshold=0.7
)
```

#### crates.io (Rust), Maven Central (Java), etc.

**Use cases:**
- Finding right library for task
- Comparing alternatives
- Checking maintenance status
- Evaluating popularity/stability

### 3. GitHub Code Search

**Purpose:** Find real-world examples and patterns

```python
# MCP Tool: search_github_code
search_github_code(
    query="sqlalchemy async session language:python",
    stars=">100",
    sort="indexed"
)

# Returns:
# - Code snippets
# - Repository context
# - Usage patterns
# - Real-world examples
```

**Use cases:**
- Learning library usage
- Finding design patterns
- Understanding best practices
- Seeing production code

---

## Code Discovery & Examples

### 4. Example Code Repositories

**Purpose:** Curated, high-quality code examples

```python
# MCP Tool: search_examples
search_examples(
    technology="FastAPI",
    pattern="authentication",
    quality="production"
)

# Returns from curated sources:
# - awesome-* lists
# - Official examples
# - Well-maintained templates
# - Production boilerplates
```

**Sources:**
- awesome-lists (awesome-python, awesome-javascript, etc.)
- Official framework examples
- RealWorld implementations
- Design pattern repositories

### 5. Snippet Collections

**Purpose:** Quick reference for common patterns

```python
# MCP Tool: get_snippet
get_snippet(
    language="python",
    pattern="retry with exponential backoff"
)

# Returns:
# - Tested code snippet
# - Explanation
# - Edge cases handled
# - Dependencies needed
```

**Sources:**
- 30 seconds of code
- Rosetta Code
- Language-specific snippet collections

---

## API & Service Integration

### 6. API Documentation Aggregators

**Purpose:** Understand third-party APIs

```python
# MCP Tool: api_docs
api_docs(
    service="stripe",
    endpoint="create_payment_intent",
    language="python"
)

# Returns:
# - Endpoint details
# - Parameters
# - Code examples
# - Error codes
# - Rate limits
```

**Sources:**
- Official API docs
- OpenAPI/Swagger specs
- Postman collections
- RapidAPI documentation

### 7. API Testing Tools

**Purpose:** Test and validate API integrations

```python
# MCP Tool: test_api
test_api(
    method="POST",
    url="http://localhost:8000/api/users",
    headers={"Content-Type": "application/json"},
    body={"name": "Test User"},
    expected_status=201
)

# Returns:
# - Response status
# - Response body
# - Headers
# - Timing
# - Validation results
```

**Integration with:**
- curl
- httpie
- Postman
- Insomnia

---

## Security & Compliance

### 8. Vulnerability Scanners

**Purpose:** Detect security issues in dependencies and code

```python
# MCP Tool: scan_dependencies
scan_dependencies(
    manifest="requirements.txt"
)

# Returns:
# - Known vulnerabilities (CVEs)
# - Severity levels
# - Fix versions available
# - Affected versions
```

**Tools:**
- Snyk
- npm audit
- pip-audit
- OWASP Dependency-Check
- GitHub Dependabot

### 9. Secret Detection

**Purpose:** Prevent accidental secret commits

```python
# MCP Tool: scan_secrets
scan_secrets(
    path="src/",
    exclude_patterns=[".env.example"]
)

# Returns:
# - Found secrets (API keys, tokens, passwords)
# - File locations
# - Line numbers
# - Secret type
```

**Tools:**
- gitleaks
- truffleHog
- detect-secrets
- git-secrets

### 10. SAST (Static Application Security Testing)

**Purpose:** Find security vulnerabilities in code

```python
# MCP Tool: security_scan
security_scan(
    path="src/",
    rules=["sql-injection", "xss", "command-injection"]
)

# Returns:
# - Vulnerabilities found
# - Severity
# - CWE classification
# - Fix recommendations
```

**Tools:**
- Bandit (Python)
- Semgrep
- CodeQL
- SonarQube

### 11. License Compliance

**Purpose:** Ensure dependency licenses are compatible

```python
# MCP Tool: check_licenses
check_licenses(
    manifest="package.json",
    allowed_licenses=["MIT", "Apache-2.0", "BSD-3-Clause"]
)

# Returns:
# - License for each dependency
# - Incompatible licenses
# - Transitive dependencies
# - Compliance status
```

---

## Performance & Debugging

### 12. Performance Profiling

**Purpose:** Identify bottlenecks and optimization opportunities

```python
# MCP Tool: profile_code
profile_code(
    script="src/main.py",
    function="process_data",
    duration=10  # seconds
)

# Returns:
# - Function call times
# - Memory usage
# - CPU usage
# - Hotspots
# - Optimization suggestions
```

**Tools:**
- cProfile (Python)
- node --prof (Node.js)
- perf (Linux)
- Flamegraphs

### 13. Memory Analysis

**Purpose:** Detect memory leaks and optimization

```python
# MCP Tool: analyze_memory
analyze_memory(
    pid=12345,
    duration=60
)

# Returns:
# - Memory growth over time
# - Object allocation stats
# - Potential leaks
# - GC statistics
```

**Tools:**
- memory_profiler
- heapy
- valgrind
- Chrome DevTools (for JS)

### 14. Debug Symbol Lookup

**Purpose:** Understand error stack traces

```python
# MCP Tool: explain_traceback
explain_traceback(
    traceback="""
    File "src/main.py", line 42, in process
        result = transform(data)
    TypeError: 'NoneType' object is not callable
    """
)

# Returns:
# - Likely cause
# - Common fixes
# - Related documentation
# - Similar issues
```

---

## Database & Data Tools

### 15. Database Schema Inspector

**Purpose:** Understand and query database structure

```python
# MCP Tool: inspect_database
inspect_database(
    connection="postgresql://localhost:5432/mydb",
    schema="public"
)

# Returns:
# - Tables
# - Columns and types
# - Indexes
# - Foreign keys
# - Constraints
```

### 16. Query Optimizer

**Purpose:** Improve SQL query performance

```python
# MCP Tool: optimize_query
optimize_query(
    query="""
    SELECT * FROM users u
    JOIN orders o ON u.id = o.user_id
    WHERE u.created_at > '2024-01-01'
    """,
    database="postgresql"
)

# Returns:
# - Execution plan
# - Missing indexes
# - Query rewrite suggestions
# - Estimated improvement
```

### 17. Sample Data Generator

**Purpose:** Create realistic test data

```python
# MCP Tool: generate_test_data
generate_test_data(
    schema={
        "users": {
            "id": "uuid",
            "name": "person_name",
            "email": "email",
            "created_at": "datetime"
        }
    },
    count=100
)

# Returns:
# - Realistic test data
# - SQL insert statements
# - JSON fixtures
# - CSV files
```

**Tools:**
- Faker
- Mimesis
- Mockaroo

---

## Visualization & Diagrams

### 18. Architecture Diagram Generator

**Purpose:** Visualize system architecture from code

```python
# MCP Tool: generate_architecture_diagram
generate_architecture_diagram(
    path="src/",
    format="mermaid"
)

# Returns:
# - Mermaid/PlantUML diagram
# - Component relationships
# - Data flow
# - PNG/SVG export
```

**Tools:**
- PlantUML
- Mermaid
- Graphviz
- draw.io automation

### 19. Database ER Diagrams

**Purpose:** Visualize database schema

```python
# MCP Tool: generate_er_diagram
generate_er_diagram(
    connection="postgresql://localhost/mydb",
    format="svg"
)

# Returns:
# - Entity-relationship diagram
# - Tables and relationships
# - Cardinality
# - Visual export
```

### 20. Dependency Graph

**Purpose:** Visualize code dependencies

```python
# MCP Tool: visualize_dependencies
visualize_dependencies(
    path="src/",
    depth=3,
    exclude=["tests", "__pycache__"]
)

# Returns:
# - Module dependency graph
# - Circular dependencies
# - Unused modules
# - Import analysis
```

---

## Collaboration & Communication

### 21. Issue/Bug Tracker Integration

**Purpose:** Link code changes to issues

```python
# MCP Tool: search_issues
search_issues(
    repo="user/project",
    state="open",
    labels=["bug", "high-priority"]
)

# Returns:
# - Issue titles
# - Descriptions
# - Comments
# - Related PRs
# - Status
```

**Integration:**
- GitHub Issues
- Jira
- Linear
- GitLab Issues

### 22. Pull Request Context

**Purpose:** Understand PR changes and discussions

```python
# MCP Tool: get_pr_context
get_pr_context(
    repo="user/project",
    pr_number=42
)

# Returns:
# - PR description
# - Changed files
# - Comments/reviews
# - CI status
# - Merge conflicts
```

### 23. Changelog Generator

**Purpose:** Auto-generate changelogs from commits

```python
# MCP Tool: generate_changelog
generate_changelog(
    since="v1.0.0",
    until="HEAD",
    format="keepachangelog"
)

# Returns:
# - Categorized changes
# - Breaking changes
# - New features
# - Bug fixes
# - Contributors
```

---

## Implementation Guide

### How IdlerGear Provides These Tools

#### Method 1: MCP Server Tools (Recommended)

**All tools exposed via MCP server for local LLMs:**

```python
# ~/.idlergear/mcp-tools/knowledge.py
from mcp import Tool

class ArxivSearchTool(Tool):
    """Search arXiv for academic papers."""

    name = "search_arxiv"
    description = "Search arXiv for academic papers on technical topics"

    async def run(self, query: str, category: str = None, max_results: int = 5):
        import arxiv

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        results = []
        for paper in search.results():
            results.append({
                "title": paper.title,
                "authors": [a.name for a in paper.authors],
                "abstract": paper.summary,
                "url": paper.pdf_url,
                "published": paper.published.isoformat()
            })

        return results
```

**Local LLMs use it:**

```python
# Gemini CLI, Claude Code, etc.
papers = await search_arxiv(
    query="attention mechanism optimization",
    category="cs.LG",
    max_results=5
)

# LLM now has access to latest research!
```

#### Method 2: Web LLMs via eddi Commands

**For Claude Code Web, Copilot Web, etc.:**

```bash
# Claude Code Web sends command
eddi-msgsrv send "SEARCH_ARXIV: transformer optimization" --server local

# Local environment executes search, sends results back
eddi-msgsrv send "RESULTS: [list of papers...]" --server local
```

#### Method 3: CLI Tools Integration

**IdlerGear wraps common CLI tools:**

```bash
# Vulnerability scanning
idlergear security scan-deps
# Wraps: pip-audit, npm audit, etc.

# Secret detection
idlergear security scan-secrets
# Wraps: gitleaks, truffleHog

# Performance profiling
idlergear perf profile src/main.py
# Wraps: cProfile, memory_profiler

# API testing
idlergear api test http://localhost:8000/api/users
# Wraps: curl, httpie
```

### Configuration

**File: `.idlergear/tools.toml`**

```toml
[tools.knowledge]
enabled = true

[tools.knowledge.arxiv]
enabled = true
default_max_results = 5

[tools.knowledge.wikipedia]
enabled = true
language = "en"

[tools.knowledge.stackoverflow]
enabled = true
api_key = "keychain:stackoverflow-api-key"

[tools.knowledge.github]
enabled = true
api_token = "keychain:github-token"

[tools.security]
enabled = true

[tools.security.vulnerability_scanning]
enabled = true
tools = ["pip-audit", "npm-audit"]

[tools.security.secret_detection]
enabled = true
tools = ["gitleaks"]
auto_scan_on_commit = true

[tools.security.sast]
enabled = true
tools = ["bandit", "semgrep"]

[tools.performance]
enabled = true

[tools.performance.profiling]
enabled = true
auto_profile_slow_functions = true
threshold_ms = 1000

[tools.database]
enabled = true
connections = [
    { name = "local_postgres", url = "postgresql://localhost:5432/mydb" },
    { name = "staging", url = "postgresql://staging:5432/mydb" }
]

[tools.visualization]
enabled = true
diagram_format = "mermaid"
auto_generate_docs = true

[tools.collaboration]
enabled = true
issue_tracker = "github"
repo = "user/project"
```

### Tool Discovery by LLMs

**AI_INSTRUCTIONS/TOOLS.md (Auto-generated):**

```markdown
# Available Tools

This project has access to the following tools via MCP server:

## Knowledge & Documentation
- `search_arxiv(query, category, max_results)` - Search academic papers
- `wikipedia_lookup(topic, summary_length)` - Get technical concept explanations
- `search_stackoverflow(query, tags)` - Find community solutions
- `fetch_docs(library, function, version)` - Get official documentation
- `search_pypi(query, classifiers)` - Find Python packages

## Security
- `scan_dependencies(manifest)` - Check for vulnerabilities
- `scan_secrets(path)` - Detect exposed secrets
- `security_scan(path, rules)` - SAST scanning
- `check_licenses(manifest, allowed_licenses)` - License compliance

## Performance
- `profile_code(script, function)` - Performance profiling
- `analyze_memory(pid)` - Memory analysis
- `optimize_query(query, database)` - SQL optimization

## Database
- `inspect_database(connection, schema)` - Schema inspection
- `execute_query(connection, query)` - Run queries safely
- `generate_test_data(schema, count)` - Create test data

## Visualization
- `generate_architecture_diagram(path)` - System diagrams
- `generate_er_diagram(connection)` - Database diagrams
- `visualize_dependencies(path)` - Dependency graphs

Use these tools to enhance your responses with current information,
security checks, and technical documentation!
```

---

## Usage Examples

### Example 1: Researching Implementation Approach

**User asks:** "How should I implement distributed tracing?"

**LLM uses tools:**

```python
# 1. Search recent research
papers = await search_arxiv("distributed tracing microservices", max_results=3)

# 2. Find popular libraries
packages = await search_pypi("distributed tracing opentelemetry")

# 3. Get community best practices
discussions = await search_stackoverflow("distributed tracing setup", tags=["microservices"])

# 4. Find real-world examples
examples = await search_github_code("opentelemetry python setup stars:>100")

# LLM response now includes:
# - Latest research findings
# - Recommended libraries (OpenTelemetry)
# - Community-validated approaches
# - Production code examples
```

### Example 2: Security Review

**User asks:** "Review this code for security issues"

**LLM uses tools:**

```python
# 1. Scan for secrets
secrets = await scan_secrets("src/")

# 2. Check dependencies
vulns = await scan_dependencies("requirements.txt")

# 3. SAST scan
security_issues = await security_scan("src/", rules=["sql-injection", "xss"])

# 4. License check
licenses = await check_licenses("requirements.txt", allowed=["MIT", "Apache-2.0"])

# LLM response includes:
# - No hardcoded secrets found ✓
# - 2 vulnerable dependencies (with fixes)
# - Potential SQL injection at src/db.py:42
# - All licenses compatible ✓
```

### Example 3: Performance Optimization

**User asks:** "Why is this endpoint slow?"

**LLM uses tools:**

```python
# 1. Profile the code
profile = await profile_code("src/api.py", function="get_users")

# 2. Analyze database query
query_analysis = await optimize_query(
    "SELECT * FROM users WHERE created_at > '2024-01-01'",
    database="postgresql"
)

# 3. Check for N+1 queries
db_insights = await inspect_database("postgresql://localhost/mydb")

# LLM response includes:
# - 85% of time in database queries
# - Missing index on users.created_at
# - N+1 query pattern detected in user.orders
# - SQL rewrite suggestion (with index)
```

### Example 4: Learning New API

**User asks:** "How do I use the Stripe payment API?"

**LLM uses tools:**

```python
# 1. Get official docs
stripe_docs = await api_docs("stripe", "create_payment_intent", language="python")

# 2. Find examples
examples = await search_github_code("stripe create_payment_intent python stars:>50")

# 3. Check for common issues
issues = await search_stackoverflow("stripe payment intent", tags=["python", "stripe"])

# LLM response includes:
# - Official API documentation
# - Working code examples from production apps
# - Common pitfalls (idempotency keys, error handling)
# - Best practices from community
```

---

## Recommended Tool Priority

### Essential (Phase 1)
1. ✅ **arXiv search** - Latest research
2. ✅ **Stack Overflow** - Community solutions
3. ✅ **GitHub code search** - Real examples
4. ✅ **Official docs** - Accurate API info
5. ✅ **Vulnerability scanning** - Security basics

### Important (Phase 2)
6. ✅ **Secret detection** - Prevent leaks
7. ✅ **Package search** - Find libraries
8. ✅ **Performance profiling** - Optimize code
9. ✅ **Database tools** - Data management
10. ✅ **Wikipedia** - Concept explanations

### Nice-to-Have (Phase 3)
11. ✅ **SAST scanning** - Deep security
12. ✅ **Memory analysis** - Advanced debugging
13. ✅ **Visualization** - Architecture diagrams
14. ✅ **Issue tracking** - Project context
15. ✅ **License compliance** - Legal safety

---

## Benefits Summary

### For LLM Coding Assistants

**Better Responses:**
- Access to current information (papers, docs, discussions)
- Real-world examples and patterns
- Security-aware recommendations
- Performance-optimized solutions

**Enhanced Capabilities:**
- Security scanning before suggesting code
- Finding up-to-date API documentation
- Discovering maintained libraries
- Understanding technical concepts deeply

**Reduced Errors:**
- Verified against official documentation
- Security vulnerabilities detected early
- Common pitfalls avoided (from Stack Overflow)
- License conflicts prevented

### For Developers

**Faster Development:**
- LLM finds information automatically
- No manual documentation searching
- Security checks built-in
- Examples readily available

**Higher Quality:**
- Research-backed decisions
- Production-tested patterns
- Security-validated code
- Well-documented solutions

**Better Learning:**
- Access to papers and explanations
- Real examples to study
- Community best practices
- Technical concept clarification

---

## Summary

**With these tools, LLM coding assistants become:**

🔬 **Researchers** - Access to arXiv, papers, technical content
📚 **Librarians** - Official docs, API references, examples
🔒 **Security Experts** - Vulnerability scanning, secret detection
⚡ **Performance Engineers** - Profiling, optimization, analysis
🎨 **Architects** - Diagrams, visualization, patterns
🤝 **Collaborators** - Issue tracking, PR context, changelogs

**All integrated into IdlerGear's MCP server for seamless access!**
