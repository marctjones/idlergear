---
id: 47
title: Build idlergear pm MCP server (replace pm-mcp)
state: closed
created: '2026-01-07T02:31:09.730315Z'
labels:
- enhancement
- mcp-server
- python
- process-management
priority: medium
---
## Goal
Replace the Node.js pm-mcp process manager with a Python-native IdlerGear implementation.

## Why Replace?
- **Single runtime**: Pure Python, no Node.js needed
- **Better integration**: Use IdlerGear's existing run system
- **Consistency**: Same codebase as rest of IdlerGear
- **Extended features**: Task-aware process management

## Tools to Implement
Based on pm-mcp (https://github.com/patrickjm/pm-mcp):

### Core Process Management
1. **list_processes(filter)** - List running processes
2. **get_process(pid)** - Get process details
3. **kill_process(pid, signal)** - Stop process
4. **start_process(command, name)** - Start background process
5. **get_process_output(pid, stream)** - Get stdout/stderr
6. **get_system_info()** - CPU, memory, disk usage

### Enhanced Features
7. **list_runs()** - Show IdlerGear managed runs
8. **attach_run(name)** - Connect to existing run
9. **detach_run(name)** - Disconnect from run

## IdlerGear-Specific Extensions
10. **link_process_to_task(pid, task_id)** - Track which task started process
11. **task_processes(task_id)** - Show processes for task
12. **cleanup_task_processes(task_id)** - Stop all task processes

## Output Format
- **Structured JSON**: {pid, name, cpu, memory, status, command}
- **Filtered by default**: Exclude system processes unless requested
- **Token-optimized**: Only relevant fields

## Implementation Notes
- Use psutil library (cross-platform process management)
- Security: validate permissions before kill
- Integration with existing `idlergear run` commands
- Support signals: SIGTERM, SIGKILL, SIGINT

## Dependencies
- psutil (pip install psutil) - cross-platform
- Python stdlib

## Estimated Effort
~400-600 LOC, 4-5 hours

## References
- pm-mcp: https://github.com/patrickjm/pm-mcp
- psutil docs: https://psutil.readthedocs.io/
