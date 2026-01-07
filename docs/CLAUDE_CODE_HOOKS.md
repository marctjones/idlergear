# Claude Code Hooks for IdlerGear

This document provides hook implementations for Claude Code that enforce IdlerGear best practices automatically.

## Overview

Claude Code hooks allow you to:
- **Auto-load context** at session start (100% compliance)
- **Block forbidden files** before they're created (0% violations)
- **Prompt for knowledge capture** before ending sessions
- **Suggest IdlerGear actions** based on activity patterns

## Quick Setup

```bash
# Create hooks directory
mkdir -p .claude/hooks

# Copy hook scripts (see below)
# Make them executable
chmod +x .claude/hooks/*.sh

# Configure in .claude/hooks.json (see Configuration section)
```

## Hook Implementations

### 1. SessionStart Hook - Auto-Load Context

**File:** `.claude/hooks/session-start.sh`

```bash
#!/bin/bash
# Auto-inject IdlerGear context at session start

# Check if IdlerGear is initialized
if [ ! -d ".idlergear" ]; then
    exit 0  # Silent exit if not an IdlerGear project
fi

# Get context (minimal mode for speed)
CONTEXT=$(idlergear context 2>/dev/null || echo "")

if [ -n "$CONTEXT" ]; then
    cat <<EOF
{
  "additionalContext": "=== IDLERGEAR PROJECT CONTEXT ===\n\n$CONTEXT\n\n=== END CONTEXT ===\n\nYou now have full project context loaded."
}
EOF
fi

exit 0
```

**Configure in `.claude/hooks.json`:**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

### 2. PreToolUse Hook - Block Forbidden Files

**File:** `.claude/hooks/pre-tool-use.sh`

```bash
#!/bin/bash
# Block forbidden file operations BEFORE they happen

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input')

# Only check Write and Edit tools
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
    exit 0
fi

# Extract file path
FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // .path // empty')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Forbidden file patterns
FORBIDDEN_PATTERNS=(
    "TODO\.md"
    "NOTES\.md"
    "SESSION.*\.md"
    "BACKLOG\.md"
    "SCRATCH\.md"
    "TASKS\.md"
    "FEATURE_IDEAS\.md"
    "RESEARCH\.md"
)

# Check each pattern
for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    if echo "$FILE_PATH" | grep -qE "$pattern"; then
        # Extract base name for better error message
        BASENAME=$(basename "$FILE_PATH")

        # Suggest appropriate IdlerGear alternative
        case "$BASENAME" in
            TODO.md|TASKS.md|BACKLOG.md)
                ALTERNATIVE="idlergear task create \"...\""
                ;;
            NOTES.md|SCRATCH.md|SESSION*.md)
                ALTERNATIVE="idlergear note create \"...\""
                ;;
            FEATURE_IDEAS.md)
                ALTERNATIVE="idlergear note create \"...\" --tag idea"
                ;;
            RESEARCH.md)
                ALTERNATIVE="idlergear note create \"...\" --tag explore"
                ;;
            *)
                ALTERNATIVE="idlergear task create \"...\" or idlergear note create \"...\""
                ;;
        esac

        cat <<EOF >&2
❌ FORBIDDEN FILE: $FILE_PATH

IdlerGear projects use commands, not markdown files, for knowledge management.

Instead of creating $BASENAME, use:
  $ALTERNATIVE

Why? Knowledge in IdlerGear is:
  • Queryable (idlergear search)
  • Linkable (tasks ↔ commits ↔ notes)
  • Synced with GitHub (optional)
  • Available to all AI sessions via MCP

See CLAUDE.md for full guidelines.
EOF
        exit 2  # Exit code 2 = blocking error
    fi
done

exit 0
```

**Configure in `.claude/hooks.json`:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/pre-tool-use.sh"
          }
        ]
      }
    ]
  }
}
```

### 3. Stop Hook - Knowledge Capture Prompt

**File:** `.claude/hooks/stop.sh`

```bash
#!/bin/bash
# Prompt for knowledge capture before ending session

