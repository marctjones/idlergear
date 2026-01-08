#!/bin/bash
# Auto-inject IdlerGear context at session start
# FAST VERSION: Reads files directly instead of calling CLI

# Check if IdlerGear is initialized
if [ ! -d ".idlergear" ]; then
    exit 0  # Silent exit if not an IdlerGear project
fi

# Start daemon if not running (background, no output)
if command -v idlergear &>/dev/null; then
    idlergear daemon start &>/dev/null &
fi

# Build context by reading files directly (no Python startup overhead)
CONTEXT=""

# Read vision
if [ -f ".idlergear/vision/VISION.md" ]; then
    VISION=$(cat ".idlergear/vision/VISION.md" 2>/dev/null | head -20)
    if [ -n "$VISION" ]; then
        CONTEXT="${CONTEXT}## Vision\n${VISION}\n\n"
    fi
fi

# Count open tasks
TASK_COUNT=0
if [ -d ".idlergear/tasks" ]; then
    TASK_COUNT=$(ls -1 ".idlergear/tasks/"*.md 2>/dev/null | wc -l)
fi

if [ "$TASK_COUNT" -gt 0 ]; then
    CONTEXT="${CONTEXT}## Open Tasks: ${TASK_COUNT}\n"
    # Show first 5 task titles (from YAML frontmatter)
    for f in $(ls -1t ".idlergear/tasks/"*.md 2>/dev/null | head -5); do
        TITLE=$(grep "^title:" "$f" 2>/dev/null | head -1 | sed "s/^title: *['\"]*//" | sed "s/['\"]* *$//")
        if [ -n "$TITLE" ]; then
            CONTEXT="${CONTEXT}- ${TITLE}\n"
        fi
    done
    CONTEXT="${CONTEXT}\n"
fi

# Count notes
NOTE_COUNT=0
if [ -d ".idlergear/notes" ]; then
    NOTE_COUNT=$(ls -1 ".idlergear/notes/"*.md 2>/dev/null | wc -l)
fi

if [ "$NOTE_COUNT" -gt 0 ]; then
    CONTEXT="${CONTEXT}## Recent Notes: ${NOTE_COUNT}\n\n"
fi

# Output context if any
if [ -n "$CONTEXT" ]; then
    # Escape for JSON
    CONTEXT_ESCAPED=$(echo -e "$CONTEXT" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | tr '\n' '\\' | sed 's/\\/\\n/g')
    cat <<EOF
{
  "additionalContext": "=== IDLERGEAR PROJECT ===\\n\\n${CONTEXT_ESCAPED}\\nRun 'idlergear context' for full details.\\n=== END ==="
}
EOF
fi

exit 0
