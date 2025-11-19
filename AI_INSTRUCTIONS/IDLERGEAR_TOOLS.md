# IdlerGear Tools Reference

**Purpose:** Complete guide to all IdlerGear tools available for LLM assistants including Goose, Claude, Gemini CLI, and others.

---

## Quick Start

IdlerGear provides tools via:
1. **CLI commands** - Direct shell invocation
2. **MCP protocol** - Programmatic access for MCP-compatible LLM tools
3. **Message passing** - Async communication between LLM environments

---

## Project Management Tools

### status
Get comprehensive project health status.

```bash
idlergear status
idlergear status --path /path/to/project
```

**MCP Tool:** `project_status`

Returns:
- Git state (branch, uncommitted changes, recent commits)
- Charter document freshness
- LLM-managed branches
- Project location and name

### context
Generate LLM-ready project context.

```bash
idlergear context
idlergear context --format json
idlergear context --output context.md
```

**MCP Tool:** `project_context`

Returns all charter documents, recent activity, and project structure formatted for LLM consumption.

### check
Analyze project for best practice adherence.

```bash
idlergear check
```

**MCP Tool:** `project_check`

Checks for:
- Missing tests
- Stale documentation
- Excessive uncommitted changes
- Dangling branches

---

## Sync Tools (Multi-Environment Coordination)

### sync push
Push current state to web sync branch.

```bash
idlergear sync push
idlergear sync push --include-untracked
```

**MCP Tool:** `sync_push`

### sync pull
Pull changes from web sync branch.

```bash
idlergear sync pull
idlergear sync pull --no-cleanup
```

**MCP Tool:** `sync_pull`

### sync status
Check sync branch status.

```bash
idlergear sync status
```

**MCP Tool:** `sync_status`

---

## Logging Tools

Capture, stream, and analyze logs from scripts and processes.

### Run with Capture
```bash
idlergear logs run --command "./run.sh" --name my-app
```

**MCP Tool:** `logs_run`

### Pipe from stdin
```bash
./script.sh 2>&1 | idlergear logs pipe --name my-app
```

**MCP Tool:** `logs_pipe`

### Multi-Terminal Streaming
```bash
# Terminal 1: Start server
idlergear logs serve --name debug

# Terminal 2: Stream to server
./run.sh 2>&1 | idlergear logs stream --to debug
```

**MCP Tools:** `logs_serve`, `logs_stream`

### Remote Streaming
```bash
# Local machine
idlergear logs serve --name debug --port 9999

# Remote machine
./run.sh 2>&1 | idlergear logs stream --to 192.168.1.100:9999
```

### Follow Logs
```bash
idlergear logs follow --session 1
```

**MCP Tool:** `logs_follow`

### List/Show/Export
```bash
idlergear logs list
idlergear logs show --session 1
idlergear logs show --session 1 --tail 50
idlergear logs export --session 1 --output debug.log
```

**MCP Tools:** `logs_list`, `logs_show`, `logs_export`

### Pull from Observability Systems
```bash
# Grafana Loki
idlergear logs pull-loki --loki http://loki:3100 --query '{app="myapp"}' --since 1h
```

**MCP Tool:** `logs_pull_loki`

### Cleanup
```bash
idlergear logs cleanup --days 7
```

**MCP Tool:** `logs_cleanup`

---

## Message Passing Tools

Send and receive messages between LLM environments via git sync branches.

### Send Message
```bash
idlergear message send --to web --body "Please review auth.py"
```

**MCP Tool:** `message_send`

### List Messages
```bash
idlergear message list
idlergear message list --unread
idlergear message list --filter-to local
```

**MCP Tool:** `message_list`

### Read Message
```bash
idlergear message read --id msg-123
```

**MCP Tool:** `message_read`

### Respond to Message
```bash
idlergear message respond --id msg-123 --body "Changes made"
```

**MCP Tool:** `message_respond`

---

## Coordination Repository Tools

Use a private GitHub repo for cross-environment communication.

### Initialize
```bash
idlergear coord init
```

**MCP Tool:** `coord_init`

### Send via Coord Repo
```bash
# File-based (default)
idlergear coord send --project my-app --message "Review auth"

# Issue-based
idlergear coord send --project my-app --message "Fix tests" --via issue
```

