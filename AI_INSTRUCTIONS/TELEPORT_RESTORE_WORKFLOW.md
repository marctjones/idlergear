# Teleport Restore Integration with IdlerGear

## Overview

Claude Code for web includes a **teleport restore** feature that allows you to seamlessly transfer your web-based coding session to your local CLI environment. This document describes how to integrate teleport restore with IdlerGear's existing hybrid local/web workflows.

## What is Teleport Restore?

Teleport restore is a feature in Claude Code web that:
- **Copies chat transcripts** from web to local CLI
- **Transfers edited files** to your local repository
- **Preserves session context** for continuity
- **Enables hybrid workflows** between web and CLI environments

When you run `claude --teleport <uuid>` locally, it:
1. Downloads the complete chat history from the web session
2. Applies all file changes to your local repository
3. Continues the conversation thread in your local CLI

## Integration with IdlerGear Workflows

IdlerGear already supports hybrid local/web development through the `idlergear sync` commands. Teleport restore complements this workflow by providing a **session-level restore** in addition to IdlerGear's **repository-level sync**.

### Workflow Comparison

| Feature | IdlerGear Sync | Claude Teleport |
|---------|----------------|-----------------|
| **Direction** | Bidirectional (push/pull) | Web → Local only |
| **What's Transferred** | All files including uncommitted | Chat transcript + edited files |
| **Use Case** | Share work between LLM tools | Continue web session locally |
| **Granularity** | Repository-wide | Session-specific |
| **Session Context** | Manual (via messages) | Automatic (chat history) |

### Recommended Hybrid Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Start on Web (Claude Code Web)                   │
├─────────────────────────────────────────────────────────────┤
│  1. Check out your project on claude.ai                    │
│  2. Work on features, make changes                         │
│  3. When ready to move to local, use teleport              │
└─────────────────────────────────────────────────────────────┘
                          ↓
                          ↓ claude --teleport <uuid>
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Continue Locally (Claude CLI + IdlerGear)        │
├─────────────────────────────────────────────────────────────┤
│  1. Run teleport command to download session               │
│  2. Review changes, run tests locally                      │
│  3. Use IdlerGear commands for project management          │
│  4. Capture logs: idlergear logs run --name teleport-dev   │
└─────────────────────────────────────────────────────────────┘
                          ↓
                          ↓ idlergear sync push
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Back to Web (Optional)                           │
├─────────────────────────────────────────────────────────────┤
│  1. Push local changes to sync branch                      │
│  2. Check out sync branch on web                           │
│  3. Continue work in web environment                       │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Integration Guide

### 1. **Working on Claude Code Web**

Start your development session on claude.ai:

```bash
# On claude.ai web interface:
# - Clone or check out your repository
# - Work on features with Claude Code web
# - Make changes across multiple files
# - Test and iterate
```

### 2. **Prepare for Teleport**

When you're ready to move to local:

1. **Copy the teleport command** from Claude Code web interface
   - Look for the teleport button/link
   - Copy the command: `claude --teleport <uuid>`

2. **Optional: Document the session** (IdlerGear enhancement)
   ```bash
   # Create a teleport session record (future feature)
   echo "{
     \"session_id\": \"<uuid>\",
     \"timestamp\": \"$(date -Iseconds)\",
     \"branch\": \"$(git branch --show-current)\",
     \"description\": \"Feature development from web session\"
   }" > .idlergear/teleport-sessions/<uuid>.json
   ```

### 3. **Execute Teleport Restore Locally**

Run the teleport command in your local environment:

```bash
# Navigate to your local repository
cd /path/to/your/project

# Execute teleport command (as copied from web)
claude --teleport <uuid>

# This will:
# - Download chat transcript
# - Apply file changes to your local repo
# - Start Claude CLI with session context
```

### 4. **Post-Teleport Integration with IdlerGear**

After teleport completes, integrate with IdlerGear workflows:

#### A. **Review Project Status**
```bash
# Check what changed during web session
idlergear status

# Review uncommitted changes
git status
git diff
```

#### B. **Capture Logs for Continued Development**
```bash
# If you continue development locally, capture logs
idlergear logs run --name post-teleport-dev --command "npm run dev"

# Or pipe existing process output
./run.sh | idlergear logs pipe --name teleport-session
```

#### C. **Generate Context for Other LLMs**
```bash
# Create context for other LLM tools (Gemini, Cursor, etc.)
idlergear context --format markdown > .idlergear/teleport-context.md

# Or use JSON for programmatic access
idlergear context --format json > .idlergear/teleport-context.json
```