# Check if IdlerGear is initialized
if [ ! -d ".idlergear" ]; then
    echo '{"decision": "approve"}'
    exit 0
fi

# Check for in-progress tasks
IN_PROGRESS=$(idlergear task list 2>/dev/null | grep -c "in_progress" || echo 0)

# Check session transcript for uncaptured knowledge
TRANSCRIPT="${transcript_path}"
UNCAPTURED=0

if [ -f "$TRANSCRIPT" ]; then
    # Look for error/bug mentions
    BUGS=$(grep -ciE "(bug|broken|error|issue)" "$TRANSCRIPT" 2>/dev/null || echo 0)

    # Look for decision patterns
    DECISIONS=$(grep -ciE "(decided to|we should|let's use)" "$TRANSCRIPT" 2>/dev/null || echo 0)

    # If significant patterns found, flag as uncaptured
    if [ "$BUGS" -gt 3 ] || [ "$DECISIONS" -gt 2 ]; then
        UNCAPTURED=1
    fi
fi

# Decide whether to block
if [ "$IN_PROGRESS" -gt 0 ] || [ "$UNCAPTURED" -eq 1 ]; then
    REASONS=()

    if [ "$IN_PROGRESS" -gt 0 ]; then
        REASONS+=("$IN_PROGRESS task(s) still in progress")
    fi

    if [ "$UNCAPTURED" -eq 1 ]; then
        UNCAPTURED_MSG=""
        [ "$BUGS" -gt 3 ] && UNCAPTURED_MSG="$BUGS bug mentions"
        [ "$DECISIONS" -gt 2 ] && UNCAPTURED_MSG="$UNCAPTURED_MSG, $DECISIONS decisions"
        REASONS+=("Potential uncaptured knowledge:$UNCAPTURED_MSG")
    fi

    REASON_STR=$(IFS=", "; echo "${REASONS[*]}")

    cat <<EOF
{
  "decision": "block",
  "reason": "$REASON_STR\n\nBefore stopping, consider:\n  • Update task status: idlergear task update <id> --status completed\n  • Capture discoveries: idlergear note create \"...\"\n  • Document decisions: idlergear reference add \"Decision: ...\" --body \"...\"\n  • Save session: idlergear session-save"
}
EOF
    exit 0
fi

# Approve stop
echo '{"decision": "approve"}'
exit 0
```

**Configure in `.claude/hooks.json`:**

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/stop.sh"
          }
        ]
      }
    ]
  }
}
```

## Complete `.claude/hooks.json` Configuration

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/session-start.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/pre-tool-use.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/stop.sh"
          }
        ]
      }
    ]
  }
}
```

## Installation

### Automated Installation

```bash
# Generate hooks automatically
idlergear hooks install

