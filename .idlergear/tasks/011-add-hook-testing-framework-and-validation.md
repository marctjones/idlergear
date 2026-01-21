---
id: 11
title: Add hook testing framework and validation
state: closed
created: '2026-01-03T05:23:29.953022Z'
labels:
- testing
- 'priority: high'
- 'effort: medium'
- 'component: integration'
priority: high
---
## Summary

Create testing framework for IdlerGear hooks to validate behavior, performance, and error handling before deployment.

## Problem

Hooks run in production Claude Code sessions. Bugs in hooks can:
- Break Claude Code workflows
- Create infinite loops
- Block legitimate operations
- Leak sensitive information

Need comprehensive testing before rollout.

## Proposed Solution

### Test Framework

Create `tests/test_hooks.py`:

```python
import json
import subprocess
from pathlib import Path

def test_hook(hook_script: Path, input_data: dict) -> dict:
    """Test a hook with JSON input."""
    result = subprocess.run(
        [hook_script],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=5
    )
    
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

def test_session_start_hook():
    """Test SessionStart hook."""
    hook = Path(".claude/hooks/session-start.sh")
    
    # Test: Normal startup
    result = test_hook(hook, {
        "session_id": "test-123",
        "source": "startup",
        "cwd": str(Path.cwd())
    })
    
    assert result["exit_code"] == 0
    assert "PROJECT CONTEXT" in result["stdout"]
    
    # Test: IdlerGear not initialized
    # Should exit 0 gracefully
    
def test_pre_tool_use_hook():
    """Test PreToolUse hook."""
    hook = Path(".claude/hooks/pre-tool-use.sh")
    
    # Test: Forbidden file (should block)
    result = test_hook(hook, {
        "tool_name": "Write",
        "tool_input": {"file_path": "TODO.md", "content": "..."}
    })
    
    assert result["exit_code"] == 2  # Blocking error
    assert "Forbidden file" in result["stderr"]
    
    # Test: Allowed file (should pass)
    result = test_hook(hook, {
        "tool_name": "Write",
        "tool_input": {"file_path": "src/main.py", "content": "..."}
    })
    
    assert result["exit_code"] == 0
```

### Manual Testing Script

Create `test-hooks-manual.sh`:

```bash
#!/bin/bash
# Manual testing of hooks

echo "Testing SessionStart hook..."
echo '{"session_id":"test","source":"startup"}' | ./.claude/hooks/session-start.sh

echo -e "\n\nTesting PreToolUse hook (forbidden file)..."
echo '{"tool_name":"Write","tool_input":{"file_path":"TODO.md"}}' | ./.claude/hooks/pre-tool-use.sh

echo -e "\n\nTesting PreToolUse hook (allowed file)..."
echo '{"tool_name":"Write","tool_input":{"file_path":"src/main.py"}}' | ./.claude/hooks/pre-tool-use.sh

echo -e "\n\nTesting Stop hook..."
echo '{"session_id":"test","stop_hook_active":false}' | ./.claude/hooks/stop.sh
```

### Performance Testing

```bash
# Measure hook execution time
time echo '{"session_id":"test"}' | ./.claude/hooks/session-start.sh

# Should be < 100ms for most hooks
# Should be < 500ms for SessionStart
```

### Acceptance Criteria

- [ ] Unit tests for all hook scripts
- [ ] Test valid inputs (happy path)
- [ ] Test invalid inputs (error handling)
- [ ] Test edge cases (missing IdlerGear, empty data)
- [ ] Performance benchmarks (< 100ms target)
- [ ] Timeout testing (hooks must complete)
- [ ] Exit code validation (0, 2 for blocking)
- [ ] JSON output validation
- [ ] Integration tests with Claude Code (manual)

## Test Cases

### SessionStart
- [ ] Startup source
- [ ] Resume source  
- [ ] Clear source
- [ ] Compact source
- [ ] IdlerGear not initialized
- [ ] Context command fails

### PreToolUse
- [ ] Each forbidden file pattern
- [ ] Allowed files
- [ ] Write tool
- [ ] Edit tool
- [ ] Missing file_path
- [ ] Non-file tools

### Stop
- [ ] In-progress tasks exist
- [ ] No in-progress tasks
- [ ] Transcript analysis
- [ ] Already stopped (stop_hook_active=true)

### PostToolUse
- [ ] Edit count tracking
- [ ] Test failure detection
- [ ] Git commit detection
- [ ] Session isolation

## Related

- All hook implementation issues (#117-#123)
- Integration strategy reference
