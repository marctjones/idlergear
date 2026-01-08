#!/bin/bash
# UserPromptSubmit hook - Detect implementation commands and suggest task creation
# FAST VERSION: Avoids CLI calls, uses simple pattern matching only

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)

if [ -z "$PROMPT" ]; then
    exit 0
fi

ADDITIONAL_CONTEXT=""

# Pattern: Implementation command (implement, add, create, build, write, make)
if echo "$PROMPT" | grep -qiE "^(implement|add|create|build|write|make|develop|fix) "; then
    # Extract feature name (first 5 words after the verb)
    FEATURE=$(echo "$PROMPT" | sed -E 's/^(implement|add|create|build|write|make|develop|fix) //i' | cut -d' ' -f1-5)

    ADDITIONAL_CONTEXT="${ADDITIONAL_CONTEXT}📋 Implementation request: \"${FEATURE}\"\n"
    ADDITIONAL_CONTEXT="${ADDITIONAL_CONTEXT}Consider: idlergear task create \"${FEATURE}\"\n\n"
fi

# Pattern: User asks about next steps
if echo "$PROMPT" | grep -qiE "(what.s next|what should|to do|work on|continue|where did we)"; then
    # Count open tasks from files (fast)
    TASK_COUNT=0
    if [ -d ".idlergear/tasks" ]; then
        TASK_COUNT=$(ls -1 ".idlergear/tasks/"*.md 2>/dev/null | wc -l)
    fi
    if [ "$TASK_COUNT" -gt 0 ]; then
        ADDITIONAL_CONTEXT="${ADDITIONAL_CONTEXT}📌 You have ${TASK_COUNT} open task(s). Run: idlergear task list\n\n"
    fi
fi

# Pattern: User mentions bugs or errors
if echo "$PROMPT" | grep -qiE "(bug|broken|error|issue|problem|failing|doesn.t work)"; then
    ADDITIONAL_CONTEXT="${ADDITIONAL_CONTEXT}🐛 Bug/error mentioned. When identified:\n"
    ADDITIONAL_CONTEXT="${ADDITIONAL_CONTEXT}  idlergear task create \"Fix: <description>\" --label bug\n\n"
fi

# Output additional context if any
if [ -n "$ADDITIONAL_CONTEXT" ]; then
    # Escape for JSON
    CONTEXT_ESCAPED=$(echo -e "$ADDITIONAL_CONTEXT" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | tr '\n' ' ' | sed 's/  */ /g')
    cat <<EOF
{
  "additionalContext": "${CONTEXT_ESCAPED}"
}
EOF
fi

exit 0
