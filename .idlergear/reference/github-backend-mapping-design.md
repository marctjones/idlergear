---
id: 1
title: GitHub Backend Mapping Design
created: '2026-01-11T16:21:23.082996Z'
updated: '2026-01-11T16:21:23.083008Z'
---
# GitHub Backend Mapping Design

This document captures the design decision for how IdlerGear's knowledge types map to GitHub primitives.

## Background

IdlerGear has 6 knowledge types. GitHub provides several primitives (Issues, Discussions, Wiki, Projects, Files). This document analyzes the optimal mapping.

## First Principles Analysis

### 1. What each knowledge type IS

| Type | Nature | Lifecycle | Who Uses |
|------|--------|-----------|----------|
| **Task** | Actionable work | open → closed | Humans + AI |
| **Note** | Quick capture, ephemeral | capture → promote/delete | Primarily AI |
| **Vision** | Project purpose | rarely changes | Everyone |
| **Plan** | Implementation roadmap | create → execute → archive | Humans + AI |
| **Reference** | Permanent documentation | accumulates | Everyone |
| **Run** | Script execution log | start → complete | Machine-specific |

### 2. What GitHub provides

| Primitive | Lifecycle | API Support | Best For |
|-----------|-----------|-------------|----------|
| **Issues** | open/closed | Full CRUD + labels + assignees | Actionable work |
| **Discussions** | open/answered | GraphQL CRUD (no REST) | Conversation, Q&A, ideas |
| **Wiki** | versioned pages | git-based (clone/push) | Documentation |
| **Projects v2** | kanban boards | GraphQL only | Work tracking |
| **Files** | git history | git push | Version-controlled content |

### 3. Key Insight: Notes Don't Fit Issues

Notes have fundamental mismatch with Issues:
- Notes are **ephemeral** (meant to be processed and cleared)
- Issues are **permanent** (work items that need resolution)
- Notes have **no lifecycle** (not "open" or "closed")
- Issues have **clear completion** (work is done or not)

When Notes are stored as Issues:
- They pollute the Issues list with non-actionable items
- The "note" label becomes a filter everyone must use
- Promotion to Task means removing label (confusing history)

## Mapping Options Evaluated

### Option A: Notes as Issues (Current)

```
Tasks → Issues
Notes → Issues (with "note" label)
Vision → VISION.md file
Plans → Projects v2
References → Wiki
Runs → Local only
```

**Pros:**
- Simple implementation (one backend for tasks+notes)
- All items visible in one place

**Cons:**
- Notes pollute Issues list
- Must filter by label constantly
- No semantic separation

### Option B: Notes as Discussions (Recommended)

```
Tasks → Issues
Notes → Discussions ("Notes" category)
Vision → VISION.md file
Plans → Projects v2
References → Wiki
Runs → Local only
```

**Pros:**
- Clean separation: Issues = work, Discussions = thinking
- Discussions support categories (can have "Ideas", "Questions", etc.)
- "Answered" state fits the "processed" concept
- GitHub UI shows them separately

**Cons:**
- No direct "convert to issue" API (must create new issue + delete discussion)
- Requires GraphQL for CRUD
- Additional implementation complexity

### Option C: Notes as Draft Issues (Not Supported)

GitHub doesn't have draft issues at the repository level. Projects v2 has draft items but they're tied to projects.

### Option D: Eliminate Notes Entirely

Just use Tasks with a "needs-review" or "draft" label.

**Pros:**
- Simpler mental model
- Fewer abstractions

**Cons:**
- Loses the capture-first workflow
- AI can't quickly dump discoveries
- Conflates "thinking" with "doing"

## Recommendation: Option B (Notes as Discussions)

### Mapping

| IdlerGear | GitHub Primitive | Rationale |
|-----------|------------------|-----------|
| Task | Issue | Perfect 1:1 mapping. Same lifecycle, fields, and semantics. |
| Note | Discussion | Ephemeral thinking belongs in Discussions, not actionable Issues. |
| Vision | VISION.md | Version-controlled with code. Simple file, no API needed. |
| Plan | Project v2 | Kanban boards with custom fields. Can link to Issues. |
| Reference | Wiki | GitHub's documentation home. Versioned, searchable. |
| Run | Local | Machine-specific execution logs. No sync needed. |

