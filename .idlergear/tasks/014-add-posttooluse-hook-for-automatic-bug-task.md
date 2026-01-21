---
id: 14
title: Add PostToolUse hook for automatic bug task creation from test failures
state: closed
created: '2026-01-03T05:33:57.520828Z'
labels:
- enhancement
- 'priority: high'
- 'effort: medium'
- core-v1
- 'component: integration'
priority: high
---
## Summary

Based on session analysis, 13.9% of commands are bug fixes, and users often paste terminal output for debugging. Add PostToolUse hook to detect test failures and auto-suggest creating bug tasks.

## Problem

Analysis of 72 Claude Code session transcripts shows:
- **13.9% of commands are bug fixes** (10 commands)
- Users paste terminal output for debugging (2x observed)
- Test failures require manual task creation
- Bug tracking is reactive, not automatic

Example from sessions:
> "the bench mark didnt finish successfully, my computer froze. what part of the benchmark is freezing"

## Proposed Solution

Enhance PostToolUse hook to detect test failures and suggest bug task creation.

### Implementation

Update `.claude/hooks/post-tool-use.sh`:

```bash
#!/bin/bash
# Detect test failures and suggest bug tasks

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_RESPONSE=$(echo "$INPUT" | jq -r '.tool_response')

SUGGESTIONS=""

# Detect test failures in Bash output
if [[ "$TOOL" == "Bash" ]]; then
  if echo "$TOOL_RESPONSE" | grep -qiE "(test.*failed|assertion.*failed|error:|FAILED|FAIL:)"; then
    # Extract failure details
    FAILURE_CONTEXT=$(echo "$TOOL_RESPONSE" | grep -iE "(test.*failed|assertion|error)" | head -3)
    
    SUGGESTIONS="Test failure detected:\n\n${FAILURE_CONTEXT}\n\n"
    SUGGESTIONS="${SUGGESTIONS}Consider creating a bug task:\n"
    SUGGESTIONS="${SUGGESTIONS}  idlergear task create \"Fix failing test\" --label bug\n\n"
  fi
  
  # Detect runtime errors
  if echo "$TOOL_RESPONSE" | grep -qiE "(traceback|exception|error:.*line)"; then
    ERROR_TYPE=$(echo "$TOOL_RESPONSE" | grep -oE "[A-Z][a-z]+Error" | head -1)
    SUGGESTIONS="${SUGGESTIONS}Runtime error detected: ${ERROR_TYPE}\n"
    SUGGESTIONS="${SUGGESTIONS}  idlergear task create \"Fix ${ERROR_TYPE}\" --label bug\n\n"
  fi
  
  # Detect benchmark/performance issues
  if echo "$TOOL_RESPONSE" | grep -qiE "(froze|freeze|hung|timeout)"; then
    SUGGESTIONS="${SUGGESTIONS}Performance issue detected (freeze/timeout)\n"
    SUGGESTIONS="${SUGGESTIONS}  idlergear task create \"Fix performance issue\" --label bug --label performance\n\n"
  fi
fi

# Output suggestions if any
if [ -n "$SUGGESTIONS" ]; then
  cat <<EOF
{
  "additionalContext": "${SUGGESTIONS}"
}
EOF
fi

exit 0
```

### Detection Patterns

| Pattern | Example | Suggested Task |
|---------|---------|----------------|
| Test failure | `test_parser.py FAILED` | "Fix failing test: test_parser" |
| Assertion error | `AssertionError: expected 5, got 3` | "Fix assertion in [module]" |
| Exception | `ValueError: invalid literal` | "Fix ValueError in [function]" |
| Freeze/timeout | "benchmark froze" | "Fix performance issue" --label performance |
| Traceback | `Traceback (most recent call last)` | "Fix [ExceptionType]" |

### Configuration

Update `.claude/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/post-tool-use.sh"
          }
        ]
      }
    ]
  }
}
```

### Smart Task Title Extraction

```bash
# Extract meaningful task title from error
extract_bug_title() {
  local OUTPUT="$1"
  
  # Try to get test name
  if echo "$OUTPUT" | grep -qE "test_[a-z_]+"; then
    TEST_NAME=$(echo "$OUTPUT" | grep -oE "test_[a-z_]+" | head -1)
    echo "Fix failing test: $TEST_NAME"
    return
  fi
  
  # Try to get exception type
  if echo "$OUTPUT" | grep -qE "[A-Z][a-z]+Error"; then
    ERROR=$(echo "$OUTPUT" | grep -oE "[A-Z][a-z]+Error" | head -1)
    echo "Fix $ERROR"
    return
  fi
  
  # Default
  echo "Fix test failure"
}
```

### Acceptance Criteria

- [ ] Detects pytest failures
- [ ] Detects unittest failures
- [ ] Detects assertion errors
- [ ] Detects runtime exceptions (ValueError, TypeError, etc.)
- [ ] Detects freeze/timeout issues
- [ ] Suggests meaningful task titles (includes test name or error type)
- [ ] Provides context in suggestion (error message snippet)
- [ ] Works for Python, JavaScript, Rust, Go test frameworks
- [ ] Doesn't spam on expected/handled errors
- [ ] Fast execution (< 50ms)

## Test Cases

### Test Failure
```bash
# Input: pytest output
# Output: "Fix failing test: test_parser_compound_words"
```

### Runtime Error
```bash
# Input: ValueError traceback
# Output: "Fix ValueError in parse_input"
```

### Performance Issue
```bash
# Input: "benchmark froze after 30s"
# Output: "Fix performance issue (freeze/timeout)" --label bug --label performance
```

## Related

- Session analysis: 13.9% of work is bug fixes
- Issue #8 (Implement PostToolUse hook for activity-based suggestions)
- Reference: "Claude Code Session Analysis - Common Command Patterns"
