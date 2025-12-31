# GitHub Integration

IdlerGear can use GitHub as a backend for knowledge storage, enabling collaboration and visibility across teams.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- Repository exists on GitHub

```bash
# Check gh is authenticated
gh auth status
```

## Configuration

Set backends in `.idlergear/config.toml`:

```toml
[backends]
task = "github"      # Issues with "task" label
note = "github"      # Issues with "note" label
explore = "github"   # Issues with "explore" label
vision = "github"    # VISION.md in repository
plan = "github"      # GitHub Projects v2
reference = "github" # GitHub Wiki pages
```

You can mix backends:

```toml
[backends]
task = "github"    # Share tasks with team
note = "local"     # Keep notes private
vision = "github"  # Shared vision
```

## Backend Mapping

| Knowledge Type | GitHub Feature |
|---------------|----------------|
| Tasks | Issues with "task" label |
| Notes | Issues with "note" label |
| Explorations | Issues with "explore" label |
| Vision | VISION.md file in repo root |
| Plans | GitHub Projects v2 |
| References | GitHub Wiki pages |

## Task Integration

Tasks become GitHub Issues:

```bash
# Creates GitHub Issue with "task" label
idlergear task create "Implement auth"

# Lists Issues with "task" label
idlergear task list

# Closes the Issue
idlergear task close 1
```

Issue features supported:
- Labels (mapped from task labels)
- Assignees
- Milestones
- Comments

## Vision Integration

Vision syncs to `VISION.md` in the repository:

```bash
# Reads from VISION.md
idlergear vision show

# Updates VISION.md (commits change)
idlergear vision edit
```

## Plan Integration

Plans use GitHub Projects v2:

```bash
# Creates a GitHub Project
idlergear plan create "auth-system" --title "Authentication"

# Links tasks to project
idlergear plan add-task auth-system 1
```

## Reference Integration

References sync to GitHub Wiki:

```bash
# Creates wiki page
idlergear reference add "API-Design" --body "..."

# Lists wiki pages
idlergear reference list

# Searches wiki content
idlergear reference search "authentication"
```

## Sync Commands

Keep local and GitHub in sync:

```bash
# Push local changes to GitHub
idlergear sync push

# Pull GitHub changes to local
idlergear sync pull

# Two-way sync
idlergear sync
```

## Labels

IdlerGear uses labels to organize Issues:

| Label | Purpose |
|-------|---------|
| `task` | Task issues |
| `note` | Note issues |
| `explore` | Exploration issues |
| `priority:high` | High priority |
| `priority:low` | Low priority |

Labels are created automatically when needed.

## Workflow Example

```bash
# 1. Initialize with GitHub backend
idlergear init
idlergear config set backends.task github

# 2. Create task (becomes GitHub Issue)
idlergear task create "Add user auth"

# 3. Work on it (issue is visible on GitHub)
# Team members can comment, etc.

# 4. Complete it (closes the Issue)
idlergear task complete 1
```

## Offline Support

When GitHub is unavailable:
- Commands fall back to cached local data
- Changes queue for later sync
- `idlergear sync` pushes queued changes

## Troubleshooting

### "gh: command not found"

Install GitHub CLI:
```bash
# macOS
brew install gh

# Ubuntu
sudo apt install gh

# Then authenticate
gh auth login
```

### "not a git repository"

Initialize git first:
```bash
git init
git remote add origin https://github.com/user/repo.git
```

### "label not found"

Labels are created automatically, but you can create them manually:
```bash
gh label create task --color 0E8A16
gh label create note --color 1D76DB
gh label create explore --color 5319E7
```