### Implementation Details

#### Notes → Discussions

1. **Category Setup**: Create "Notes" category in Discussions (can be done via API)
2. **Tags → Labels**: Note tags become discussion labels
3. **Promotion Workflow**:
   - Read discussion title + body
   - Create new Issue with same content
   - Add comment to discussion: "Promoted to #N"
   - Close discussion (or delete if user prefers)

4. **GraphQL Required**: Discussions require GraphQL API (`createDiscussion`, `updateDiscussion`, etc.)

#### API Availability

```
createDiscussion       ✓ (tested)
updateDiscussion       ✓
deleteDiscussion       ✓ (tested)
closeDiscussion        ✓
reopenDiscussion       ✓
```

No `convertDiscussionToIssue` mutation - manual promote required.

### Category Structure

Recommend creating these Discussion categories:

| Category | Purpose | IdlerGear Mapping |
|----------|---------|-------------------|
| Notes | Quick captures from AI/humans | `note create` |
| Ideas | Features to explore | `note create --tag idea` |
| Questions | Research questions | `note create --tag explore` |

Or simpler: just use "Ideas" category for all notes.

## Migration Path

1. **Phase 1**: Implement discussion backend for notes
2. **Phase 2**: Add migration command: `idlergear note migrate --to-discussions`
3. **Phase 3**: Deprecate note storage in Issues

## Decision

**Use Discussions for Notes**, with these key points:

1. Notes go to Discussions ("Notes" or "Ideas" category)
2. Promotion creates Issue + closes Discussion
3. Tags map to discussion labels
4. GraphQL implementation required

This keeps Issues clean for actionable work and gives Notes their own semantic space.

---

## Unified Reference Model

### The Problem with Separate Vision

Vision was originally a separate knowledge type, but:
- It's just documentation (like References)
- It maps to a file (VISION.md) just like README.md
- Having separate commands (`vision show` vs `reference show`) adds complexity

### Proposal: References with Sources

Unify all documentation under **References** with different **sources**:

| Source Type | Examples | Storage | Sync |
|-------------|----------|---------|------|
| **file** | VISION.md, README.md, CHANGELOG.md | Repo files | Git |
| **wiki** | Architecture, API Design | GitHub Wiki | Wiki sync |
| **generated** | API docs, CLI docs, Schema docs | Built from code | Rebuild |

### Pinned References (Special Files)

Some references are "pinned" to specific repo files:

| Reference | File | Purpose |
|-----------|------|---------|
| `vision` | VISION.md | Project purpose and direction |
| `readme` | README.md | User-facing documentation |
| `contributing` | CONTRIBUTING.md | Contributor guidelines |
| `changelog` | CHANGELOG.md | Release history |

These are pre-configured and cannot be deleted. They're just references with a fixed file location.

### CLI Design

```bash
# Pinned references (files in repo)
idlergear reference show vision       # reads VISION.md
idlergear reference show readme       # reads README.md
idlergear reference edit vision       # edits VISION.md

# Wiki references
idlergear reference show "API Design" # reads from Wiki
idlergear reference add "New Doc"     # creates Wiki page

# Generated references (read-only)
idlergear reference show "API Reference"  # shows generated docs
idlergear reference build                  # rebuilds all generated

# List all
idlergear reference list
# [pinned] vision        VISION.md
# [pinned] readme        README.md
# [wiki]   API Design    GitHub Wiki
# [gen]    API Reference openapi.yaml
```

### Generated Documentation

AI assistants benefit from structured API documentation. IdlerGear can integrate with documentation generators:

| Generator | Input | Language | Output |
|-----------|-------|----------|--------|
| `openapi` | openapi.yaml | Any | REST API docs |
| `asyncapi` | asyncapi.yaml | Any | Event/message docs |
| `graphql` | schema.graphql | Any | GraphQL schema |
| `protobuf` | *.proto | Any | gRPC service docs |
| `jsonschema` | *.json | Any | Schema docs |
| `click` | Python module | Python | CLI docs |
| `typer` | Python module | Python | CLI docs |
| `pydantic` | Python module | Python | Model docs |
| `xmldoc` | *.dll, *.xml | .NET | API docs from XML comments |
| `rustdoc` | Cargo.toml | Rust | API docs from rustdoc |

