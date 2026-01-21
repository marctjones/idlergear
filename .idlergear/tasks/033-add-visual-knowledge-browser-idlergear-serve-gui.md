---
id: 33
title: 'Add visual knowledge browser: idlergear serve --gui'
state: open
created: '2026-01-07T01:37:00.170869Z'
labels:
- enhancement
- gui
- goose
- 'effort: large'
priority: medium
---
## Summary
Launch local web UI for visual knowledge management, optimized for Goose GUI integration.

## Context
From Goose integration analysis (Note #4): Goose GUI users need visual interface for project knowledge, not just text commands.

## Implementation

```bash
idlergear serve --gui
# Launches web UI on localhost:8080
```

## Features

### 1. **Kanban Board**
- Drag-and-drop tasks between columns
- Backlog → In Progress → Review → Done
- Visual priority indicators (🔴 🟡 🟢)

### 2. **Knowledge Graph**
- Visual relationships: note → task → plan
- Interactive exploration
- Timeline view

### 3. **Search & Filter**
- Full-text search across all knowledge types
- Filter by tags, labels, dates
- Saved searches

### 4. **Run Dashboard**
- Live logs from active runs
- Run history with outputs
- Terminal-style view

### 5. **Session Timeline**
- What happened when
- Git commits linked to knowledge
- Activity heatmap

## Technology Stack

- **Backend**: FastAPI (already used for MCP server)
- **Frontend**: Vanilla JS + Tailwind CSS (no heavy frameworks)
- **Real-time**: WebSockets for live updates
- **Rendering**: Markdown + syntax highlighting

## Goose Integration Options

### Option A: Deep Links
```
goose://open-url?url=http://localhost:8080/tasks/42
```

### Option B: Embedded iFrame
Goose GUI embeds IdlerGear UI directly

### Option C: Standalone Browser
Opens in default browser

## Configuration

```toml
[gui]
enabled = true
port = 8080
host = "localhost"
auto_open = true  # Open browser on start
theme = "auto"    # or "light", "dark"
```

## Security

- Localhost-only by default
- Optional auth for remote access
- CORS headers for Goose GUI embedding

## Acceptance Criteria
- [ ] Web UI launches on `idlergear serve --gui`
- [ ] Kanban board for tasks
- [ ] Knowledge graph visualization
- [ ] Search works across all types
- [ ] Real-time updates via WebSocket
- [ ] Responsive design (works on all screen sizes)
- [ ] Tests for API endpoints
- [ ] Documentation with screenshots

## Related
- Note #4 (Goose integration analysis)
- #108 (project/kanban support)
- #112 (watch mode - could show in GUI)