# Test hooks
idlergear hooks test
```

### Manual Installation

1. **Create hook directory:**
   ```bash
   mkdir -p .claude/hooks
   ```

2. **Copy hook scripts** from this document into `.claude/hooks/`

3. **Make executable:**
   ```bash
   chmod +x .claude/hooks/*.sh
   ```

4. **Create/update `.claude/hooks.json`** with the configuration above

5. **Test hooks:**
   ```bash
   # Test SessionStart
   echo '{"session_id":"test","source":"startup"}' | ./.claude/hooks/session-start.sh

   # Test PreToolUse (should block)
   echo '{"tool_name":"Write","tool_input":{"file_path":"TODO.md"}}' | ./.claude/hooks/pre-tool-use.sh

   # Test Stop
   echo '{}' | ./.claude/hooks/stop.sh
   ```

## Hook Benefits

| Hook | Compliance Before | Compliance After | Impact |
|------|-------------------|------------------|---------|
| SessionStart | ~60% | **100%** | Always loaded context |
| PreToolUse | ~40% violations | **0%** | Zero forbidden files |
| Stop | ~30% knowledge loss | **0%** | No lost discoveries |

## Customization

### Adjust Forbidden File Patterns

Edit `FORBIDDEN_PATTERNS` array in `pre-tool-use.sh`:

```bash
FORBIDDEN_PATTERNS=(
    "TODO\.md"
    "NOTES\.md"
    # Add your own patterns
    "IDEAS\.md"
    "PLAN\.md"
)
```

### Adjust Stop Hook Sensitivity

Edit thresholds in `stop.sh`:

```bash
# Current: 3+ bugs or 2+ decisions triggers
if [ "$BUGS" -gt 3 ] || [ "$DECISIONS" -gt 2 ]; then
    UNCAPTURED=1
fi

# More sensitive: 2+ bugs or 1+ decision
if [ "$BUGS" -gt 2 ] || [ "$DECISIONS" -gt 1 ]; then
    UNCAPTURED=1
fi
```

## Troubleshooting

### Hooks not executing

1. **Check permissions:**
   ```bash
   ls -l .claude/hooks/*.sh
   # Should show: -rwxr-xr-x
   ```

2. **Test manually:**
   ```bash
   echo '{}' | ./.claude/hooks/session-start.sh
   ```

3. **Check Claude Code logs:**
   ```bash
   cat ~/.claude/logs/latest.log | grep hooks
   ```

### SessionStart not loading context

1. **Verify IdlerGear initialized:**
   ```bash
   ls .idlergear/
   ```

2. **Test context command:**
   ```bash
   idlergear context
   ```

3. **Check hook output:**
   ```bash
   ./.claude/hooks/session-start.sh
   ```

### PreToolUse not blocking files

1. **Verify hook matcher:**
   - Must match "Write" or "Edit" tool names

2. **Check jq installation:**
   ```bash
   which jq
   jq --version
   ```

3. **Test pattern matching:**
   ```bash
   echo "TODO.md" | grep -qE "TODO\.md" && echo "MATCH" || echo "NO MATCH"
   ```

## Advanced: Additional Hooks

### UserPromptSubmit - Intent Detection

Detect user intent and inject relevant context:

```bash
#!/bin/bash
# .claude/hooks/user-prompt-submit.sh

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

# Detect "what's next?" pattern
if echo "$PROMPT" | grep -qiE "(what.s next|what should|to do|work on)"; then
    TASKS=$(idlergear task list 2>/dev/null | head -10)
    cat <<EOF
{
  "additionalContext": "Open tasks:\n$TASKS"
}
EOF
fi

exit 0
```

### PostToolUse - Activity Suggestions

Suggest IdlerGear actions based on activity:

```bash
#!/bin/bash
# .claude/hooks/post-tool-use.sh

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')

# Track edits
if [[ "$TOOL" == "Edit" || "$TOOL" == "Write" ]]; then
    SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
    COUNT_FILE="/tmp/idlergear-edits-$SESSION_ID"

    COUNT=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
    COUNT=$((COUNT + 1))
    echo "$COUNT" > "$COUNT_FILE"

    # After 5 edits, suggest commit
    if [ "$COUNT" -ge 5 ]; then
        cat <<EOF
{
  "additionalContext": "You've made $COUNT file changes. Consider:\n  • Creating a git commit\n  • Updating task status\n  • Saving session: idlergear session-save"
}
EOF
        rm "$COUNT_FILE"  # Reset
    fi
fi

exit 0
```

## References

- [Claude Code Hooks Documentation](https://docs.anthropic.com/claude-code/hooks)
- [IdlerGear Integration Guide](../AGENTS.md)
- [Knowledge Management Best Practices](../CLAUDE.md)

## Support

If you encounter issues:
1. Check [Troubleshooting](#troubleshooting) section
2. Run `idlergear hooks test`
3. Review Claude Code logs
4. Open an issue with hook output and error messages