#### D. **Send Messages to Other LLMs**
```bash
# Inform other LLM collaborators about teleport session
# (Future IdlerGear command)
idlergear messages send \
  --from claude-web \
  --to gemini-local \
  --type message \
  --body "Teleported web session <uuid>. Review changes in commit abc123."
```

### 5. **Commit Changes from Teleport Session**

Review and commit the changes that came from the web session:

```bash
# Review all changes
git status
git diff

# Add changes
git add .

# Commit with reference to teleport session
git commit -m "feat: Add feature X (teleported from web session <uuid>)"

# Push to remote
git push origin your-branch
```

### 6. **Optional: Push to Sync Branch for Web Access**

If you need to go back to web after local changes:

```bash
# Push all local changes to sync branch
idlergear sync push --include-untracked

# On claude.ai web:
# - Check out the sync branch (e.g., idlergear-web-sync-main)
# - Continue development with full local changes available
```

## Advanced Workflows

### Workflow 1: Web → Teleport → Local → Web Round Trip

```bash
# Start: Working on web
# (make changes on claude.ai)

# Step 1: Teleport to local
claude --teleport <uuid-1>

# Step 2: Continue locally with IdlerGear
idlergear logs run --name local-dev --command "pytest tests/"
git commit -am "fix: Address test failures from web session"

# Step 3: Push back to web
idlergear sync push --include-untracked

# Step 4: Continue on web
# (check out sync branch on claude.ai)

# Step 5: Later, teleport again
claude --teleport <uuid-2>
```

### Workflow 2: Multi-LLM Collaboration with Teleport

```bash
# Claude Web does initial implementation
# (work on claude.ai)

# Step 1: Teleport to local
claude --teleport <uuid>

# Step 2: Create context for Gemini
idlergear context --format markdown > context.md

# Step 3: Ask Gemini to review via file-based message
cat > .idlergear/messages/$(uuidgen).json <<EOF
{
  "from": "claude-web",
  "to": "gemini-local",
  "type": "question",
  "timestamp": "$(date -Iseconds)",
  "body": "Teleported session <uuid>. Please review authentication logic in src/auth.py:150-200",
  "context_file": ".idlergear/teleport-context.md"
}
EOF

# Step 4: Gemini reads and responds
# (gemini reads message, reviews code, writes response)

# Step 5: Commit final version
git commit -am "feat: Authentication with peer review"
```

### Workflow 3: Teleport Session Log Management

```bash
# After teleport, create a session log
# (Future IdlerGear feature)

idlergear teleport log \
  --session-id <uuid> \
  --description "Feature X development" \
  --files-changed "src/auth.py,tests/test_auth.py" \
  --branch $(git branch --show-current)

# List all teleport sessions
idlergear teleport list

# Export teleport session info
idlergear teleport show --session <uuid> --format json
```

## Best Practices

### 1. **Always Review After Teleport**
```bash
# Don't blindly accept teleported changes
git status
git diff
idlergear check  # Run best practices check
```

### 2. **Commit Immediately After Teleport**
```bash
# Create a clean commit boundary
git commit -am "chore: Teleport session <uuid>"

# Or review and commit selectively
git add -p  # Interactive staging
git commit -m "feat: Specific feature from web session"
```

### 3. **Document Web Session Context**
```bash
# Add session notes to commit message
git commit -m "feat: Add user authentication

Teleported from web session <uuid>
- Implemented JWT-based auth
- Added password hashing
- Created login/logout endpoints

Related: #123"
```

### 4. **Use IdlerGear Logs for Continued Development**
```bash
# After teleport, if continuing development locally
idlergear logs run --name post-teleport \
  --command "npm run test:watch"

# Logs will be in .idlergear/logs/ for future debugging
```

### 5. **Coordinate with Other LLMs**
```bash
# After teleport, notify other LLM collaborators
idlergear messages send \
  --from claude-web \
  --to all \
  --body "Teleported session <uuid>. Core auth implemented. Ready for testing phase."
```

### 6. **Clean Up After Teleport**
```bash
# If teleport created temporary files
git clean -n  # Preview what will be removed
git clean -f  # Remove untracked files

# Or add them to .gitignore if needed
echo "*.teleport.tmp" >> .gitignore
```

## Known Issues and Workarounds

### Issue 1: Teleport 400 Error (Tool Use Concurrency)

**Problem:** Sometimes `claude --teleport <uuid>` fails with "API Error: 400 due to tool use concurrency issues"

**Workaround:**
```bash
# Retry the teleport command
claude --teleport <uuid>

# If it continues to fail, use IdlerGear sync as alternative
# (on claude.ai web, commit your changes first, then):
idlergear sync pull
```

### Issue 2: Teleported Files Conflict with Local Changes

**Problem:** Teleport tries to apply changes to files you've modified locally

