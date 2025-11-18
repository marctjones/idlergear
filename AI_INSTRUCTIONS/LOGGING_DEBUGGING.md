# Logging and Debugging Guide for LLM Coding Assistants

**Purpose:** This guide explains how to set up logging for scripts you write, how to coordinate log capture across terminals and machines, and how to receive logs from OTEL-enabled environments.

---

## Quick Reference

```bash
# Capture logs locally
./script.sh 2>&1 | idlergear logs pipe --name my-app

# Multi-terminal (same machine)
# Terminal 1: idlergear logs serve --name debug
# Terminal 2: ./script.sh 2>&1 | idlergear logs stream --to debug

# Remote machine
# Remote: ./script.sh 2>&1 | idlergear logs stream --to 192.168.1.100:9999
# Local:  idlergear logs serve --port 9999 --name remote-app

# Via eddi (secure, works through NAT)
# Local:  idlergear logs serve --via eddi --name debug  # Get code: H7K-9M3
# Remote: ./script.sh 2>&1 | idlergear logs stream --via eddi --code H7K-9M3

# Pull from observability stack
idlergear logs pull --otel http://collector:4318 --query 'service.name=myapp'
idlergear logs pull --loki http://loki:3100 --query '{app="myapp"}'
```

---

## Writing Scripts with Proper Logging

### Always Use Structured Logging

When writing scripts that may need debugging, use structured JSON logging so IdlerGear and LLMs can parse it effectively:

**Python:**
```python
import logging
import json
import sys

# JSON structured logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
        })

handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)

# Usage
logger = logging.getLogger(__name__)
logger.info("Starting process", extra={"user_id": 123})
```

**Node.js:**
```javascript
const log = (level, message, data = {}) => {
  console.error(JSON.stringify({
    time: new Date().toISOString(),
    level,
    message,
    ...data
  }));
};

// Usage
log('info', 'Starting server', { port: 3000 });
log('error', 'Connection failed', { host: 'db', error: err.message });
```

**Bash:**
```bash
#!/bin/bash
log() {
    local level=$1
    shift
    echo "{\"time\":\"$(date -Iseconds)\",\"level\":\"$level\",\"message\":\"$*\"}" >&2
}

# Usage
log INFO "Starting deployment"
log ERROR "Failed to connect to database"
```

### Log Levels and What to Log

| Level | When to Use | Examples |
|-------|-------------|----------|
| ERROR | Something failed and needs attention | Connection failures, unhandled exceptions |
| WARN | Something unexpected but recovered | Retry succeeded, deprecated API used |
| INFO | Normal operation milestones | Server started, request completed |
| DEBUG | Detailed diagnostic info | Variable values, function entry/exit |

### Critical Information to Always Log

1. **Startup:** Configuration loaded, services connected
2. **External calls:** API requests/responses, database queries
3. **State changes:** User actions, data modifications
4. **Errors:** Full stack traces, input that caused failure
5. **Shutdown:** Cleanup status, final metrics

---

## Setting Up Log Capture

### Scenario 1: Simple Local Capture

When running a script in the same terminal:

```bash
# Run and capture
idlergear logs run --command "./my-script.sh" --name my-app

# Or pipe existing output
./my-script.sh 2>&1 | idlergear logs pipe --name my-app

# View the logs
idlergear logs show --session 1
idlergear logs show --session 1 --tail 50
```

### Scenario 2: Separate Terminal (Same Machine)

When you need to run a long-lived process and monitor it separately:

**Tell the user:**
> "Please open a second terminal and run:
> ```bash
> idlergear logs serve --name debug-session
> ```
>
> Then in your original terminal, run:
> ```bash
> ./your-app.sh 2>&1 | idlergear logs stream --to debug-session
> ```
>
> I'll be able to see the logs in real-time from the first terminal."

**How it works:**
- `logs serve` creates a Unix socket at `/tmp/idlergear-logs-<name>.sock`
- `logs stream` sends log lines to that socket
- Both share the same `.idlergear/logs/` directory

### Scenario 3: Different Machine

When the script runs on a remote server:

**Tell the user:**
> "On the remote machine, run:
> ```bash
> ./your-app.sh 2>&1 | idlergear logs stream --to YOUR_IP:9999
> ```
>
> On your local machine (where I can see logs), run:
> ```bash
> idlergear logs serve --port 9999 --name remote-app
> ```
>
> Replace YOUR_IP with your local machine's IP address."

**Firewall note:** Port 9999 must be accessible from the remote machine.

### Scenario 4: Secure Remote via eddi

When machines are behind NAT or you need secure communication:

**Tell the user:**
> "First, ensure eddi is installed:
> ```bash
> idlergear eddi install
> ```
>
> On your local machine, start a log server:
> ```bash
> idlergear logs serve --via eddi --name debug-session
> ```
>
> This will output a connection code like `H7K-9M3`.
>
> On the remote machine, run:
> ```bash
> ./your-app.sh 2>&1 | idlergear logs stream --via eddi --code H7K-9M3
> ```
>
> The code is valid for 2 minutes. Logs will stream securely through Tor."

**Benefits of eddi:**
- Works through NAT/firewalls
- No port forwarding needed
- Encrypted via Tor
- Short-lived connection codes

---

## Pulling Logs from Observability Systems

### OpenTelemetry Collector

If the application sends logs to an OTEL collector:

```bash
# Pull recent logs
idlergear logs pull --otel http://collector:4318 \
  --query 'service.name=myapp' \
  --since 1h

# Pull and save to session
idlergear logs pull --otel http://collector:4318 \
  --query 'service.name=myapp AND severity>=ERROR' \
  --name otel-errors
```

### Grafana Loki

