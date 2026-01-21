---
id: 1
title: GitHub-Integration
created: '2026-01-07T00:09:17.248879Z'
updated: '2026-01-07T00:09:17.248941Z'
---
# GitHub Integration

Sync IdlerGear knowledge with GitHub Issues, Wiki, and Projects.

## Overview

IdlerGear can sync knowledge types with GitHub:

| Knowledge Type | GitHub Service | Direction |
|----------------|----------------|-----------|
| Tasks | GitHub Issues | Bidirectional |
| Notes | GitHub Issues (labeled) | Bidirectional |
| Vision | VISION.md file | Push |
| Plans | GitHub Projects | Push |
| References | GitHub Wiki | Bidirectional |
| Runs | *(no sync)* | Local only |

## Prerequisites

### 1. GitHub CLI

Install and authenticate the GitHub CLI:

```bash
# Install (macOS)
brew install gh

# Install (Linux)
sudo apt install gh

# Authenticate
gh auth login
```

### 2. Repository

Your project must be a git repo with a GitHub remote:

```bash
git remote -v
# Should show github.com origin
```

## Setup

### Automatic Setup

```bash
idlergear setup-github
```

This:
1. Detects your GitHub repository
2. Checks if Wiki is enabled
3. Configures appropriate backends

### Manual Setup

```bash
# Use GitHub for tasks
idlergear config set backend.task github

# Use GitHub Wiki for references
idlergear config set backend.reference github
```

## Task Sync

Tasks sync bidirectionally with GitHub Issues.

### Configuration

```bash
idlergear config set backend.task github
```

### Sync Command

```bash
idlergear task sync
```

This:
1. Creates GitHub Issues for new local tasks
2. Downloads new GitHub Issues as local tasks
3. Updates changed items in both directions

### Mapping

| IdlerGear | GitHub Issue |
|-----------|--------------|
| id | Issue number |
| title | Issue title |
| body | Issue body |
| state (open/closed) | Issue state |
| priority | Label (priority-high, etc.) |
| labels | Labels |

### Example

```bash
# Create locally
idlergear task create "Fix auth bug" --label bug --priority high

# Sync to GitHub
idlergear task sync
# Creates issue #42 with labels: bug, priority-high

# Close on GitHub, then sync
# Issue closed on github.com
idlergear task sync
# Local task 42 now shows as closed
```

## Reference Sync (Wiki)

References sync bidirectionally with GitHub Wiki.

### Configuration

```bash
idlergear config set backend.reference github
```

### Sync Command

```bash
idlergear reference sync
```

### How It Works

1. IdlerGear clones the wiki repository (`.idlergear/.wiki/`)
2. Compares local references with wiki pages
3. Pushes/pulls changes as needed
4. Uses wiki page titles as reference titles

### Wiki Page Format

Wiki pages have a specific format:

```markdown
---
id: 1
title: API Design
created: '2026-01-10T10:00:00Z'
updated: '2026-01-10T10:00:00Z'
---
# API Design

Your content here...
```

### Example

```bash
# Create reference
idlergear reference add "API Design" --body "REST conventions..."

# Sync to Wiki
idlergear reference sync
# Creates wiki page "API-Design"

# Edit on GitHub Wiki, then sync
idlergear reference sync
# Local reference updated
```

### Wiki Link Syntax

References use wiki link syntax for cross-references:

```markdown
See [[API-Design]] for details.
Related: [[Architecture]], [[Getting-Started]]
```

## Note Sync

Notes sync as GitHub Issues with a special label.

### Configuration

```bash
idlergear config set backend.note github
```

### How It Works

- Notes are created as Issues with the `note` label
- Tags become additional labels
- Promotion to task removes the `note` label

### Example

```bash
# Create note
idlergear note create "Consider caching" --tag idea

# Sync
idlergear task sync  # Notes sync with tasks
# Creates issue with labels: note, idea

# Promote to task
idlergear note promote 1 --to task
# Removes 'note' label, becomes regular issue
```

## Vision Sync

Vision syncs as a VISION.md file in the repository root.

### Configuration

```bash
idlergear config set backend.vision github
```

### How It Works

- Pushes `.idlergear/vision.md` content to `VISION.md`
- Requires git commit and push

### Example

```bash
# Edit vision
idlergear vision edit

# Sync (creates/updates VISION.md)
idlergear vision sync

# Commit the file
git add VISION.md
git commit -m "Update project vision"
git push
```

## Plan Sync

Plans can sync with GitHub Projects v2.

### Configuration

```bash
idlergear config set backend.plan github
```

### Creating Linked Projects

```bash
# Create local project that syncs to GitHub
idlergear project create "Sprint 1" --create-on-github
```

### Syncing

```bash
idlergear project sync sprint-1
```

### Linking Existing Projects

```bash
# Link to GitHub Project number 5
idlergear project link sprint-1 5
```

## Conflict Resolution

When the same item is modified both locally and on GitHub:

### Tasks/Notes
- Last sync wins
- Newer timestamp takes precedence
- Manual review recommended for important changes

### References (Wiki)
- Git-based merge
- Conflicts shown in file
- Manual resolution required

### Best Practices

1. **Sync frequently** - Reduces conflict likelihood
2. **Single source of truth** - Decide if GitHub or local is primary
3. **Check before sync** - Review pending changes

## Troubleshooting

### "Not a GitHub repository"

Ensure you have a GitHub remote:

```bash
git remote add origin https://github.com/user/repo.git
```

### "Authentication failed"

Re-authenticate with GitHub CLI:

```bash
gh auth login
```

### "Wiki not enabled"

Enable wiki in repository settings:
1. Go to repository Settings
2. Features → Wikis → Enable

### "Sync failed: conflict"

Check the conflict:

```bash
idlergear reference show "Page Name"
```

Resolve manually and re-sync.

### Check Backend Status

```bash
idlergear config backend show
```

## Security

- **No tokens stored** - Uses `gh` CLI authentication
- **Local clones** - Wiki cloned to `.idlergear/.wiki/`
- **HTTPS by default** - Secure communication
- **Respects .gitignore** - `.idlergear/` typically ignored

## Limitations

- **Runs don't sync** - Logs are local only
- **No real-time sync** - Manual sync required
- **Single repo** - One GitHub repo per project
- **Wiki required** - Reference sync needs wiki enabled

## Related

- [[Getting-Started]] - Initial setup
- [[Commands-Reference]] - Sync commands
- [[Architecture]] - Backend system design