#### Registering Generators

```bash
# Register OpenAPI docs
idlergear reference register "API Reference" \
    --source generated \
    --generator openapi \
    --input openapi.yaml

# Register .NET XML docs
idlergear reference register "API Reference" \
    --source generated \
    --generator xmldoc \
    --input "bin/Debug/net8.0/MyApp.xml"

# Register Rust docs
idlergear reference register "API Reference" \
    --source generated \
    --generator rustdoc \
    --input .

# Rebuild when code changes
idlergear reference build
```

### Why Generated Docs Help AI

Instead of parsing prose documentation, AI gets structured data:

```bash
idlergear reference show "API Reference" --format json
```

```json
{
  "endpoints": [
    {
      "path": "/api/tasks",
      "method": "POST",
      "summary": "Create a new task",
      "parameters": [
        {"name": "title", "type": "string", "required": true}
      ],
      "responses": {
        "201": {"description": "Task created"}
      }
    }
  ]
}
```

### Updated Knowledge Model (5 Types)

| Type | Description | GitHub Backend |
|------|-------------|----------------|
| **Task** | Actionable work | Issues |
| **Note** | Quick capture | Discussions |
| **Plan** | Implementation roadmap | Projects v2 |
| **Reference** | All documentation | Files + Wiki + Generated |
| **Run** | Script execution | Local only |

Vision becomes a pinned reference, not a separate type. This simplifies the model while gaining power through generated docs.

### Migration from Vision to Reference

```bash
# Old way (deprecated)
idlergear vision show
idlergear vision edit

# New way
idlergear reference show vision
idlergear reference edit vision
```

The old commands can remain as aliases for backwards compatibility.

---

## Generator Configuration System

Generators rely on third-party tools (rustdoc, dotnet, protoc, etc.). The system needs:
1. **Discovery** - Which generators are available on this system?
2. **Configuration** - How to invoke them, where outputs go
3. **Extensibility** - Users can add custom generators

### Generator Types

| Type | Implementation | External Dependencies |
|------|----------------|----------------------|
| **Built-in** | Pure Python | None or Python packages |
| **Shell** | Invokes external command | Requires tool in PATH |
| **Custom** | User-defined command | User-specified |

### Built-in Generators (No External Deps)

| Generator | Dependencies | Notes |
|-----------|--------------|-------|
| `openapi` | `pyyaml` (Python) | Parse OpenAPI specs |
| `jsonschema` | None (stdlib) | Parse JSON schemas |
| `click` | `click` module | Introspect Click CLI |
| `typer` | `typer` module | Introspect Typer CLI |
| `pydantic` | `pydantic` module | Introspect Pydantic models |
| `xmldoc` | None (stdlib XML) | Parse .NET XML docs |

### Shell Generators (External Tools)

| Generator | Required Tool | Detection |
|-----------|---------------|-----------|
| `rustdoc` | `cargo +nightly` | `which cargo` |
| `protobuf` | `protoc` | `which protoc` |
| `godoc` | `go` | `which go` |
| `javadoc` | `javadoc` | `which javadoc` |

### Configuration File

```toml
# .idlergear/config.toml

[generators]
# Which generators are enabled (auto-detected by default)
enabled = ["openapi", "click", "rustdoc"]

# Built-in generator with Python dependencies
[generators.openapi]
enabled = true
# No command = use built-in Python parser

# Shell generator - invokes external tool
[generators.rustdoc]
enabled = true
command = "cargo +nightly doc"
env = { RUSTDOCFLAGS = "-Z unstable-options --output-format json" }
output = "target/doc/{crate}.json"
requires = ["cargo"]  # Must be in PATH

# Custom user-defined generator
[generators.my-swagger]
enabled = true
command = "npx swagger-cli bundle api.yaml -o docs/api.json"
output = "docs/api.json"
format = "openapi"  # Parse output as OpenAPI format
requires = ["npx"]
```

### Generator CLI

