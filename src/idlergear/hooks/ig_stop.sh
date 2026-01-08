#!/bin/bash
# Prompt for knowledge capture before ending session
# FAST VERSION: Reads files directly instead of calling CLI

# Check if IdlerGear is initialized
if [ ! -d ".idlergear" ]; then
    echo '{"decision": "approve"}'
    exit 0
fi

# Check for in-progress tasks by looking at task files
IN_PROGRESS=0
if [ -d ".idlergear/tasks" ]; then
    # Look for status: in_progress in frontmatter
    IN_PROGRESS=$(grep -l "status:.*in_progress" .idlergear/tasks/*.md 2>/dev/null | wc -l)
fi

# Decide whether to block
if [ "$IN_PROGRESS" -gt 0 ]; then
    cat <<EOF
{
  "decision": "block",
  "reason": "${IN_PROGRESS} task(s) still in progress.\n\nBefore stopping, consider:\n  • Update task status: idlergear task close <id>\n  • Capture discoveries: idlergear note create \"...\"\n  • Save session: idlergear session save"
}
EOF
    exit 0
fi

# Approve stop
echo '{"decision": "approve"}'
exit 0
