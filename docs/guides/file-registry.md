# File Registry & Deprecated File Detection

## Overview

The IdlerGear file registry is a **proactive knowledge management system** that tracks file status and annotations to help AI assistants work with the right files. It solves a common problem in AI-assisted development: **AI agents accessing outdated or deprecated files**.

### The Problem

When multiple AI agents work on a project over time:
- Data scientists create improved datasets but forget to delete old versions
- Developers refactor code and leave `_old.py` files around
- AI assistants grep for files and unknowingly use deprecated versions
- Token waste from analyzing wrong files
- Bugs from using stale data

### The Solution

The file registry provides:
- **Status tracking**: Mark files as current/deprecated/archived/problematic
- **File annotations**: Describe file purpose, tags, components for efficient discovery
- **Version links**: Connect deprecated files to their successors
- **Token-efficient search**: Find the right file in ~200 tokens vs 15,000 tokens (grep + reading files)
- **Multi-agent coordination**: Registry updates broadcast to all active agents via daemon

## Quick Start

### Basic Usage

```bash
# Mark a file as deprecated with a successor
idlergear file deprecate old_data.csv --successor data.csv --reason "Fixed label errors"

# Check file status
idlergear file status data.csv
# Output: current

idlergear file status old_data.csv
# Output: deprecated → data.csv (Fixed label errors)

# List all deprecated files
idlergear file list --status deprecated
```

### Annotation-Based Discovery

```bash
# Annotate a file after creating it
idlergear file annotate src/api/auth.py \
  --description "REST API endpoints for user authentication, JWT generation, session management" \
  --tags api,auth,endpoints,jwt \
  --components AuthController,TokenManager,login \
  --related src/models/user.py

# Search for files efficiently (200 tokens vs 15,000!)
idlergear file search --query "authentication"
# Returns: src/api/auth.py with description and metadata

# Find files by tags
idlergear file search --tags auth,api

# Find files by component name
idlergear file search --components AuthController
```

## Core Concepts

### File Status

Every registered file has one of four statuses:

| Status | Meaning | Use Case |
|--------|---------|----------|
| **current** | Active, should be used | Current implementation, latest data |
| **deprecated** | Outdated, has successor | Old code, previous dataset version |
| **archived** | Historical, not for work | Experiments, old prototypes |
| **problematic** | Known issues, use cautiously | Buggy code, suspect data |

### File Annotations

Annotations enable **token-efficient file discovery**:

```python
{
    "path": "src/api/auth.py",
    "description": "REST API endpoints for authentication...",
    "tags": ["api", "auth", "endpoints", "jwt"],
    "components": ["AuthController", "TokenManager", "login"],
    "related_files": ["src/models/user.py"]
}
```

**Benefits:**
- AI searches annotations (~200 tokens) instead of grep + reading files (~15,000 tokens)
- 93% token savings on file discovery
- Faster, more accurate file finding

## CLI Command Reference

### `idlergear file register`

Register a file with explicit status.

```bash
idlergear file register <path> --status <current|deprecated|archived|problematic> [--reason "..."]

# Examples
idlergear file register data.csv --status current
idlergear file register old_api.py --status archived --reason "Replaced by REST API"
```

**Options:**
- `<path>` - File path relative to project root
- `--status` - File status (required)
- `--reason` - Optional reason for status

### `idlergear file deprecate`

Mark a file as deprecated with an optional successor.

```bash
idlergear file deprecate <path> [--successor <path>] [--reason "..."]

# Examples
idlergear file deprecate training_data_v1.csv \
  --successor training_data_v2.csv \
  --reason "Fixed data quality issues"

idlergear file deprecate api_old.py \
  --successor api.py \
  --reason "Refactored to async/await"
```

**Options:**
- `<path>` - File to deprecate
- `--successor` - Path to current version (optional)
- `--reason` - Reason for deprecation (optional)

### `idlergear file status`

Show the status of a file.