**MCP Tool:** `coord_send`

### Read from Coord Repo
```bash
idlergear coord read --project my-app
idlergear coord read --project my-app --via issue
```

**MCP Tool:** `coord_read`

---

## Teleport Tools

Manage Claude Code web teleport sessions for live testing.

### Prepare for Teleport
```bash
idlergear teleport prepare
idlergear teleport prepare --branch feature-x
```

**MCP Tool:** `teleport_prepare`

Stashes local changes, fetches remote, and checks out the target branch.

### Watch Session
```bash
idlergear teleport watch
idlergear teleport watch --command "./my-script.sh"
idlergear teleport watch --auto-restart
```

**MCP Tool:** `teleport_watch`

Watches for code changes and notifies you to run the command.

### Finish Teleport
```bash
idlergear teleport finish
```

**MCP Tool:** `teleport_finish`

Merges to main, cleans up branches, pushes, and restores stash.

### Session Management
```bash
# Log a session
idlergear teleport log --session-id abc123 --description "Auth feature"

# List sessions
idlergear teleport list

# Show session details
idlergear teleport show --session-id abc123

# Export session
idlergear teleport export --session-id abc123 --format json
```

**MCP Tools:** `teleport_log`, `teleport_list`, `teleport_show`, `teleport_export`

### Restore Stash
```bash
idlergear teleport restore-stash
```

**MCP Tool:** `teleport_restore_stash`

---

## Eddi Tools (Tor Hidden Services & Messaging)

eddi provides two main tools:
- **eddi-server**: Serve apps as Tor hidden services
- **eddi-msgsrv**: Generic message server for any messaging use case

### Install
```bash
idlergear eddi install
idlergear eddi install --force
```

**MCP Tool:** `eddi_install`

Installs both binaries to `~/.idlergear/bin/` (keeps binaries out of repos).

Requirements:
- Rust toolchain (cargo): https://rustup.rs
- Git

### Status
```bash
idlergear eddi status
```

**MCP Tool:** `eddi_status`

### Uninstall
```bash
idlergear eddi uninstall
```

**MCP Tool:** `eddi_uninstall`

---

### eddi-server: Publishing Apps as Hidden Services

Serve any app listening on a Unix socket as a Tor hidden service:

```bash
# Start your app on a Unix socket
gunicorn --bind unix:/tmp/myapp.sock myapp:app

# Serve as hidden service
~/.idlergear/bin/eddi-server --socket /tmp/myapp.sock
```

See `AI_INSTRUCTIONS/EDDI_HIDDEN_SERVICES.md` for complete setup guide.

---

### eddi-msgsrv: Generic Message Server

A dynamically-created message server accessible via Tor. Useful for:
- LLM-to-LLM communication across machines
- Any application needing secure messaging through NAT/firewalls
- Temporary collaboration channels

#### Creating a Server

```bash
# Create a message server
eddi-msgsrv create-server --name my-server --ttl 5

# Local-only (no Tor)
eddi-msgsrv create-server --name my-server --ttl 5 --local-only
```

#### Client Registration (Broker/Token Workflow)

Clients connect via a human-mediated token exchange:

1. **Admin creates broker** with short-lived code:
```bash
eddi-msgsrv create-broker --server my-server --namespace user@example.com
# Output: Code H7K-9M3 (valid 120 seconds)
```

2. **Human gives code to client** (out of band - email, chat, etc.)

3. **Client connects using code**:
```bash
eddi-msgsrv connect --code H7K-9M3 --namespace user@example.com
```

4. **Client receives persistent token** for future connections

#### Sending and Receiving Messages

```bash
# Send a message
eddi-msgsrv send "Hello from machine A"

# Listen for messages
eddi-msgsrv listen
```

#### Server Management

```bash
# List all servers
eddi-msgsrv list-servers

# Check server status
eddi-msgsrv status

# List connected clients
eddi-msgsrv list-clients --server my-server

# Revoke a client
eddi-msgsrv revoke-client --server my-server --code <client-code>

# Stop server
eddi-msgsrv stop-server my-server

# Cleanup all
eddi-msgsrv cleanup --force
```

#### Example: LLM-to-LLM Coordination

