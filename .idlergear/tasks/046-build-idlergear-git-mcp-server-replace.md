---
id: 46
title: Build idlergear git MCP server (replace cyanheads/git-mcp-server)
state: closed
created: '2026-01-07T02:31:09.716585Z'
labels:
- enhancement
- mcp-server
- python
- git
- github-integration
priority: high
---
## Goal
Replace the Node.js cyanheads/git-mcp-server with a Python-native IdlerGear implementation.

## Why Replace?
- **Single runtime**: Eliminate Node.js dependency
- **Task integration**: Link commits to IdlerGear tasks automatically
- **Better output**: Optimized for AI token efficiency
- **Consistency**: Same testing/deployment as IdlerGear
- **Customization**: Task-aware git operations

## Tools to Implement
Based on cyanheads server (https://github.com/cyanheads/git-mcp-server):

### Core Git Operations
1. **status(repo_path)** - Structured git status
2. **diff(repo_path, target, staged)** - Configurable diffs
3. **diff_unstaged(path, file)** - Unstaged changes
4. **diff_staged(path, file)** - Staged changes
5. **commit(path, message)** - Create commits
6. **add(path, files)** - Stage files
7. **reset(path, files)** - Unstage files
8. **log(path, max_count)** - Commit history
9. **show(path, revision)** - Show specific commit

### Advanced Operations
10. **create_branch(path, name)** - New branch
11. **checkout(path, ref)** - Switch branches
12. **merge(path, branch)** - Merge branches
13. **list_branches(path)** - All branches
14. **search_commits(path, query)** - Search history

## IdlerGear-Specific Extensions
15. **commit_task(task_id, message)** - Auto-link commit to task
16. **status_for_task(task_id)** - Filter status by task files
17. **task_commits(task_id)** - Show all commits for task
18. **sync_task_from_commits()** - Update tasks from commit messages

## Output Format
- **Dual mode**: JSON (default) or Markdown (for readability)
- **Configurable verbosity**: summary, normal, verbose
- **Token-optimized**: minimal noise, maximum signal

## Implementation Notes
- Use GitPython library (not subprocess)
- Security: validate repo paths
- Async-friendly design
- Conventional commit parsing

## Dependencies
- GitPython (pip install GitPython)
- Python stdlib

## Estimated Effort
~800-1000 LOC, 6-8 hours

## References
- cyanheads: https://github.com/cyanheads/git-mcp-server
- Official mcp-server-git: https://github.com/modelcontextprotocol/servers/blob/main/src/git/README.md
- Conventional Commits: https://www.conventionalcommits.org/
