# Integrating eddi Message Server with IdlerGear Workflows

**Document for:** IdlerGear development team
**About:** How to use eddi's `msgsrv` (messaging server) as a tool in IdlerGear workflows
**eddi Repository:** https://github.com/marctjones/eddi
**eddi Branch:** `claude/cli-message-passing-01Sbqwn269RoUr7uc7yp4ce9`

---

## Executive Summary

The **eddi messaging server** (`eddi-msgsrv`) provides secure, real-time, Tor-based message passing that perfectly complements IdlerGear's git-based coordination system. While IdlerGear excels at code synchronization and batch operations, eddi-msgsrv enables real-time execution, log streaming, and bidirectional communication between web coding interfaces and local development environments.

**Key Insight:** Use **git-based messaging** for code sync, **eddi-msgsrv** for real-time execution and streaming.

---

## What is eddi-msgsrv?

### Overview

**eddi-msgsrv** is a secure message passing system built in Rust that uses:

- **Tor hidden services** for anonymous, NAT-traversing connectivity
- **Introduction/Rendezvous pattern** for secure client authentication
- **Unix Domain Sockets** for fast local IPC (with optional Tor for remote access)
- **SQLite state management** for persistence
- **Ephemeral brokers** that only exist for 2 minutes to minimize attack surface

### Architecture: Three Components

```
1. Server (persistent)
   - Long-running message server
   - Persistent .onion address (when Tor enabled)
   - Unix socket: /tmp/eddi-msgsrv-<name>.sock
   - Stores messages with TTL (default: 5 minutes)

2. Broker (ephemeral)
   - Temporary handshake server (2-minute lifetime)
   - Generates short codes (e.g., H7K-9M3)
   - Validates clients and issues access tokens
   - Self-destructs after handshake

3. Client
   - Discovers broker via namespace + code + timestamp
   - Receives server address + access token
   - Connects directly to server for messaging
```

