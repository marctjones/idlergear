"""Claude Code hooks installation and management."""

import json
from pathlib import Path
from typing import Dict, List

# Hook script templates
SESSION_START_HOOK = '''#!/bin/bash
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
  "additionalContext": "=== IDLERGEAR PROJECT CONTEXT ===\\n\\n$CONTEXT\\n\\n=== END CONTEXT ===\\n\\nYou now have full project context loaded."
}
EOF
fi

exit 0
'''

PRE_TOOL_USE_HOOK = '''#!/bin/bash
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
    "TODO\\.md"
    "NOTES\\.md"
    "SESSION.*\\.md"
    "BACKLOG\\.md"
    "SCRATCH\\.md"
    "TASKS\\.md"
    "FEATURE_IDEAS\\.md"
    "RESEARCH\\.md"
)

# Check each pattern
for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    if echo "$FILE_PATH" | grep -qE "$pattern"; then
        # Extract base name for better error message
        BASENAME=$(basename "$FILE_PATH")

        # Suggest appropriate IdlerGear alternative
        case "$BASENAME" in
            TODO.md|TASKS.md|BACKLOG.md)
                ALTERNATIVE="idlergear task create \\"...\\""
                ;;
            NOTES.md|SCRATCH.md|SESSION*.md)
                ALTERNATIVE="idlergear note create \\"...\\""
                ;;
            FEATURE_IDEAS.md)
                ALTERNATIVE="idlergear note create \\"...\\" --tag idea"
                ;;
            RESEARCH.md)
                ALTERNATIVE="idlergear note create \\"...\\" --tag explore"
                ;;
            *)
                ALTERNATIVE="idlergear task create \\"...\\" or idlergear note create \\"...\\""
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
'''

STOP_HOOK = '''#!/bin/bash
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
    DECISIONS=$(grep -ciE "(decided to|we should|let\\'s use)" "$TRANSCRIPT" 2>/dev/null || echo 0)

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
  "reason": "$REASON_STR\\n\\nBefore stopping, consider:\\n  • Update task status: idlergear task update <id> --status completed\\n  • Capture discoveries: idlergear note create \\"...\\"\\n  • Document decisions: idlergear reference add \\"Decision: ...\\" --body \\"...\\"\\n  • Save session: idlergear session-save"
}
EOF
    exit 0
fi

# Approve stop
echo '{"decision": "approve"}'
exit 0
'''

HOOKS_JSON_TEMPLATE = {
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


def install_hooks(project_path: Path = None, force: bool = False) -> Dict[str, bool]:
    """
    Install Claude Code hooks for IdlerGear.

    Args:
        project_path: Project root (default: cwd)
        force: Overwrite existing hooks

    Returns:
        Dict of installed hooks
    """
    if project_path is None:
        project_path = Path.cwd()

    hooks_dir = project_path / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Install hook scripts
    hooks = {
        "session-start.sh": SESSION_START_HOOK,
        "pre-tool-use.sh": PRE_TOOL_USE_HOOK,
        "stop.sh": STOP_HOOK,
    }

    for filename, content in hooks.items():
        hook_path = hooks_dir / filename

        if hook_path.exists() and not force:
            results[filename] = False  # Skipped
            continue

        hook_path.write_text(content)
        hook_path.chmod(0o755)  # Make executable
        results[filename] = True  # Installed

    # Install/update hooks.json
    hooks_json_path = project_path / ".claude" / "hooks.json"

    if hooks_json_path.exists() and not force:
        # Merge with existing
        existing = json.loads(hooks_json_path.read_text())
        # TODO: Smart merge
        results["hooks.json"] = False
    else:
        hooks_json_path.write_text(json.dumps(HOOKS_JSON_TEMPLATE, indent=2))
        results["hooks.json"] = True

    return results


def test_hooks(project_path: Path = None) -> Dict[str, Dict[str, any]]:
    """
    Test installed hooks.

    Returns:
        Dict of test results
    """
    import subprocess

    if project_path is None:
        project_path = Path.cwd()

    hooks_dir = project_path / ".claude" / "hooks"
    results = {}

    # Test SessionStart
    session_start = hooks_dir / "session-start.sh"
    if session_start.exists():
        result = subprocess.run(
            [str(session_start)],
            input='{"session_id":"test","source":"startup"}',
            capture_output=True,
            text=True,
            cwd=project_path
        )
        results["session-start"] = {
            "exists": True,
            "executable": session_start.stat().st_mode & 0o111 != 0,
            "exit_code": result.returncode,
            "output_length": len(result.stdout)
        }
    else:
        results["session-start"] = {"exists": False}

    # Test PreToolUse (should block TODO.md)
    pre_tool_use = hooks_dir / "pre-tool-use.sh"
    if pre_tool_use.exists():
        test_input = json.dumps({
            "tool_name": "Write",
            "tool_input": {"file_path": "TODO.md"}
        })
        result = subprocess.run(
            [str(pre_tool_use)],
            input=test_input,
            capture_output=True,
            text=True,
            cwd=project_path
        )
        results["pre-tool-use"] = {
            "exists": True,
            "executable": pre_tool_use.stat().st_mode & 0o111 != 0,
            "exit_code": result.returncode,
            "blocks_forbidden": result.returncode == 2,
            "error_message": result.stderr[:200] if result.stderr else ""
        }
    else:
        results["pre-tool-use"] = {"exists": False}

    # Test Stop
    stop = hooks_dir / "stop.sh"
    if stop.exists():
        result = subprocess.run(
            [str(stop)],
            input='{}',
            capture_output=True,
            text=True,
            cwd=project_path
        )
        results["stop"] = {
            "exists": True,
            "executable": stop.stat().st_mode & 0o111 != 0,
            "exit_code": result.returncode,
            "valid_json": result.stdout.strip().startswith("{")
        }
    else:
        results["stop"] = {"exists": False}

    return results


def list_hooks(project_path: Path = None) -> List[Dict[str, any]]:
    """List installed hooks with status."""
    if project_path is None:
        project_path = Path.cwd()

    hooks_dir = project_path / ".claude" / "hooks"

    if not hooks_dir.exists():
        return []

    hooks = []
    for hook_file in hooks_dir.glob("*.sh"):
        stat = hook_file.stat()
        hooks.append({
            "name": hook_file.name,
            "path": str(hook_file),
            "executable": stat.st_mode & 0o111 != 0,
            "size": stat.st_size,
            "modified": stat.st_mtime
        })

    return hooks
