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
