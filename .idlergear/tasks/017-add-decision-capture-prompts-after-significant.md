---
id: 17
title: Add decision capture prompts after significant implementation
state: open
created: '2026-01-03T05:33:59.314184Z'
labels:
- enhancement
- 'priority: medium'
- 'effort: medium'
- 'component: integration'
priority: medium
---
## Summary

Based on session analysis, only 1.4% of commands are documentation-related, despite 36% being implementation work. Need prompts to capture design decisions and architectural choices.

## Problem

Analysis of 72 Claude Code session transcripts shows:
- **Only 1.4% of commands are documentation** (1 command out of 72)
- **36.1% are implementation commands** (26 commands)
- Documentation/decision capture is severely underutilized
- Design decisions get lost in conversation

## Proposed Solution

Add decision capture prompts triggered by implementation patterns.

### 1. Detect Decision-Making Patterns

Add to PostToolUse hook:

```bash
#!/bin/bash
# Detect decision-making conversations

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')

# For Bash tool or file operations
if [[ "$TOOL" =~ (Bash|Write|Edit) ]]; then
  # Check recent transcript for decision indicators
  if [ -f "$TRANSCRIPT" ]; then
    RECENT=$(tail -200 "$TRANSCRIPT")
    
    # Decision patterns
    DECISION_INDICATORS=(
      "we should"
      "let's use"
      "decided to"
      "chose"
      "approach"
      "instead of"
      "vs\."
      "trade-?off"
      "because"
      "reason"
    )
    
    DECISION_COUNT=0
    for pattern in "${DECISION_INDICATORS[@]}"; do
      COUNT=$(echo "$RECENT" | grep -ciE "$pattern" || echo 0)
      DECISION_COUNT=$((DECISION_COUNT + COUNT))
    done
    
    # If multiple decision indicators, suggest documenting
    if [ "$DECISION_COUNT" -ge 3 ]; then
      cat <<EOF
{
  "additionalContext": "Design decisions detected in recent conversation (${DECISION_COUNT} decision indicators).\n\nConsider documenting this decision:\n  idlergear reference add \"Decision: [title]\" --body \"...\"\n\nExample:\n  idlergear reference add \"Decision: Use PostgreSQL over MySQL\" --body \"Chose PostgreSQL because: 1) Better JSON support, 2) More robust concurrency, 3) Team experience\""
}
EOF
    fi
  fi
fi

exit 0
```

### 2. UserPromptSubmit - Detect "Which Should We Use?" Questions

```bash
# Pattern: User asking for architectural advice
if echo "$PROMPT" | grep -qiE "(which should|what should|should we use|better to|recommend)"; then
  cat <<EOF
{
  "additionalContext": "Architectural decision question detected.\n\nAfter deciding, document the choice:\n  idlergear reference add \"Decision: [what was chosen]\" --body \"Rationale: ...\""
}
EOF
fi
```

### 3. Stop Hook - Check for Undocumented Decisions

Add to stop hook:

```bash
#!/bin/bash
# Check for undocumented decisions before stopping

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')

if [ -f "$TRANSCRIPT" ]; then
  RECENT=$(tail -500 "$TRANSCRIPT")
  
  # Count decision indicators
  DECISION_COUNT=$(echo "$RECENT" | grep -ciE "(decided|chose|let's use|approach|instead of)" || echo 0)
  
  # Count reference additions in this session
  REF_COUNT=$(echo "$RECENT" | grep -ciE "idlergear.*reference.*add" || echo 0)
  
  # If decisions made but no references added
  if [ "$DECISION_COUNT" -ge 2 ] && [ "$REF_COUNT" -eq 0 ]; then
    cat <<EOF
{
  "decision": "block",
  "reason": "Design decisions detected (${DECISION_COUNT} indicators) but no references created. Document key decisions before stopping?"
}
EOF
    exit 0
  fi
fi

echo '{"decision": "approve"}'
exit 0
```

### 4. Decision Template Generation

Create helper for generating decision references:

```bash
idlergear reference add-decision() {
  local TITLE="$1"
  local CHOSEN="$2"
  local ALTERNATIVES="$3"
  local RATIONALE="$4"
  
  BODY=$(cat <<EOF
# Decision: ${TITLE}

## Chosen Approach
${CHOSEN}

## Alternatives Considered
${ALTERNATIVES}

## Rationale
${RATIONALE}

## Date
$(date +%Y-%m-%d)

## Context
[Link to issue/discussion if applicable]
EOF
)
  
  idlergear reference add "Decision: ${TITLE}" --body "$BODY"
}
```

### 5. Decision Pattern Examples

Trigger prompts for these patterns:

| Pattern | Example | Suggested Action |
|---------|---------|------------------|
| Architecture choice | "Use microservices vs monolith" | Document decision |
| Library selection | "React vs Vue" | Document why chosen |
| Design pattern | "Factory pattern for this" | Document pattern choice |
| Data structure | "Use HashMap instead of Array" | Document trade-offs |
| Algorithm choice | "Binary search vs linear" | Document reasoning |
| Infrastructure | "Deploy to AWS vs GCP" | Document pros/cons |

### 6. MCP Tool

```python
def prompt_decision_capture(context: str):
    """Prompt user to document a decision."""
    return {
        "reminder": "Consider documenting this decision as a reference",
        "context": context,
        "command": "idlergear reference add \"Decision: [title]\" --body \"...\""
    }
```

## Acceptance Criteria

- [ ] Detects decision-making conversations (3+ decision indicators)
- [ ] Prompts to document after implementation with decisions
- [ ] Detects "which should we use" questions
- [ ] Stop hook blocks if decisions made but not documented
- [ ] Helper command for decision reference template
- [ ] MCP tool for decision capture prompts
- [ ] Configurable sensitivity (decision indicator threshold)
- [ ] Examples in documentation

## Related

- Session analysis: Only 1.4% documentation vs 36% implementation
- Issue #6 (Implement Stop hook)
- Issue #8 (PostToolUse hook enhancements)
- Reference: "Claude Code Session Analysis - Common Command Patterns"
