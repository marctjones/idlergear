# GitHub Projects Integration

IdlerGear provides Kanban-style project boards that sync with GitHub Projects v2, enabling visual task tracking and workflow management.

## Features

- Local Kanban boards with customizable columns
- Bidirectional sync with GitHub Projects v2
- Automatic task assignment to project boards
- Task movement between columns
- Project creation and management

## Quick Start

### Create a Project Board

```bash
# Create a local project with default columns (Backlog, In Progress, Review, Done)
idlergear project create "Sprint Backlog"

# Create with custom columns
idlergear project create "Release v2.0" --columns "To Do" "Doing" "Testing" "Done"

# Create and also create on GitHub
idlergear project create "Team Board" --create-on-github
```

### Add Tasks to Projects

```bash
# Add a specific task to a project
idlergear project add-task sprint-backlog 123

# Add to a specific column
idlergear project add-task sprint-backlog 124 --column "In Progress"

# View project board
idlergear project show sprint-backlog
```

### Move Tasks Between Columns

```bash
# Move task to different column
idlergear project move-task sprint-backlog 123 --column "Review"
```

## Auto-Add Tasks to Projects

Configure IdlerGear to automatically add new tasks to a project board when they're created.

### Setup

1. **Create a project board:**
   ```bash
   idlergear project create "Sprint Backlog"
   ```

2. **Configure auto-add in `.idlergear/config.toml`:**
   ```toml
   [projects]
   default_project = "sprint-backlog"
   default_column = "Backlog"
   auto_add = true
   ```

   Or use the CLI:
   ```bash
   idlergear config set projects.auto_add true
   idlergear config set projects.default_project "sprint-backlog"
   idlergear config set projects.default_column "Backlog"
   ```

3. **Create tasks as normal:**
   ```bash
   idlergear task create "Feature: Add login"
   # ✓ Created task #123: Feature: Add login
   # ✓ Added to project 'sprint-backlog'
   ```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `projects.default_project` | string | None | Project slug or name for new tasks |
| `projects.default_column` | string | "Backlog" | Column name for auto-added tasks |
| `projects.auto_add` | boolean | false | Enable/disable auto-add feature |

### Disabling Auto-Add

Temporarily disable auto-add without removing configuration:

```bash
idlergear config set projects.auto_add false
```

Or remove the default project:

```bash
idlergear config set projects.default_project ""
```

### How It Works

When `auto_add = true`:

1. You create a task via CLI or MCP tool
2. IdlerGear checks for `projects.default_project` configuration
3. If found, task is automatically added to the specified project
4. Task is placed in the `default_column` (or first column if not specified)
5. Task creation never fails even if project add fails (silent fallback)

The auto-add feature works with both:
- CLI: `idlergear task create ...`
- MCP tool: `idlergear_task_create(...)`

### Example Workflow

```bash
# Set up auto-add for current sprint
idlergear project create "Sprint 24"
idlergear config set projects.auto_add true
idlergear config set projects.default_project "sprint-24"

# All new tasks automatically added
idlergear task create "Bug: Fix login timeout" --label bug
# ✓ Created task #125: Bug: Fix login timeout
# ✓ Added to project 'sprint-24'

idlergear task create "Feature: Add dark mode" --label enhancement
# ✓ Created task #126: Feature: Add dark mode
# ✓ Added to project 'sprint-24'

# View sprint board
idlergear project show sprint-24
```

## Syncing with GitHub

### One-Time Sync

Push a local project to GitHub Projects v2:

```bash
idlergear project sync sprint-backlog
```

This creates the project on GitHub if it doesn't exist and adds all tasks as issues.

### Link to Existing GitHub Project

If you already have a GitHub Project, link it to your local board:

```bash
# List available GitHub Projects
idlergear project list --include-github

# Link to project #5
idlergear project link sprint-backlog 5
```

## Managing Projects

### List Projects

```bash
# List local projects
idlergear project list

# Include GitHub Projects
idlergear project list --include-github
```

### View Project Board

```bash
idlergear project show sprint-backlog
```

### Delete Project

```bash
# Delete local project only
idlergear project delete sprint-backlog

# Also delete from GitHub
idlergear project delete sprint-backlog --delete-on-github
```

## MCP Integration

All project operations are available via MCP tools for use in AI assistants:

```python
# Create project
idlergear_project_create(title="Sprint 24")

# Add task to project
idlergear_project_add_task(project_name="sprint-24", task_id="123")

# Move task
idlergear_project_move_task(project_name="sprint-24", task_id="123", column="Review")

# View project
idlergear_project_show(name="sprint-24")
```

When using MCP `idlergear_task_create()`, the response includes `added_to_project` boolean indicating whether auto-add was triggered:

```json
{
  "task": {
    "id": 123,
    "title": "Feature: Add login",
    ...
  },
  "added_to_project": true
}
```

## Tips

1. **Use slugs or full names**: Project identifiers work with both slugified names (`sprint-backlog`) and full titles (`Sprint Backlog`)

2. **Silent failures**: Auto-add silently skips if the project doesn't exist, ensuring task creation never fails

3. **Column fallback**: If the specified column doesn't exist, the first column is used automatically

4. **Per-project configuration**: Auto-add is workspace-wide, but you can change the default project as you switch between sprints or releases

## See Also

- [IdlerGear Tasks Documentation](../README.md#tasks)
- [Configuration Guide](../README.md#configuration)
- [MCP Tools Reference](../../src/idlergear/skills/idlergear/references/mcp-tools.md)
