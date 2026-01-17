# GitHub Label Conventions

IdlerGear integrates with GitHub Issues and uses labels to categorize and prioritize work. This guide explains the label conventions and how to use them effectively.

## Label Categories

### Priority Labels

Priority labels indicate the urgency and importance of tasks:

- **`priority:critical`** (Red `#B60205`) - Urgent issues requiring immediate attention
- **`priority:high`** (Orange `#D93F0B`) - Important issues to address soon
- **`priority:medium`** (Yellow `#FBCA04`) - Standard priority work
- **`priority:low`** (Light Gray `#C5DEF5`) - Nice-to-have improvements

### Type Labels

Type labels categorize the nature of the work:

- **`bug`** (Red `#D73A4A`) - Something isn't working correctly
- **`enhancement`** (Blue `#A2EEEF`) - New feature or improvement request
- **`documentation`** (Blue `#0075CA`) - Documentation updates or additions
- **`tech-debt`** (Brown `#D4C5F9`) - Technical debt or code quality improvements
- **`question`** (Pink `#D876E3`) - Questions needing clarification

### IdlerGear-Specific Labels

IdlerGear creates special labels for its knowledge types:

- **`exploration`** (Green `#0E8A16`) - Research tasks or investigations
- **`note`** (Yellow `#FBCA04`) - Quick notes or findings
- **`tag:*`** (Light Green `#C2E0C6`) - Note tags (e.g., `tag:explore`, `tag:idea`)

### Status Labels

Status labels indicate the state of an issue:

- **`wontfix`** (Gray `#FFFFFF`) - This will not be worked on
- **`duplicate`** (Gray `#CFD3D7`) - Duplicate of another issue
- **`help wanted`** (Green `#008672`) - Community contributions welcome
- **`good first issue`** (Purple `#7057FF`) - Good for newcomers

## How IdlerGear Uses Labels

### Mapping Knowledge Types to GitHub

IdlerGear maps its knowledge types to GitHub Issues using labels:

| Knowledge Type | GitHub Representation | Labels |
|----------------|----------------------|---------|
| Tasks | GitHub Issues | Any labels |
| Explorations | GitHub Issues | `exploration` |
| Notes | GitHub Issues | `note` + `tag:*` |

### Priority Mapping

When you create a task with a priority, IdlerGear automatically adds the corresponding label:

```bash
# Creates issue with priority:high label
idlergear task create "Fix critical bug" --priority high --label bug

# Creates issue with priority:medium label (default)
idlergear task create "Add new feature" --priority medium
```

### Label Validation

IdlerGear validates labels when creating tasks and notes:

```bash
# If label doesn't exist, you'll be prompted to create it
idlergear task create "New task" --label custom-label

# IdlerGear will ask:
# Label 'custom-label' does not exist. Create it? [Y/n]
```

## Setting Up Labels

### Initialize Standard Labels

Use the `ensure-standards` command to create all recommended labels:

```bash
# Creates 12 standard GitHub labels
idlergear label ensure-standards

# Dry-run to preview what would be created
idlergear label ensure-standards --dry-run
```

### List All Labels

```bash
# View all labels in the repository
idlergear label list
```

Output example:
```
Labels (15):
  bug                   [#D73A4A]  Something isn't working
  enhancement           [#A2EEEF]  New feature or request
  documentation         [#0075CA]  Improvements or additions to documentation
  priority:high         [#D93F0B]  High priority
  exploration           [#0E8A16]  IdlerGear exploration
  ...
```

### Create Custom Labels

```bash
# Create a new label with color and description
idlergear label create "team:backend" \
    --color "5319E7" \
    --description "Backend team issues"

# Create label (will prompt for color/description)
idlergear label create "area:api"
```

### Delete Labels

```bash
# Delete a label
idlergear label delete "old-label"

# Force delete (no confirmation)
idlergear label delete "old-label" --force
```

## Best Practices

### 1. Use Consistent Type Labels

Always tag issues with their type:

```bash
# Good: Clear type classification
idlergear task create "Fix login crash" --label bug --priority high
idlergear task create "Add dark mode" --label enhancement

# Bad: Missing type label
idlergear task create "Something to do"
```

### 2. Prefix Custom Categories

Use prefixes for custom label categories:

- `team:*` - Team ownership (e.g., `team:frontend`, `team:backend`)
- `area:*` - Product area (e.g., `area:auth`, `area:api`)
- `size:*` - Effort estimation (e.g., `size:small`, `size:large`)
- `tag:*` - Note categorization (e.g., `tag:explore`, `tag:idea`)