**Workaround:**
```bash
# Before teleport, commit or stash local changes
git stash push -m "Local work before teleport"

# Run teleport
claude --teleport <uuid>

# Review conflicts and merge
git stash pop
# (resolve conflicts manually)
```

### Issue 3: Teleport Session Loses Context

**Problem:** Chat transcript doesn't include full project context

**Workaround:**
```bash
# After teleport, regenerate full context
idlergear context --format markdown

# Provide to Claude CLI if continuing conversation
cat .idlergear/context.md | pbcopy  # macOS
cat .idlergear/context.md | xclip   # Linux
```

## Future IdlerGear Enhancements

### Planned Features

1. **Teleport Session Tracking**
   ```bash
   idlergear teleport log --session <uuid>
   idlergear teleport list
   idlergear teleport show <uuid>
   ```

2. **Automatic Message Creation on Teleport**
   ```bash
   # Auto-create message for other LLMs when teleporting
   idlergear config set auto_message_on_teleport true
   ```

3. **Teleport + Sync Merge Tool**
   ```bash
   # Merge teleported changes with sync branch
   idlergear teleport merge --sync-branch idlergear-web-sync-main
   ```

4. **Teleport Session Restore**
   ```bash
   # Re-apply a previous teleport session
   idlergear teleport restore --session <uuid>
   ```

## Integration Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Claude Code Web (claude.ai)                 │
├────────────────────────────────────────────────────────────────┤
│  - Interactive web IDE                                         │
│  - Chat-based development                                      │
│  - Generates teleport command                                  │
└────────────────────────────────────────────────────────────────┘
                          ↓
                          ↓ claude --teleport <uuid>
                          ↓ (Downloads chat + files)
                          ↓
┌────────────────────────────────────────────────────────────────┐
│                    Local Repository                            │
├────────────────────────────────────────────────────────────────┤
│  ├── src/                  (teleported changes applied)        │
│  ├── tests/                (teleported changes applied)        │
│  ├── .idlergear/                                              │
│  │   ├── logs/             (capture continued dev)            │
│  │   ├── messages/         (coordinate with other LLMs)       │
│  │   ├── teleport-sessions/  (track teleport history)         │
│  │   └── config.toml       (IdlerGear settings)               │
│  └── git history           (commit teleported changes)         │
└────────────────────────────────────────────────────────────────┘
                          ↓
                          ↓ idlergear sync push
                          ↓ (optional: back to web)
                          ↓
┌────────────────────────────────────────────────────────────────┐
│                    Sync Branch (GitHub)                        │
├────────────────────────────────────────────────────────────────┤
│  - idlergear-web-sync-main                                    │
│  - Contains all local changes                                  │
│  - Can be checked out on claude.ai                            │
└────────────────────────────────────────────────────────────────┘
```

## Quick Reference

### Common Commands

```bash
# Teleport from web to local
claude --teleport <uuid>

# Check status after teleport
idlergear status
git status

# Capture logs for continued dev
idlergear logs run --name dev --command "npm start"

# Generate context for other LLMs
idlergear context --format markdown

# Send message to collaborators
idlergear messages send --to gemini-local --body "Teleported session <uuid>"

# Commit changes
git commit -am "feat: Changes from web session <uuid>"

# Push to sync branch for web
idlergear sync push --include-untracked

# Pull sync branch locally
idlergear sync pull

# Check sync status
idlergear sync status
```

### Typical Session Flow

```bash
# 1. Start on web (claude.ai)
# 2. Copy teleport command when ready to move local
# 3. Execute locally:
cd ~/projects/myproject
claude --teleport abc-123-def

# 4. Review and integrate:
idlergear status
git status
git diff

# 5. Continue development:
idlergear logs run --name dev --command "npm run dev"

# 6. Commit:
git commit -am "feat: Feature from web session abc-123-def"

# 7. Optional: Push back to web
idlergear sync push
```

## Summary

**Teleport restore** integrates seamlessly with IdlerGear's hybrid workflows:

- ✅ **Use teleport** to move active web sessions to local CLI
- ✅ **Use IdlerGear sync** to share repository state between environments
- ✅ **Use IdlerGear logs** to capture continued development after teleport
- ✅ **Use IdlerGear messages** to coordinate between multiple LLMs
- ✅ **Commit teleported changes** with clear session references

This combination provides the best of both worlds:
- **Session-level continuity** (teleport)
- **Repository-level coordination** (sync)
- **Multi-LLM collaboration** (messages)
- **Structured logging** (logs)
- **Project context** (status/context/check)

The result is a powerful hybrid workflow that lets you work seamlessly across web and local environments with multiple LLM coding assistants.
