# MANDATORY: Check Suggestions File (File-Based IPC)

## Background

Level 2 enforcement hooks write suggestions to a file because `additionalContext` may not be delivered to Claude by Claude Code infrastructure.

## REQUIRED ACTION

**Every 5 tool uses, you MUST run:**

```bash
cat /tmp/idlergear-suggestions-$(echo $CLAUDE_SESSION_ID | head -c 8).txt 2>/dev/null || echo "No suggestions"
```

Or more simply:

```bash
ls -t /tmp/idlergear-suggestions-*.txt 2>/dev/null | head -1 | xargs cat 2>/dev/null
```

## What to Do With Suggestions

When you see suggestions in the file:

1. **File annotation reminders** - Annotate the file immediately with `idlergear_file_annotate`
2. **Test failure reminders** - Create bug task with `idlergear task create`
3. **Commit reminders** - Review changes and commit
4. **Message notifications** - Check messages with `idlergear_message_list`

## Workflow

```
1. Use Read tool
2. (Hook writes suggestion to file)
3. After 5 tools, check file
4. Act on suggestions
5. Continue work
```

## Why This Is Necessary

- `additionalContext` from hooks not reaching Claude (issue #396)
- File-based IPC is the workaround
- Hooks write to `/tmp/idlergear-suggestions-{session_id}.txt`
- You must proactively check it

## When to Check

- Every 5 tool uses (Read, Edit, Write, Bash, Grep count)
- After reading source files
- Before committing
- When starting new work

## Example

```bash
# Check for suggestions
cat /tmp/idlergear-suggestions-*.txt 2>/dev/null

# Output might show:
# === 14:32:45 - After Read ===
# 📝 RECOMMENDED: Annotate context.py for 93% token savings!
# ...

# Act on it:
idlergear_file_annotate(path="src/idlergear/context.py", ...)
```

**This is NOT optional. Check the file regularly.**