```bash
# Create team labels
idlergear label create "team:frontend" --color "1D76DB"
idlergear label create "team:backend" --color "5319E7"

# Use team labels
idlergear task create "Update UI components" --label team:frontend
```

### 3. Combine Priority and Type

Always combine priority with type for better filtering:

```bash
# Priority + type = clear categorization
idlergear task create "Database migration failing" \
    --label bug \
    --priority critical

idlergear task create "Add export feature" \
    --label enhancement \
    --priority medium
```

### 4. Use Tags for Notes

Use `tag:*` labels to categorize notes:

```bash
# Create note with explore tag
idlergear note create "How does the auth flow work?" --tag explore

# Create note with idea tag
idlergear note create "Could use Redis for caching" --tag idea
```

## Label Filtering

### Filter Tasks by Label

```bash
# Show all bugs
idlergear task list --label bug

# Show high-priority tasks
idlergear task list --label priority:high

# Combine filters (GitHub backend only)
gh issue list --label bug --label priority:critical
```

### Filter Notes by Tag

```bash
# Show exploration notes
idlergear note list --tag explore

# Show idea notes
idlergear note list --tag idea
```

## Color Conventions

IdlerGear follows GitHub's color conventions for semantic meaning:

| Color Family | Hex Range | Usage | Examples |
|--------------|-----------|-------|----------|
| Red | `#B60205` - `#D73A4A` | Critical, bugs, blockers | `priority:critical`, `bug` |
| Orange | `#D93F0B` | High priority, warnings | `priority:high` |
| Yellow | `#FBCA04` | Medium priority, notes | `priority:medium`, `note` |
| Blue | `#0075CA` - `#A2EEEF` | Features, documentation | `enhancement`, `documentation` |
| Green | `#0E8A16` - `#008672` | Good states, explorations | `exploration`, `help wanted` |
| Purple | `#5319E7` - `#7057FF` | Community, custom teams | `good first issue` |
| Gray | `#C5DEF5` - `#FFFFFF` | Low priority, closed states | `priority:low`, `wontfix` |

## Common Label Combinations

### Bug Triage Workflow

```bash
# New bug report
idlergear task create "App crashes on startup" --label bug

# After investigation, set priority
gh issue edit 123 --add-label priority:critical

# Assign to team
gh issue edit 123 --add-label team:mobile

# Mark as duplicate
gh issue close 123 --reason "not planned"
gh issue edit 123 --add-label duplicate
```

### Feature Planning

```bash
# New feature request
idlergear task create "Add user notifications" \
    --label enhancement \
    --priority medium

# During planning, add metadata
gh issue edit 124 --add-label area:notifications
gh issue edit 124 --add-label size:large
gh issue edit 124 --add-label team:backend
```

### Documentation Work

```bash
# Documentation tasks
idlergear task create "Update API docs" \
    --label documentation \
    --priority low

# Mark as good first issue for contributors
gh issue edit 125 --add-label "good first issue"
```

## Integration with GitHub Projects

Labels work seamlessly with GitHub Projects v2 for advanced filtering and views:

```bash
# In GitHub Projects, create views filtered by labels:
# - "High Priority Bugs" → label:bug AND label:priority:high
# - "Backend Work" → label:team:backend
# - "Good First Issues" → label:"good first issue"
```

## Troubleshooting

### Label Doesn't Exist

```bash
# Error: Label 'custom' not found
idlergear task create "Task" --label custom

# Solution: Create the label first
idlergear label create "custom" --color "1D76DB"

# Or use ensure-standards for common labels
idlergear label ensure-standards
```

### Wrong Priority Label

```bash
# Created with wrong priority
idlergear task create "Fix bug" --priority low

# Fix using gh CLI
gh issue edit 126 --remove-label priority:low
gh issue edit 126 --add-label priority:high
```

### Inconsistent Label Usage

```bash
# Audit labels across issues
gh issue list --json labels --jq '.[] | .labels[].name' | sort | uniq -c

# Fix inconsistencies
gh issue list --label "old-name" --json number --jq '.[].number' | \
    xargs -I {} gh issue edit {} --remove-label "old-name" --add-label "new-name"
```

## References

- [GitHub Labels Documentation](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels)
- [IdlerGear Label Commands](../README.md#label-commands)
- [GitHub Backend](../DESIGN.md#github-backend)