### Security Model: Introduction Pattern

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Admin creates Server                                     │
│    → Gets .onion address (or Unix socket)                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Admin creates Broker                                     │
│    → Gets short code: H7K-9M3                               │
│    → Valid for: 120 seconds                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Admin shares code out-of-band                            │
│    → Phone, Signal, email, etc.                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Client connects to Broker                                │
│    → Uses code + namespace                                  │
│    → Time-based discovery (±5 minute window)                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Broker validates client                                  │
│    → Issues access token                                    │
│    → Sends server .onion address                            │
│    → Broker shuts down (ephemeral!)                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Client connects to Server                                │
│    → Uses access token                                      │
│    → Persistent connection for messaging                    │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ Attack surface minimization (broker only lives 2 minutes)
- ✅ Server stealth (main server doesn't handle authentication)
- ✅ Persistence (clients can reconnect without new codes)
- ✅ Token revocation (remove access without restarting server)

---

## CLI Commands Reference

### Server Management

```bash
# Create server (Tor enabled by default)
eddi-msgsrv create-server --name my-server --ttl 5

# Create server (local-only mode, no Tor)
eddi-msgsrv create-server --name my-server --ttl 5 --local-only

# List all servers
eddi-msgsrv list-servers

# Show status
eddi-msgsrv status [server-name]

# Stop server
eddi-msgsrv stop-server my-server

# Cleanup
eddi-msgsrv cleanup --force
```

### Broker Management (Handshake Server)

```bash
# Create broker
eddi-msgsrv create-broker --server my-server --namespace user@example.com

# Output:
# ✓ Broker created
# Namespace: user@example.com
# Short Code: H7K-9M3
# Valid for: 120 seconds
#
# Share with client:
#   eddi-msgsrv connect --code H7K-9M3 --namespace user@example.com

# List active brokers
eddi-msgsrv list-brokers

# Stop broker
eddi-msgsrv stop-broker <broker-id>
```

### Client Operations

```bash
# Connect to server via broker
eddi-msgsrv connect --code H7K-9M3 --namespace user@example.com

# Connect with time window adjustment
eddi-msgsrv connect --code H7K-9M3 --namespace user@example.com --time-window 10

# Connect with alias
eddi-msgsrv connect --code H7K-9M3 --namespace user@example.com --alias web-env

# Send message
eddi-msgsrv send "Hello, world!"
eddi-msgsrv send "Debug this error" --server my-server

# Receive messages (one-time)
eddi-msgsrv receive --once

# Listen for messages (continuous)
eddi-msgsrv listen
eddi-msgsrv listen --server my-server

# List connections
eddi-msgsrv list-connections

# Disconnect
eddi-msgsrv disconnect my-server
```

### Administration

```bash
# List clients connected to server
eddi-msgsrv list-clients --server my-server

# Revoke client access
eddi-msgsrv revoke-client --server my-server --code H7K-9M3
```

---

## Integration with IdlerGear: Use Cases

### Use Case 1: Real-Time Code Execution from Web

**Scenario:** Coding in Claude Code Web, need to test locally

**Current IdlerGear Workflow (Git-Based):**
```bash
# In Claude Code Web: write code, commit to sync branch
# Total latency: 30-60 seconds per iteration

# Local terminal:
idlergear sync pull        # 15 seconds
python main.py             # Run code
idlergear sync push        # 20 seconds (with logs)
```

**Enhanced Workflow with eddi-msgsrv:**
```bash
# ONE-TIME SETUP (Local):
# 1. Start eddi messaging server
eddi-msgsrv create-server --name idlergear-local --ttl 10

# 2. Create broker for web environment
eddi-msgsrv create-broker --server idlergear-local --namespace claude-web@myproject
# → Shares code: H7K-9M3

# 3. Share code with web environment via git (one-time)
echo "EDDI_BROKER_CODE=H7K-9M3" >> .idlergear/web-config
echo "EDDI_NAMESPACE=claude-web@myproject" >> .idlergear/web-config
git add .idlergear/web-config
git commit -m "Add eddi broker config"
git push

# IN CLAUDE CODE WEB:
# 1. Connect to local environment (one-time)
eddi-msgsrv connect --code H7K-9M3 --namespace claude-web@myproject --alias local

# 2. Send execution request
eddi-msgsrv send "EXEC: python main.py" --server local

# LOCAL LISTENS AND EXECUTES:
# (Background process listening for commands)
eddi-msgsrv listen --server idlergear-local | while read -r msg; do
  if [[ "$msg" == "EXEC:"* ]]; then
    cmd="${msg#EXEC: }"
    eval "$cmd" 2>&1 | eddi-msgsrv send --server idlergear-local
  fi
done

# RESULT:
# - Total latency: 2-5 seconds (vs 30-60 with git)
# - Real-time log streaming
# - Bidirectional communication
```

### Use Case 2: GUI Testing with Screenshot Feedback

```bash
# Local setup: Start GUI listener
#!/bin/bash
# idlergear-gui-tester.sh

eddi-msgsrv listen --server idlergear-local | while read -r msg; do
  case "$msg" in
    "RUN_GUI:"*)
      script="${msg#RUN_GUI: }"
      python "$script" &
      PID=$!
      eddi-msgsrv send "GUI started: PID $PID" --server idlergear-local

      # Stream logs
      tail -f /tmp/gui-$PID.log | while read -r line; do
        eddi-msgsrv send "LOG: $line" --server idlergear-local
      done
      ;;

    "SCREENSHOT")
      # Take screenshot
      import -window root /tmp/screenshot.png
      base64 /tmp/screenshot.png | eddi-msgsrv send --server idlergear-local
      ;;

    "KILL_GUI")
      kill $PID
      eddi-msgsrv send "GUI stopped" --server idlergear-local
      ;;
  esac
done

# In Claude Code Web:
eddi-msgsrv send "RUN_GUI: src/gui/app.py" --server local
# ... receives logs in real-time ...
# User clicks button, error occurs
eddi-msgsrv send "SCREENSHOT" --server local
# ... receives screenshot ...
# Claude analyzes error + screenshot, suggests fix
```

### Use Case 3: Long-Running Data Processing

```bash
# Local: Start task runner
#!/bin/bash
# idlergear-task-runner.sh

eddi-msgsrv listen --server idlergear-local | while read -r msg; do
  case "$msg" in
    "TASK:"*)
      task_cmd="${msg#TASK: }"

      # Run in background, stream progress
      $task_cmd 2>&1 | while read -r line; do
        eddi-msgsrv send "PROGRESS: $line" --server idlergear-local
      done

      # Send completion
      eddi-msgsrv send "TASK_COMPLETE: $task_cmd" --server idlergear-local
      ;;
  esac
done

# In Claude Code Web:
# Start long-running task
eddi-msgsrv send "TASK: python process_large_dataset.py" --server local

# Monitor progress (async in web UI)
eddi-msgsrv listen --server local
# ... sees progress updates every few seconds ...
# PROGRESS: Processing row 1000/100000
# PROGRESS: Processing row 2000/100000
# ...
# TASK_COMPLETE: python process_large_dataset.py

# Web environment can close browser and check back later!
```

### Use Case 4: Database Queries from Web

```bash
# Local: Database query proxy
#!/bin/bash
# idlergear-db-proxy.sh

eddi-msgsrv listen --server idlergear-local | while read -r msg; do
  case "$msg" in
    "QUERY:"*)
      query="${msg#QUERY: }"

      # Execute query (PostgreSQL example)
      psql -d mydb -c "$query" -t | while read -r row; do
        eddi-msgsrv send "ROW: $row" --server idlergear-local
      done

      eddi-msgsrv send "QUERY_COMPLETE" --server idlergear-local
      ;;
  esac
done

# In Claude Code Web:
eddi-msgsrv send "QUERY: SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '7 days';" --server local

# Receives:
# ROW: 127
# QUERY_COMPLETE

# Claude uses result to suggest optimizations
```

### Use Case 5: Integration Testing with Secrets

```bash
# Local: Test runner with local secrets
#!/bin/bash
# idlergear-test-runner.sh

eddi-msgsrv listen --server idlergear-local | while read -r msg; do
  case "$msg" in
    "TEST:"*)
      test_cmd="${msg#TEST: }"

      # Load local secrets
      source .env.local

      # Run tests
      $test_cmd 2>&1 | while read -r line; do
        # Filter out secrets before sending
        filtered=$(echo "$line" | sed 's/API_KEY=.*/API_KEY=***/')
        eddi-msgsrv send "TEST_LOG: $filtered" --server idlergear-local
      done

      eddi-msgsrv send "TEST_COMPLETE: Exit code $?" --server idlergear-local
      ;;
  esac
done

# In Claude Code Web:
eddi-msgsrv send "TEST: pytest tests/integration/test_stripe.py -v" --server local

# Receives real test results with actual API calls
# But secrets never leave local environment
```

---

## Proposed IdlerGear Commands

### New IdlerGear CLI Integration

```bash
# Start eddi messaging bridge for web environments
idlergear eddi start [--server-name <name>] [--ttl <minutes>]
# → Creates eddi-msgsrv server
# → Generates broker code
# → Displays connection instructions for web

# Create broker for web coding tool
idlergear eddi connect-web [--namespace <id>]
# → Creates broker
# → Outputs short code
# → Instructions for web environment

# Send command to local environment (from web)
idlergear eddi exec "<command>"
# → Sends EXEC message
# → Waits for response
# → Displays output

# Listen for messages from web
idlergear eddi listen [--handle-exec]
# → Listens for messages
# → Optionally auto-executes EXEC commands
# → Streams responses back

# Show eddi connection status
idlergear eddi status
# → Shows active servers
# → Active brokers
# → Connected clients

# Stop eddi bridge
idlergear eddi stop
# → Stops servers
# → Cleanup
```

### Configuration in .idlergear.toml

```toml
[eddi]
enabled = true
default_server_name = "idlergear-local"
default_ttl = 10  # minutes
default_namespace = "local@myproject"

# Auto-start on idlergear init
auto_start = false

# Tor settings
tor_enabled = true  # Default: Tor for security
local_only = false  # Set true for fast local development

# Security
require_approval_for_exec = true  # Prompt before executing commands
allowed_commands = [
  "python",
  "npm",
  "pytest",
  "cargo",
]
forbidden_commands = [
  "rm -rf",
  "sudo",
  "dd",
]

# Automation
[eddi.handlers]
# Auto-handle EXEC messages
auto_exec = false

# Auto-stream logs
auto_stream_logs = true

# Auto-take screenshots on GUI errors
auto_screenshot = true
```

---

## Workflow Examples

### Workflow 1: Hybrid Git + eddi Messaging

**Best of both worlds: Git for code, eddi for execution**

```bash
# LOCAL SETUP (one time):
# 1. Start eddi server
idlergear eddi start --server-name my-project

# Output:
# ✓ eddi server 'my-project' started
# Socket: /tmp/eddi-msgsrv-my-project.sock
# Onion: abc123def456.onion (when Tor enabled)
#
# To connect from web:
# 1. Create broker: idlergear eddi connect-web
# 2. Use code in web environment

# 2. Create broker for Claude Code Web
idlergear eddi connect-web --namespace claude-web@my-project

# Output:
# ✓ Broker created
# Short Code: H7K-9M3
# Valid for: 120 seconds
#
# In Claude Code Web, run:
#   eddi-msgsrv connect --code H7K-9M3 --namespace claude-web@my-project --alias local

# 3. Start command listener
idlergear eddi listen --handle-exec &

# IN CLAUDE CODE WEB:
# 1. Connect (one-time)
eddi-msgsrv connect --code H7K-9M3 --namespace claude-web@my-project --alias local

# 2. Write code in web UI (use git for sync)
# ... coding ...

# 3. Test locally via eddi
eddi-msgsrv send "EXEC: python -m pytest tests/ -v" --server local

# Receives output in real-time:
# TEST_LOG: test_user_login PASSED
# TEST_LOG: test_user_logout PASSED
# TEST_LOG: test_password_reset FAILED
# TEST_LOG: AssertionError: Expected 200, got 404
# TEST_COMPLETE: Exit code 1

# 4. Fix code, test again (rapid iteration)
eddi-msgsrv send "EXEC: python -m pytest tests/test_password_reset.py -v" --server local

# 5. Once all tests pass, commit to git
# (Use git-based sync for code commits, eddi for execution)
```

### Workflow 2: Multi-Environment Development

**Local ← eddi → Staging ← eddi → Production**

```bash
# Scenario: Test changes across multiple environments

# LOCAL → STAGING
# 1. Create staging server
ssh staging
eddi-msgsrv create-server --name staging-env --ttl 30

# 2. Create broker
eddi-msgsrv create-broker --server staging-env --namespace local@staging
# Code: X9Y-2K7

# 3. Connect from local
eddi-msgsrv connect --code X9Y-2K7 --namespace local@staging --alias staging

# 4. Send code via git (for sync)
git push staging feature-branch

# 5. Trigger deployment via eddi (for execution)
eddi-msgsrv send "EXEC: cd /app && git pull && ./deploy.sh" --server staging

# 6. Monitor deployment logs in real-time
eddi-msgsrv listen --server staging
```

### Workflow 3: Team Collaboration

**Multiple developers, one project**

```bash
# Team lead (local):
# 1. Create shared server
eddi-msgsrv create-server --name team-project --ttl 60

# 2. Create brokers for each team member
eddi-msgsrv create-broker --server team-project --namespace alice@team
# Code: A1B-C2D

eddi-msgsrv create-broker --server team-project --namespace bob@team
# Code: E3F-G4H

# 3. Share codes via Signal/phone

# Alice connects:
eddi-msgsrv connect --code A1B-C2D --namespace alice@team --alias team

# Bob connects:
eddi-msgsrv connect --code E3F-G4H --namespace bob@team --alias team

# Real-time collaboration:
# Alice: "I'm running the migration script now"
eddi-msgsrv send "EXEC: python manage.py migrate" --server team

# Bob sees output:
# PROGRESS: Running migration 001_initial
# PROGRESS: Running migration 002_add_users
# COMPLETE: Migrations applied successfully

# Bob: "Thanks! Running tests now"
eddi-msgsrv send "EXEC: pytest tests/ -v" --server team

# Everyone sees test results in real-time
```

---

## Comparison: Git-Based vs eddi Messaging

| Feature | Git-Based (IdlerGear Current) | eddi Messaging (New) | Recommendation |
|---------|-------------------------------|----------------------|----------------|
| **Latency** | 30-60 seconds | 2-5 seconds | Use eddi for real-time |
| **Code Sync** | ✅ Excellent | ⚠️ Manual | **Use git** |
| **Large Files** | ✅ Good | ❌ Not designed for | Use git |
| **Real-time Execution** | ❌ No | ✅ Yes | **Use eddi** |
| **Log Streaming** | ❌ No | ✅ Yes | **Use eddi** |
| **Long-running Tasks** | ❌ No | ✅ Yes | **Use eddi** |
| **Bidirectional** | ✅ Yes (slow) | ✅ Yes (fast) | Use eddi for speed |
| **Security** | Git authentication | Tor + tokens | Both secure |
| **NAT Traversal** | Via GitHub | Via Tor | Both work |
| **Offline Mode** | ✅ Yes | ❌ No | Use git offline |
| **Git History** | ⚠️ Pollutes | ✅ No pollution | Use eddi to reduce noise |
| **Message TTL** | Permanent (git) | 5-60 minutes | Use eddi for ephemeral |
| **Setup Complexity** | Low | Medium | Git easier |

### Recommended Hybrid Approach

**Use both systems for their strengths:**

1. **Git-based (idlergear sync)** for:
   - Code synchronization
   - Large files (datasets, models)
   - Persistent documentation
   - PR workflow
   - Offline work

2. **eddi messaging** for:
   - Real-time command execution
   - Log streaming
   - Long-running processes
   - GUI testing
   - Database queries
   - Integration tests with local secrets
   - Rapid iteration debugging

---

## Implementation Roadmap for IdlerGear

### Phase 1: Basic Integration (Immediate)

```bash
# Add eddi-msgsrv as optional dependency
# New commands:
idlergear eddi start
idlergear eddi stop
idlergear eddi status
```

**Tasks:**
- [ ] Add eddi-msgsrv binary detection
- [ ] Create wrapper commands
- [ ] Basic server management
- [ ] Connection string generation
- [ ] Documentation

### Phase 2: Command Execution (Short Term)

```bash
# Bidirectional command execution
idlergear eddi exec "<command>"
idlergear eddi listen --handle-exec
```

**Tasks:**
- [ ] Message protocol design (EXEC, RESPONSE, ERROR)
- [ ] Command whitelist/blacklist
- [ ] Approval workflow for destructive commands
- [ ] Streaming output handler
- [ ] Error handling

### Phase 3: Smart Automation (Medium Term)

```bash
# Auto-detect and route commands
idlergear run "python main.py"  # Auto-decides git vs eddi
```

**Tasks:**
- [ ] Heuristics for git vs eddi routing
- [ ] Unified message interface
- [ ] Fallback logic (eddi → git)
- [ ] Performance monitoring
- [ ] Usage analytics

### Phase 4: Advanced Features (Long Term)

```bash
# Full integration
idlergear daemon start  # Runs both git sync + eddi listener
```

**Tasks:**
- [ ] Daemon mode
- [ ] Web UI connection wizard
- [ ] Multi-environment support
- [ ] Team collaboration features
- [ ] Enterprise security (audit logs, RBAC)

---

## Security Considerations

### Threat Model

**What eddi protects against:**
- ✅ Network eavesdropping (Tor encryption)
- ✅ IP address exposure (Tor anonymity)
- ✅ NAT traversal issues (Tor hidden services)
- ✅ Unauthorized access (broker + token authentication)
- ✅ Long-lived attack surface (ephemeral brokers)

**What eddi does NOT protect against:**
- ❌ Code execution vulnerabilities in your app
- ❌ Compromised broker codes (share securely!)
- ❌ Local system compromise
- ❌ Social engineering

### Best Practices

1. **Share broker codes securely**
   - Use Signal, phone, or encrypted email
   - Never share in public channels (Slack, Discord)
   - Use short TTLs (2 minutes default)

2. **Use approval workflows**
   ```bash
   idlergear eddi listen --require-approval
   # Prompts before executing any EXEC command
   ```

3. **Whitelist commands**
   ```toml
   [eddi.security]
   allowed_commands = ["python", "npm", "pytest"]
   forbidden_patterns = ["rm -rf", "sudo", "dd"]
   ```

4. **Monitor audit logs**
   ```bash
   idlergear eddi audit
   # [2025-11-18 10:30:15] EXEC: python main.py (approved)
   # [2025-11-18 10:30:45] EXEC: rm -rf / (DENIED)
   ```

5. **Use Tor by default**
   - Default: Tor enabled (secure, anonymous)
   - Only use `--local-only` for development/testing
   - Tor adds 30-60 seconds to startup (worth it!)

6. **Rotate broker codes frequently**
   - Create new broker for each session
   - Revoke old tokens after use
   - Use namespace + timestamp for discovery

---

## Feedback for eddi Claude Instance

### What's Working Well ✅

1. **Architecture is solid**
   - Introduction/Rendezvous pattern is elegant
   - Ephemeral brokers minimize attack surface
   - Tor-first design is security-conscious

2. **CLI design is intuitive**
   - Clear command structure
   - Good help documentation
   - Sensible defaults (Tor enabled, 5-minute TTL)

3. **Documentation is excellent**
   - MSGSRV_QUICKSTART.md is comprehensive
   - MESSAGE_SERVER.md covers architecture well
   - Good troubleshooting sections

4. **Security model is well-thought-out**
   - Time-based broker discovery is clever
   - Token-based access control is appropriate
   - Optional stealth mode is nice

### Suggested Improvements 🔧

1. **Message Protocol Standardization**

   **Current:** Messages are free-form strings

   **Suggestion:** Define a JSON message protocol
   ```json
   {
     "type": "EXEC",
     "command": "python main.py",
     "metadata": {
       "sender": "claude-web",
       "timestamp": 1700000000,
       "request_id": "abc123"
     }
   }
   ```

   **Benefits:**
   - Structured message parsing
   - Request/response correlation
   - Easier automation
   - Better error handling

2. **Response Streaming**

   **Current:** Messages sent one at a time

   **Suggestion:** Add streaming support for long outputs
   ```bash
   # New flag for send command
   eddi-msgsrv send --stream "python long_running_script.py"

   # Streams output line-by-line as it's generated
   # Instead of waiting for entire output
   ```

   **Benefits:**
   - Real-time feedback for long processes
   - Better UX for web coding tools
   - Ability to cancel long-running commands

3. **Binary Data Support**

   **Current:** Text messages only

   **Suggestion:** Support base64-encoded binary data
   ```bash
   # Send screenshot
   eddi-msgsrv send --binary screenshot.png

   # Receive binary
   eddi-msgsrv receive --binary > output.png
   ```

   **Benefits:**
   - Screenshots for GUI testing
   - File transfer between environments
   - Richer data exchange

4. **Reconnection Handling**

   **Current:** Manual reconnection

   **Suggestion:** Auto-reconnect with exponential backoff
   ```bash
   # New flag
   eddi-msgsrv listen --auto-reconnect --max-attempts 5
   ```

   **Benefits:**
   - Better UX for network interruptions
   - More robust for long-running sessions
   - Reduces manual intervention

5. **Message Queue Persistence**

   **Current:** Messages stored in-memory only

   **Suggestion:** Optional SQLite queue for missed messages
   ```bash
   # Server with persistent queue
   eddi-msgsrv create-server --name my-server --persist-messages

   # Client fetches missed messages
   eddi-msgsrv receive --since-last-seen
   ```

   **Benefits:**
   - Handle temporary disconnections
   - Fetch messages sent while offline
   - Better reliability

6. **Web-Friendly Output Format**

   **Current:** CLI-focused output

   **Suggestion:** Add JSON output mode
   ```bash
   eddi-msgsrv status --json
   eddi-msgsrv list-connections --json
   ```

   **Benefits:**
   - Easier parsing in scripts
   - Better integration with web tools
   - Machine-readable format

7. **Connection Aliases in State**

   **Current:** Aliases are CLI-only

   **Suggestion:** Persist aliases in SQLite state
   ```bash
   # Alias persists across sessions
   eddi-msgsrv connect --code ABC-XYZ --namespace user@ex --alias staging

   # Later (new session):
   eddi-msgsrv send "Hello" --server staging  # Still works!
   ```

   **Benefits:**
   - Better UX for multiple connections
   - Easier to remember than server names
   - Consistent across sessions

8. **Health Check Endpoint**

   **Current:** No health check

   **Suggestion:** Add ping/pong support
   ```bash
   eddi-msgsrv ping --server my-server
   # Pong! Latency: 245ms
   ```

   **Benefits:**
   - Monitor connection health
   - Detect network issues early
   - Useful for automation

9. **Batch Operations**

   **Current:** One message at a time

   **Suggestion:** Support message batches
   ```bash
   # Send multiple commands
   eddi-msgsrv send-batch commands.txt

   # Contents of commands.txt:
   # EXEC: python test1.py
   # EXEC: python test2.py
   # EXEC: python test3.py
   ```

   **Benefits:**
   - Run test suites
   - Deploy scripts
   - Automation workflows

10. **Integration Examples**

    **Current:** Generic examples

    **Suggestion:** Add integration docs for popular tools
    - `docs/INTEGRATION_CLAUDE_WEB.md`
    - `docs/INTEGRATION_COPILOT.md`
    - `docs/INTEGRATION_IDLERGEAR.md`

    **Contents:**
    - Step-by-step setup
    - Common workflows
    - Troubleshooting
    - Example scripts

### Questions for Clarification ❓

1. **Message size limits?**
   - What's the max message size?
   - How are large messages handled?
   - Should we chunk large outputs?

2. **Concurrent connections?**
   - How many clients can connect to one server?
   - Is there a connection limit?
   - What happens when limit is reached?

3. **Message ordering?**
   - Are messages guaranteed to be delivered in order?
   - What happens if client misses messages?
   - Is there a sequence number system?

4. **Error handling?**
   - How are errors communicated?
   - Is there a standard error format?
   - What's the retry policy?

5. **Broker cleanup?**
   - Do expired brokers auto-cleanup?
   - What about stale broker records in SQLite?
   - Is there a background cleanup process?

6. **Tor bootstrap time?**
   - Current: 30-60 seconds
   - Can this be optimized?
   - Caching Tor circuits?
   - Pre-warming connections?

7. **State migration?**
   - What happens on version upgrades?
   - Is there a migration system for SQLite schema changes?
   - Backward compatibility guarantees?

### Nice-to-Have Features 🌟

1. **End-to-end encryption beyond Tor**
   - NaCl/libsodium encryption
   - Forward secrecy
   - Optional for paranoid users

2. **Multi-broker load balancing**
   - Multiple brokers for high availability
   - Round-robin code generation
   - Failover support

3. **Message filtering/routing**
   - Subscribe to specific message types
   - Regex-based filtering
   - Topic-based pub/sub

4. **Web dashboard**
   - Browser-based UI for monitoring
   - Real-time message viewer
   - Connection management

5. **Metrics and monitoring**
   - Prometheus exporter
   - Grafana dashboards
   - Performance metrics

6. **Plugin system**
   - Custom message handlers
   - Protocol extensions
   - Third-party integrations

---

## Conclusion

The **eddi messaging server** is a powerful tool that perfectly complements IdlerGear's git-based coordination. By combining both:

- **Git** handles code synchronization and persistent state
- **eddi** handles real-time execution and ephemeral messaging

This hybrid approach provides:
- ✅ Best-in-class code sync (git)
- ✅ Real-time execution and feedback (eddi)
- ✅ Security and privacy (Tor)
- ✅ Fast iteration (2-5 second latency)
- ✅ Long-running process support (eddi)
- ✅ Clean git history (no sync branch pollution)

**Next Steps:**
1. Implement Phase 1 integration in IdlerGear
2. Document web coding tool setup
3. Create example workflows
4. Test with Claude Code Web, Copilot Web
5. Gather user feedback
6. Iterate on protocol design

---

**Document Version:** 1.0
**Date:** 2025-11-18
**Author:** IdlerGear Development Team
**For eddi Claude Instance:** See "Feedback for eddi Claude Instance" section above