```bash
idlergear file status <path>

# Output examples
# current
# deprecated → data_v2.csv (Fixed label errors)
# archived (Historical experiments)
```

### `idlergear file list`

List all registered files, optionally filtered by status.

```bash
idlergear file list [--status <status>]

# Examples
idlergear file list                    # All files
idlergear file list --status deprecated  # Only deprecated
idlergear file list --status current     # Only current
```

### `idlergear file annotate`

Annotate a file with description, tags, components, and related files for token-efficient discovery.

```bash
idlergear file annotate <path> \
  [--description "..."] \
  [--tags tag1,tag2,...] \
  [--components Component1,Component2,...] \
  [--related file1.py,file2.py,...]

# Example
idlergear file annotate src/services/payment.py \
  --description "Payment processing service: Stripe integration, refunds, webhooks" \
  --tags payment,stripe,service,webhooks \
  --components PaymentService,StripeClient,WebhookHandler \
  --related src/models/transaction.py,src/api/billing.py
```

**When to annotate:**
1. ✅ After creating a new file - Annotate immediately with purpose
2. ✅ After reading a file to understand it - Capture that knowledge
3. ✅ When refactoring - Update annotations to stay accurate
4. ✅ Instead of grep for finding files - Search annotations first

### `idlergear file search`

Search files by description text, tags, components, or status (token-efficient alternative to grep).

```bash
idlergear file search [--query "text"] [--tags tag1,tag2] [--components Component1] [--status <status>]

# Examples
idlergear file search --query "authentication"
idlergear file search --tags api,auth
idlergear file search --components UserController
idlergear file search --status current --tags api
```

**Returns:** File paths with descriptions and metadata (~200 tokens vs 15,000 for grep + reading files)

### `idlergear file unregister`

Remove a file from the registry.

```bash
idlergear file unregister <path>
```

## MCP Tool Reference

AI assistants can use these MCP tools directly:

### `idlergear_file_register`

```python
{
    "path": "data.csv",
    "status": "current",
    "reason": "Latest dataset"
}
```

### `idlergear_file_deprecate`

```python
{
    "path": "old_data.csv",
    "successor": "data.csv",
    "reason": "Fixed validation errors"
}
```

### `idlergear_file_status`

```python
{
    "path": "data.csv"
}
# Returns: {"status": "current", "successor": null, "reason": null}
```

### `idlergear_file_list`

```python
{
    "status": "deprecated"  # optional filter
}
# Returns: [{"path": "...", "status": "...", ...}, ...]
```

### `idlergear_file_annotate`

```python
{
    "path": "src/api/auth.py",
    "description": "REST API endpoints for authentication",
    "tags": ["api", "auth", "endpoints"],
    "components": ["AuthController", "login"],
    "related_files": ["src/models/user.py"]
}
```

### `idlergear_file_search`

```python
{
    "query": "authentication",        # optional
    "tags": ["api", "auth"],          # optional
    "components": ["AuthController"], # optional
    "status": "current"               # optional
}
# Returns: [{"path": "...", "description": "...", "tags": [...], ...}, ...]
```

### `idlergear_file_get_annotation`

```python
{
    "path": "src/api/auth.py"
}
# Returns: {"path": "...", "description": "...", "tags": [...], "components": [...], ...}
```

### `idlergear_file_list_tags`

```python
{}  # No parameters
# Returns: {"api": {"count": 5, "files": ["...", ...]}, "auth": {...}, ...}
```

## Workflow Examples

### Workflow 1: Data Versioning

**Scenario:** Data scientist creates improved dataset

```bash
# Create new version
cp training_data.csv training_data_v1.csv
# ... improve data: fix labels, add validation, clean nulls ...
mv improved_data.csv training_data.csv

# Deprecate old version
idlergear file deprecate training_data_v1.csv \
  --successor training_data.csv \
  --reason "Fixed label errors, added validation, cleaned nulls"

# Annotate current version
idlergear file annotate training_data.csv \
  --description "Training dataset for model v2: 10K samples, validated labels, no nulls" \
  --tags data,training,ml \
  --components ModelTrainer
```