```bash
# Machine A (coordinator): Create server
eddi-msgsrv create-server --name llm-coord --ttl 60
eddi-msgsrv create-broker --server llm-coord --namespace claude-a
# Give code to Machine B

# Machine B: Connect
eddi-msgsrv connect --code H7K-9M3 --namespace claude-b --alias coordinator

# Machine A: Send task
eddi-msgsrv send "Please review auth.py and report issues"

# Machine B: Listen and respond
eddi-msgsrv listen
eddi-msgsrv send "Found 3 issues: ..."
```

Benefits:
- Works through NAT/firewalls
- No port forwarding needed
- Encrypted via Tor
- Human-mediated trust (code exchange)
- Persistent tokens after initial connection

---

## MCP Server

Start the MCP server to expose all tools to LLM clients.

### Start Server
```bash
idlergear mcp start
```

### Get Info
```bash
idlergear mcp info
```

---

## Common Workflows

### 1. Web-to-Local Sync Workflow

```bash
# 1. Push to web
idlergear sync push

# 2. Work in web LLM (Claude Web, etc.)
# 3. Pull back
idlergear sync pull
```

### 2. Teleport Live Testing Workflow

```bash
# 1. Prepare
idlergear teleport prepare

# 2. Run teleport command from Claude Code web
claude --teleport <uuid>

# 3. Watch for changes
idlergear teleport watch

# 4. When notified, run your tests:
./run.sh

# 5. Press Ctrl+C and finish
idlergear teleport finish
```

### 3. Multi-LLM Debugging Workflow

```bash
# Terminal 1: Start log server
idlergear logs serve --name debug

# Terminal 2: Run your app
./run.sh 2>&1 | idlergear logs stream --to debug

# Terminal 3: LLM assistant can query logs
idlergear logs show --session 1 --tail 100
```

### 4. Cross-Machine Coordination

```bash
# Machine A: Send message
idlergear message send --to machine-b --body "Please test auth changes"
idlergear sync push

# Machine B: Receive message
idlergear sync pull
idlergear message list
idlergear message read --id <msg-id>

# Machine B: Respond
idlergear message respond --id <msg-id> --body "Tests pass"
idlergear sync push
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub PAT for API access | Falls back to `gh auth token` |

---

## File Locations

| Path | Description |
|------|-------------|
| `~/.idlergear/bin/` | Binary installations (eddi-msgsrv) |
| `~/.idlergear/src/` | Source code for built tools |
| `.idlergear/logs/` | Log sessions (per-project) |
| `.idlergear/messages/` | Message queue (per-project) |

---

## Security Notes

1. **Tor secrets**: Never commit `hs_ed25519_*`, `hostname`, `tor_data/` directories
2. **Binaries**: Install to `~/.idlergear/bin/`, not in project repos
3. **MCP server**: Runs on stdio only, no network exposure
4. **GitHub tokens**: Store in `.env` (gitignored)

---

## For LLM Assistants

When using IdlerGear tools:

1. **Check project status first**: Run `project_status` to understand git state
2. **Use structured logging**: See `AI_INSTRUCTIONS/LOGGING_DEBUGGING.md`
3. **Coordinate via messages**: Use message tools for async LLM-to-LLM communication
4. **Clean up branches**: Use `teleport finish` to merge and cleanup after sessions
5. **Don't commit secrets**: Watch for Tor keys, tokens, and binaries

### MCP Integration

If your LLM client supports MCP:

1. Configure the IdlerGear MCP server in your client
2. All tools above become available programmatically
3. Use tool names like `project_status`, `logs_list`, `message_send`

### Manual CLI Usage

If MCP is not available, invoke CLI commands directly:

```bash
idlergear status
idlergear logs show --session 1
idlergear message send --to web --body "Ready for review"
```

---

## Troubleshooting

### "Permission denied" on eddi binary
```bash
chmod +x ~/.idlergear/bin/eddi-msgsrv
```

### Log server connection refused
```bash
# Check socket exists
ls /tmp/idlergear-logs-*.sock

# Restart server
idlergear logs serve --name debug
```

### Sync branch conflicts
```bash
idlergear sync pull --no-cleanup
# Resolve conflicts manually
git add .
git commit
```

### Missing cargo for eddi install
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```