```bash
# List generators and their status
idlergear generator list
# NAME        STATUS      TYPE        REQUIRES
# openapi     ✓ enabled   built-in    pyyaml
# click       ✓ enabled   built-in    click
# rustdoc     ✗ disabled  shell       cargo +nightly
# xmldoc      ✓ enabled   built-in    -
# my-swagger  ✓ enabled   custom      npx

# Auto-detect available generators
idlergear generator detect
# Detected tools:
#   ✓ cargo 1.75.0      → rustdoc available
#   ✓ dotnet 8.0.1      → xmldoc available
#   ✓ python click      → click available
#   ✗ protoc            → protobuf unavailable
#   ✗ go                → godoc unavailable

# Enable/disable generators
idlergear generator enable rustdoc
idlergear generator disable xmldoc

# Add custom generator
idlergear generator add my-docs \
    --command "npm run build:docs" \
    --output "docs/api.json" \
    --format openapi \
    --requires npx,node

# Remove custom generator
idlergear generator remove my-docs

# Show generator configuration
idlergear generator show rustdoc
# Name: rustdoc
# Type: shell
# Status: enabled
# Command: cargo +nightly doc
# Env: RUSTDOCFLAGS=-Z unstable-options --output-format json
# Output: target/doc/{crate}.json
# Requires: cargo (found at /usr/bin/cargo)
```

### Generator Base Class

```python
# src/idlergear/generators/base.py
from abc import ABC, abstractmethod
from typing import Optional
import shutil

class Generator(ABC):
    """Base class for documentation generators."""

    name: str
    generator_type: str  # "built-in", "shell", "custom"
    requires: list[str]  # External dependencies
    python_deps: list[str]  # Python package dependencies

    def detect(self) -> bool:
        """Check if this generator can run on this system."""
        # Check shell dependencies
        for tool in self.requires:
            if not shutil.which(tool):
                return False

        # Check Python dependencies
        for pkg in self.python_deps:
            try:
                __import__(pkg)
            except ImportError:
                return False

        return True

    def get_missing_deps(self) -> list[str]:
        """Return list of missing dependencies."""
        missing = []
        for tool in self.requires:
            if not shutil.which(tool):
                missing.append(f"{tool} (not in PATH)")
        for pkg in self.python_deps:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(f"{pkg} (pip install {pkg})")
        return missing

    @abstractmethod
    def generate(self, input_path: str, config: dict) -> dict:
        """Generate structured documentation.

        Returns:
            dict with structured API/schema documentation
        """
        pass


class ShellGenerator(Generator):
    """Generator that invokes an external command."""

    generator_type = "shell"
    command: str
    env: dict[str, str] = {}
    output_path: str

    def generate(self, input_path: str, config: dict) -> dict:
        import subprocess
        import json

        # Run the command
        env = {**os.environ, **self.env, **config.get("env", {})}
        result = subprocess.run(
            self.command,
            shell=True,
            cwd=input_path,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise GeneratorError(f"Command failed: {result.stderr}")

        # Read and parse output
        output_file = Path(input_path) / self.output_path
        return json.loads(output_file.read_text())
```

### Workflow

1. **At install time**: `idlergear generator detect` runs automatically
2. **User registers reference**: `idlergear reference register "API" --generator rustdoc`
3. **System checks**: Is rustdoc enabled and available?
4. **At build time**: `idlergear reference build` invokes enabled generators
5. **AI queries**: `idlergear reference show "API" --format json`

### Error Handling

```bash
# When generator is unavailable
$ idlergear reference register "API" --generator rustdoc
Error: Generator 'rustdoc' is not available.
Missing dependencies:
  - cargo +nightly (not in PATH)

To use this generator, install Rust nightly:
  rustup install nightly

Or disable this generator:
  idlergear generator disable rustdoc
```

---

## External References

- [GitHub GraphQL Mutations](https://docs.github.com/en/graphql/reference/mutations)
- [Using the GraphQL API for Discussions](https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Rust rustdoc](https://doc.rust-lang.org/rustdoc/)
- [.NET XML Documentation](https://docs.microsoft.com/en-us/dotnet/csharp/language-reference/xmldoc/)