**Result:** AI assistants will always use `training_data.csv` and know why the old version was deprecated.

### Workflow 2: Code Refactoring

**Scenario:** Developer refactors API to async/await

```bash
# Keep old version temporarily for reference
git mv api.py api_old.py

# Write new async version
# ... create new api.py ...

# Deprecate old synchronous version
idlergear file deprecate api_old.py \
  --successor api.py \
  --reason "Refactored to async/await pattern for better performance"

# Annotate new version
idlergear file annotate api.py \
  --description "Async REST API: user endpoints, authentication, rate limiting" \
  --tags api,async,rest \
  --components UserAPI,AuthMiddleware \
  --related src/models/user.py,src/auth/jwt.py

# After testing, delete old version
rm api_old.py
idlergear file unregister api_old.py
```

### Workflow 3: Archiving Experiments

**Scenario:** Archive old experiments that shouldn't be used for new work

```bash
# Move experiments to archive
mkdir -p archive/experiments
mv experiment_*.py archive/experiments/

# Mark all as archived
for file in archive/experiments/*.py; do
  idlergear file register "$file" \
    --status archived \
    --reason "Historical experiments, not for new work"
done
```

### Workflow 4: Token-Efficient File Discovery

**Scenario:** AI needs to find authentication code

```bash
# INEFFICIENT: grep + read multiple files (15,000 tokens)
grep -r "authentication" . | head -10
cat src/api/auth.py src/services/auth.py src/models/user.py
# AI reads 3 files (~15,000 tokens)

# EFFICIENT: search annotations (200 tokens, 93% savings!)
idlergear file search --query "authentication"
# Returns: {
#   "path": "src/api/auth.py",
#   "description": "REST API endpoints for authentication, JWT generation",
#   "tags": ["api", "auth", "jwt"]
# }
# AI reads only the right file (~5,000 tokens total)
```

### Workflow 5: Multi-Agent Coordination

**Scenario:** Multiple AI agents working on the project

```bash
# Terminal 1: Start daemon for multi-agent coordination
idlergear daemon start

# Terminal 2: Claude Code (auto-registers as agent)
# AI creates new dataset version
idlergear file deprecate data.csv --successor data_v2.csv

# Terminal 3: Another AI agent (Aider, Cursor, etc.)
# Immediately receives notification via daemon:
# 📢 File Registry Update
#    data.csv has been deprecated
#    → Use data_v2.csv instead
#    Reason: Fixed validation errors
```

## Configuration

Edit `.idlergear/config.toml`:

```toml
[file_registry]
# Enable/disable file registry (default: true)
enabled = true

# Block vs warn on deprecated file access (default: true = block)
strict_mode = true

# Cache TTL in seconds (default: 60)
cache_ttl = 60

# Access log retention in days (default: 30)
log_retention_days = 30

# Auto-deprecate patterns (files matching these are auto-deprecated on scan)
auto_patterns = [
  "*.bak",
  "*_old.*",
  "*_backup.*",
  "*_deprecated.*",
]

# Auto-archived directories (contents marked as archived on scan)
auto_archived_dirs = [
  "archive/",
  "old/",
  "backup/",
  "deprecated/",
]
```

## Best Practices

### 1. Annotate Proactively

✅ **DO:** Annotate files immediately when creating or understanding them
```bash
# After creating auth.py
idlergear file annotate src/api/auth.py \
  --description "REST API authentication endpoints" \
  --tags api,auth
```

❌ **DON'T:** Skip annotations and rely on grep later

### 2. Search Annotations Before Grep

✅ **DO:** Search annotations first (93% token savings)
```bash
idlergear file search --query "authentication"
```

❌ **DON'T:** Use grep as first resort (wastes tokens)

### 3. Always Link Successors

