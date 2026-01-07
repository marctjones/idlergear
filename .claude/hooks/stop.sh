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
    DECISIONS=$(grep -ciE "(decided to|we should|let\'s use)" "$TRANSCRIPT" 2>/dev/null || echo 0)

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
