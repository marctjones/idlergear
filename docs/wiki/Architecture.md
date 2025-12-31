# Architecture

IdlerGear's architecture separates concerns into layers: CLI, Core, and Backends.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Interfaces                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │   CLI   │  │   MCP   │  │  Python │  │  Future: HTTP   │ │
│  │ (typer) │  │ Server  │  │   API   │  │  REST/GraphQL   │ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘ │
└───────┼────────────┼────────────┼────────────────┼──────────┘
        │            │            │                │
        └────────────┴─────┬──────┴────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                          ▼                                  │
│                    Core Library                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Knowledge Types                      │   │
│  │  Task │ Note │ Explore │ Vision │ Plan │ Reference   │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Backend Registry                     │   │
│  │              Dispatch to configured backend           │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                          ▼                                  │
│                      Backends                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │    Local    │  │   GitHub    │  │   Future: Jira,     │  │
│  │ (JSON files)│  │ (gh CLI)    │  │   Linear, Notion    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
src/idlergear/
├── __init__.py          # Package init, exports
├── cli.py               # Typer CLI application
├── mcp_server.py        # MCP server (35 tools)
├── core/
│   ├── __init__.py
│   ├── config.py        # Configuration management
│   ├── project.py       # Project operations
│   └── types.py         # Data models (Task, Note, etc.)
├── backends/
│   ├── __init__.py
│   ├── base.py          # Abstract backend interface
│   ├── registry.py      # Backend dispatch
│   ├── local.py         # Local JSON storage
│   └── github.py        # GitHub backend (gh CLI)
└── templates/
    ├── CLAUDE.md        # Template for install
    ├── AGENTS.md        # Template for install
    └── ...
```

## Core Concepts

### Knowledge Types

Six types, each with its own lifecycle:

```python
class Task:
    id: str
    description: str
    status: Literal["open", "closed"]
    priority: Optional[str]
    labels: List[str]
    created_at: datetime
    closed_at: Optional[datetime]

class Note:
    id: str
    content: str
    created_at: datetime

class Exploration:
    id: str
    question: str
    context: str
    status: Literal["open", "closed"]
    findings: List[str]

class Vision:
    content: str
    updated_at: datetime

class Plan:
    id: str
    slug: str
    title: str
    tasks: List[str]  # Task IDs
    status: Literal["active", "completed", "archived"]

class Reference:
    id: str
    title: str
    body: str
    tags: List[str]
```

### Backend Interface

All backends implement the same interface:

```python
class Backend(ABC):
    @abstractmethod
    async def task_create(self, task: Task) -> Task: ...

    @abstractmethod
    async def task_list(self, filters: dict) -> List[Task]: ...

    @abstractmethod
    async def task_get(self, id: str) -> Task: ...

    @abstractmethod
    async def task_update(self, id: str, updates: dict) -> Task: ...

    # ... same pattern for all knowledge types
```

### Backend Registry

Routes operations to configured backends:

```python
class BackendRegistry:
    def __init__(self, config: Config):
        self.backends = {
            "task": self._create_backend(config.backends.task),
            "note": self._create_backend(config.backends.note),
            # ...
        }

    def get_backend(self, knowledge_type: str) -> Backend:
        return self.backends[knowledge_type]
```

## Local Backend

Stores data in `.idlergear/`:

```
.idlergear/
├── config.toml          # Project configuration
├── vision.md            # Vision document
├── tasks/
│   ├── 1.json
│   └── 2.json
├── notes/
│   └── 1.json
├── explorations/
│   └── 1.json
├── plans/
│   └── auth-system.json
└── reference/
    └── api-design.json
```

## GitHub Backend

Uses `gh` CLI for all GitHub operations:

```python
class GitHubBackend(Backend):
    async def task_create(self, task: Task) -> Task:
        result = subprocess.run([
            "gh", "issue", "create",
            "--title", task.description,
            "--label", "task"
        ], capture_output=True)
        # Parse issue number from result
        return task
```

Mapping:
- Tasks → Issues with "task" label
- Notes → Issues with "note" label
- Explorations → Issues with "explore" label
- Vision → VISION.md file
- Plans → GitHub Projects v2
- References → Wiki pages

## MCP Server

Exposes 35 tools via JSON-RPC:

```python
@server.tool()
async def task_create(description: str) -> dict:
    """Create a new task."""
    backend = registry.get_backend("task")
    task = await backend.task_create(Task(description=description))
    return {"id": task.id, "description": task.description}
```

## Configuration Flow

```
1. CLI/MCP receives command
2. Core loads .idlergear/config.toml
3. Registry looks up backend for knowledge type
4. Backend executes operation
5. Result returned through layers
```

## Future Architecture

Planned additions:

- **Daemon**: Single process for MCP server, file watching, event bus
- **Event Bus**: Pub/sub for multi-agent coordination
- **HTTP API**: REST/GraphQL for non-CLI access
- **Additional Backends**: Jira, Linear, Notion, etc.