```bash
# Pull from Loki
idlergear logs pull --loki http://loki:3100 \
  --query '{app="myapp", env="prod"}' \
  --since 30m

# With regex filter
idlergear logs pull --loki http://loki:3100 \
  --query '{app="myapp"} |~ "error|exception"' \
  --since 1h
```

### AWS CloudWatch

```bash
# Pull from CloudWatch
idlergear logs pull --cloudwatch \
  --log-group /aws/lambda/my-function \
  --since 1h \
  --name lambda-logs

# With filter pattern
idlergear logs pull --cloudwatch \
  --log-group /ecs/my-service \
  --filter-pattern "ERROR" \
  --since 2h
```

### Google Cloud Logging

```bash
# Pull from GCP
idlergear logs pull --gcp \
  --project my-project \
  --query 'resource.type="k8s_container" AND severity>=ERROR' \
  --since 1h
```

---

## Asking Users to Set Up Logging

### Template for Requesting Log Capture

When you write a script that needs debugging, use this template:

```markdown
## Running with Log Capture

To help me debug any issues, please capture the logs:

### Option A: Simple (same terminal)
```bash
./run.sh 2>&1 | idlergear logs pipe --name app-debug
```

### Option B: Separate terminal (recommended for long-running apps)

**Terminal 1:**
```bash
idlergear logs serve --name app-debug
```

**Terminal 2:**
```bash
./run.sh 2>&1 | idlergear logs stream --to app-debug
```

After running, I can view the logs with:
```bash
idlergear logs show --session <id> --tail 100
```
```

### Template for Remote Debugging

```markdown
## Remote Debugging Setup

Since the app runs on a different machine, let's set up remote log streaming:

### On your local machine:
```bash
idlergear logs serve --via eddi --name remote-debug
```
Note the connection code (e.g., `H7K-9M3`).

### On the remote machine:
```bash
./your-app.sh 2>&1 | idlergear logs stream --via eddi --code <CODE>
```

Replace `<CODE>` with the code from step 1.

I'll be able to see the logs in real-time once connected.
```

---

## Creating run.sh for Consistent Execution

Always create a `run.sh` that includes proper logging setup:

```bash
#!/bin/bash
# run.sh - Standard entry point with logging

set -euo pipefail

# Configuration
APP_NAME="${APP_NAME:-myapp}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Logging function
log() {
    local level=$1
    shift
    echo "{\"time\":\"$(date -Iseconds)\",\"level\":\"$level\",\"app\":\"$APP_NAME\",\"message\":\"$*\"}" >&2
}

# Startup
log INFO "Starting $APP_NAME"
log INFO "Log level: $LOG_LEVEL"
log INFO "Working directory: $(pwd)"

# Run the actual application
exec python -m src.main "$@"
```

**Tell users:**
> "Run the app with:
> ```bash
> ./run.sh 2>&1 | idlergear logs pipe --name myapp
> ```
>
> Or for continuous development:
> ```bash
> idlergear logs serve --name myapp
> # In another terminal:
> ./run.sh 2>&1 | idlergear logs stream --to myapp
> ```"

---

## Reading and Analyzing Logs

### List Available Sessions

```bash
idlergear logs list
```

Output:
```
ID  | Name        | Started              | Lines | Status
----|-------------|----------------------|-------|--------
3   | app-debug   | 2025-01-15 10:30:00  | 1542  | active
2   | backend     | 2025-01-15 09:15:00  | 823   | stopped
1   | frontend    | 2025-01-14 16:45:00  | 2103  | stopped
```

### View Logs

```bash
# Show all logs for a session
idlergear logs show --session 3

# Show last 100 lines
idlergear logs show --session 3 --tail 100

# Follow logs in real-time
idlergear logs follow --session 3

# Export to file
idlergear logs export --session 3 --output debug.log
```

### Filter and Search

```bash
# Search for errors
idlergear logs show --session 3 --grep "ERROR"

# Filter by time range
idlergear logs show --session 3 --since "10 minutes ago"

# JSON query (for structured logs)
idlergear logs show --session 3 --jq '.level == "ERROR"'
```

---

## MCP Integration

All logging commands are available as MCP tools for LLM assistants:

```python
# Available MCP tools:
logs_serve      # Start log server
logs_stream     # Stream logs to server
logs_list       # List log sessions
logs_show       # Show log content
logs_pull_otel  # Pull from OTEL
logs_pull_loki  # Pull from Loki
```

LLM assistants using MCP can:
1. Programmatically start log servers
2. Pull logs from observability systems
3. Analyze log content directly
4. Set up multi-terminal coordination

---

## Troubleshooting

### "Connection refused" when streaming

```bash
# Check if server is running
ls /tmp/idlergear-logs-*.sock

# Restart the server
idlergear logs serve --name debug
```

### Logs not appearing

1. Ensure you're capturing stderr: `2>&1`
2. Check the app is actually writing to stdout/stderr
3. Flush buffers in your app (Python: `flush=True`, Node: `process.stderr.write`)

### eddi connection failed

```bash
# Verify eddi is installed
idlergear eddi status

# Check Tor is running
systemctl status tor

# Generate new code (old one may have expired)
idlergear logs serve --via eddi --name debug
```

### OTEL/Loki pull returns empty

1. Verify the endpoint URL is correct
2. Check authentication (may need `--token` or `--user/--password`)
3. Adjust the `--since` time window
4. Test the query in Grafana/OTEL UI first

---

## Best Practices Summary

1. **Always use structured (JSON) logging** - easier to parse and query
2. **Log to stderr** - keeps stdout clean for actual output
3. **Include context** - timestamps, request IDs, user IDs
4. **Create run.sh** - consistent entry point with logging built-in
5. **Use eddi for remote** - secure, NAT-friendly
6. **Pull from OTEL when available** - centralized logs are easier
7. **Provide clear instructions** - tell users exactly what to run