✅ **DO:** Link deprecated files to their replacements
```bash
idlergear file deprecate old.py --successor new.py --reason "Refactored"
```

❌ **DON'T:** Deprecate without indicating what to use instead

### 4. Provide Deprecation Reasons

✅ **DO:** Explain why a file was deprecated
```bash
--reason "Fixed data quality issues, added validation"
```

❌ **DON'T:** Leave future developers guessing

### 5. Clean Up Eventually

✅ **DO:** Delete deprecated files after a grace period
```bash
# After 2 weeks
rm old_data.csv
idlergear file unregister old_data.csv
```

❌ **DON'T:** Let deprecated files accumulate indefinitely

## Troubleshooting

### "File not found in registry"

**Cause:** Registry is opt-in. Files must be explicitly registered or annotated.

**Solution:**
```bash
# Register the file
idlergear file register data.csv --status current

# Or annotate it (auto-registers as current)
idlergear file annotate data.csv --description "Training data"
```

### "False positive - need to access archived file"

**Cause:** File is marked archived but you need to read it.

**Solution:**
```bash
# Change status to current if it should be used
idlergear file register old_data.csv --status current

# Or update the registry entry to problematic with a note
idlergear file register old_data.csv --status problematic \
  --reason "Use cautiously: known data quality issues"
```

### "Registry out of sync between agents"

**Cause:** Daemon not running, so updates aren't broadcast to other agents.

**Solution:**
```bash
# Check daemon status
idlergear daemon status

# Start if not running
idlergear daemon start

# Agents will now receive real-time registry updates
```

### "How do I find all files with a specific tag?"

**Solution:**
```bash
# Search by tag
idlergear file search --tags api

# Or list all tags
idlergear file list-tags
```

### "Can I bulk-annotate files?"

**Solution:**
```bash
# Use a shell script
for file in src/api/*.py; do
  idlergear file annotate "$file" \
    --tags api,endpoints \
    --components "$(basename $file .py)"
done
```

## Integration with Other Tools

### With Claude Code

Claude Code's MCP integration automatically uses file registry tools. When Claude searches for files, it:
1. Checks annotations first (token-efficient)
2. Falls back to grep only if needed
3. Never accesses deprecated files without warning

### With Aider

Add to `.aider.conf.yml`:
```yaml
read:
  - .idlergear/file-registry.json  # Aider reads registry

conventions: |
  Check file status before editing:
  `idlergear file status <file>`

  Search annotations before grep:
  `idlergear file search --query "..."`
```

### With Cursor IDE

Cursor rules automatically include file registry commands in context.

### With Daemon

Enable multi-agent coordination:
```bash
# Start daemon
idlergear daemon start

# All agents receive registry updates in real-time
# Agent A deprecates a file → Agent B immediately notified
```

## Advanced Usage

### Custom Status Workflows

```bash
# Mark file as problematic during investigation
idlergear file register buggy_code.py --status problematic \
  --reason "Memory leak under investigation"

# After fix, mark as current
idlergear file register buggy_code.py --status current
```

### Related File Networks

```bash
# Build knowledge graph of related files
idlergear file annotate src/api/users.py \
  --related src/models/user.py,src/auth/jwt.py,tests/test_users.py

idlergear file annotate src/models/user.py \
  --related src/api/users.py,src/db/schema.py

# Search finds the network
idlergear file search --query "user management"
# Returns users.py with related_files showing the full context
```

### Component-Based Search

```bash
# Annotate with class/function names
idlergear file annotate src/services/payment.py \
  --components PaymentService,StripeClient,RefundHandler

# Find all files containing a specific component
idlergear file search --components PaymentService
```

## See Also

- [File Registry Workflow Examples](../examples/file-registry-workflow.md)
- [MCP Tools Reference](../../src/idlergear/skills/idlergear/references/mcp-tools.md)
- [Multi-Agent Coordination](./daemon.md)
- [Token Efficiency Best Practices](./token-efficiency.md)
