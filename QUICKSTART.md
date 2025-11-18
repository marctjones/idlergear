# IdlerGear Quick Start: Hybrid Local + Web LLM Development

**The Killer Workflow: Web LLM for Planning/Coding + Local for GUI Testing**

This guide shows you how to create a new project and seamlessly work between:
- **Claude Code Web** (planning, development, headless tests)
- **Local Gemini CLI** (context, coordination, local execution)
- **Local environment** (GUI testing, log collection)

---

## The 5-Minute Setup

### Step 1: Create New Project (Local Terminal)

```bash
# Create project with all the magic
idlergear new my-gui-app \
  --lang python \
  --llm-tools gemini,claude \
  --enable-logs \
  --enable-messaging

# Output:
# ⏳ Creating project 'my-gui-app'...
# [1/12] Creating local directory ✓
# [2/12] Initializing git repository ✓
# [3/12] Creating GitHub repository ✓
# [4/12] Creating documentation for LLM assistants ✓
# [5/12] Setting up development environment ✓
# [6/12] Installing development tools ✓
# [7/12] Setting up project structure ✓
# [8/12] Setting up pre-commit hooks ✓
# [9/12] Setting up log management ✓
# [10/12] Setting up message passing (eddi) ✓
#         Tor hidden service: abc123def456.onion
#         Connection code: TOR-XYZ789
# [11/12] Creating initial project files ✓
# [12/12] Final setup ✓
#
# ✨ Project 'my-gui-app' created successfully!
#
# 📋 NEXT STEPS:
# 1. cd my-gui-app
# 2. Launch local LLM: idlergear tools launch gemini
# 3. Connect web LLM with code: TOR-XYZ789
```

**What was created:**
```
my-gui-app/
├── AI_INSTRUCTIONS/          ← Gemini will read these automatically
│   ├── README.md            ← Main instructions for LLMs
│   ├── TESTING.md           ← TDD requirements
│   ├── LOGGING.md           ← How to use logging
│   └── COLLABORATION.md     ← Multi-LLM workflow
├── src/                      ← Source code
├── tests/                    ← Test suite
├── .idlergear/
│   ├── logs/                ← Log collection
│   └── messages/            ← LLM message passing
└── [full project structure]
```

### Step 2: Enter Directory & Launch Local LLM

```bash
# Enter project directory
cd my-gui-app

# Launch Gemini CLI (local)
idlergear tools launch gemini

# Behind the scenes, idlergear runs:
# gemini-cli --mcp http://localhost:3000 \
#   --context-files "AI_INSTRUCTIONS/README.md,VISION.md,DESIGN.md,TODO.md"
```

**Gemini CLI automatically:**
1. ✅ Connects to MCP server (localhost:3000)
2. ✅ Reads `AI_INSTRUCTIONS/README.md` (best practices)
3. ✅ Reads `VISION.md` (project vision)
4. ✅ Reads `DESIGN.md` (technical design)
5. ✅ Reads `TODO.md` (current tasks)
6. ✅ Loads project context (git status, test coverage, recent logs)

**Gemini now knows:**
- Project structure
- Best practices (TDD, logging, secrets management)
- Testing requirements (>80% coverage)
- Git workflow
- Available tools (MCP, eddi, logging)

### Step 3: Get Connection Code for Remote LLM (Gemini CLI)

```bash
# In Gemini CLI conversation:
You: "Show me the connection code for Claude Code Web"

# Gemini uses MCP tool to query idlergear
result = await get_eddi_connection_info()

Gemini: Here's the connection information for Claude Code Web:

**Connection Code:** TOR-XYZ789
**Namespace:** claude-web@my-gui-app
**Onion Address:** abc123def456.onion:8080

To connect from Claude Code Web, run:
```bash
eddi-msgsrv connect --code TOR-XYZ789 --namespace claude-web@my-gui-app --alias local
```

This will establish a secure Tor connection from the web to your local environment.
```

### Step 4: Connect Claude Code Web to Local Environment

**In browser: https://claude.ai/code**

```bash
# Clone the repository
git clone https://github.com/marctjones/my-gui-app.git
cd my-gui-app

# Connect to local environment using the code from Gemini
eddi-msgsrv connect --code TOR-XYZ789 --namespace claude-web@my-gui-app --alias local

# Output:
# 🔍 Searching for broker...
#   Code: TOR-XYZ789
#   Namespace: claude-web@my-gui-app
#   Time window: ±5 minutes
# ✓ Found broker at timestamp 1234567890
#   Broker ID: a1b2c3d4e5f6...
#
# ✓ Handshake successful!
#   Server: abc123def456.onion
#   Access token: XYZ123AB...
#
# ✓ Connected to local environment!
#   You can now send commands and receive logs in real-time.
```

**Claude Code Web now has:**
- ✅ Access to all project documentation (via git)
- ✅ Real-time connection to local environment (via eddi)
- ✅ Ability to execute commands locally
- ✅ Ability to receive logs from local execution

---

## The Development Cycle

### Cycle 1: Claude Code Web Plans & Develops

**In Claude Code Web:**

```
You: I want to build a GUI application that displays a list of users
with search functionality. Follow TDD - write tests first.
```

**Claude reads documentation (automatically):**
- `AI_INSTRUCTIONS/README.md` → Knows to use TDD
- `AI_INSTRUCTIONS/TESTING.md` → Knows coverage requirements (>80%)
- `AI_INSTRUCTIONS/LOGGING.md` → Knows to use structlog

**Claude creates feature branch:**
```bash
git checkout -b feature/user-list-gui
```

**Claude develops (TDD workflow):**

1. **Writes tests first:**
```python
# tests/test_user_list.py
import pytest
from src.gui.user_list import UserListWindow

def test_user_list_loads_users():
    window = UserListWindow()
    assert len(window.users) > 0

def test_user_list_search():
    window = UserListWindow()
    window.search("Alice")
    assert len(window.filtered_users) == 1
    assert window.filtered_users[0].name == "Alice"

def test_user_list_display():
    window = UserListWindow()
    assert window.is_visible()
```

2. **Runs headless tests (locally via eddi):**
```bash
# Claude Code Web sends command to local
eddi-msgsrv send "EXEC: pytest tests/test_user_list.py -v" --server local

# Waits for response from local environment
```

**Local environment executes:**
```bash
# idlergear log daemon captures this request
# Executes: pytest tests/test_user_list.py -v
# Streams output back to Claude Code Web via eddi

# Output (streamed to Claude):
# test_user_list.py::test_user_list_loads_users FAILED
# test_user_list.py::test_user_list_search FAILED
# test_user_list.py::test_user_list_display FAILED
# ImportError: No module named 'src.gui.user_list'
```

3. **Claude implements the code:**
```python
# src/gui/user_list.py
import tkinter as tk
from tkinter import ttk
import structlog

log = structlog.get_logger()

class UserListWindow:
    def __init__(self):
        log.info("user_list_window_init")
        self.users = self._load_users()
        self.filtered_users = self.users
        self.window = None

    def _load_users(self):
        log.info("loading_users")
        # Load users from database
        return [
            User(1, "Alice"),
            User(2, "Bob"),
            User(3, "Charlie")
        ]

    def search(self, query):
        log.info("user_search", query=query)
        self.filtered_users = [
            u for u in self.users
            if query.lower() in u.name.lower()
        ]

    def is_visible(self):
        return self.window is not None

class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name
```

4. **Runs tests again:**
```bash
eddi-msgsrv send "EXEC: pytest tests/test_user_list.py -v" --server local

# Output (streamed back):
# test_user_list.py::test_user_list_loads_users PASSED
# test_user_list.py::test_user_list_search PASSED
# test_user_list.py::test_user_list_display PASSED
# ==================== 3 passed in 0.12s ====================
```

5. **Checks coverage:**
```bash
eddi-msgsrv send "EXEC: pytest tests/test_user_list.py --cov=src.gui.user_list" --server local

# Output:
# src/gui/user_list.py    100%
```

6. **Commits:**
```bash
git add tests/test_user_list.py src/gui/user_list.py
git commit -m "feat: Add user list GUI with search functionality

- Implemented UserListWindow class
- Added user loading and search
- Tests: 3 passed, coverage: 100%"
git push origin feature/user-list-gui
```

### Cycle 2: Claude Tells Local to Test Interactively

**Claude Code Web sends command:**

```bash
eddi-msgsrv send "RUN_GUI: src.gui.user_list" --server local
```

**Local environment receives command:**

```bash
# idlergear log daemon listener sees: RUN_GUI: src.gui.user_list
# Executes:
python -m src.gui.user_list &
PID=$!

# Starts collecting logs
idlergear logs collect --pid $PID --stream-to eddi

# GUI window opens on local machine
# User can interact with it
```

**Local environment streams logs to Claude:**

```bash
# As user interacts with GUI, logs stream in real-time:

# User opens application:
LOG: 2025-11-18T10:30:15Z INFO user_list_window_init
LOG: 2025-11-18T10:30:15Z INFO loading_users

# User types "A" in search box:
LOG: 2025-11-18T10:30:20Z INFO user_search query="A"

# User types "Al":
LOG: 2025-11-18T10:30:21Z INFO user_search query="Al"

# User types "Alice":
LOG: 2025-11-18T10:30:22Z INFO user_search query="Alice"

# User clicks on Alice:
LOG: 2025-11-18T10:30:25Z ERROR user_click_failed user_id=1
LOG: 2025-11-18T10:30:25Z ERROR Traceback (most recent call last):
LOG:   File "src/gui/user_list.py", line 45, in on_user_click
LOG:     self.show_user_details(user_id)
LOG: AttributeError: 'UserListWindow' object has no attribute 'show_user_details'
```

**Claude Code Web receives error logs in real-time!**

### Cycle 3: Claude Fixes Bug Based on Logs

**In Claude Code Web (sees the error):**

```
Claude: I see the error from the GUI test. The UserListWindow is missing
the show_user_details method. Let me fix this.
```

**Claude implements the fix:**

```python
# src/gui/user_list.py
class UserListWindow:
    # ... existing code ...

    def show_user_details(self, user_id):
        """Show details dialog for a user."""
        log.info("show_user_details", user_id=user_id)
        user = next((u for u in self.users if u.id == user_id), None)
        if user:
            # Show details in a dialog
            details = f"User ID: {user.id}\nName: {user.name}"
            tk.messagebox.showinfo("User Details", details)
        else:
            log.error("user_not_found", user_id=user_id)
```

**Writes test:**

```python
# tests/test_user_list.py
def test_show_user_details():
    window = UserListWindow()
    # Mock messagebox
    with patch('tkinter.messagebox.showinfo') as mock:
        window.show_user_details(1)
        mock.assert_called_once()
        assert "Alice" in mock.call_args[0][1]
```

**Runs tests:**

```bash
eddi-msgsrv send "EXEC: pytest tests/test_user_list.py -v" --server local

# Output:
# test_user_list.py::test_user_list_loads_users PASSED
# test_user_list.py::test_user_list_search PASSED
# test_user_list.py::test_user_list_display PASSED
# test_user_list.py::test_show_user_details PASSED
# ==================== 4 passed in 0.15s ====================
```

**Commits:**

```bash
git add src/gui/user_list.py tests/test_user_list.py
git commit -m "fix: Add show_user_details method

Found via GUI testing - clicking on user failed.
Added implementation and test."
git push origin feature/user-list-gui
```

### Cycle 4: Claude Tells Local to Pull & Test Again

**Claude Code Web sends command:**

```bash
eddi-msgsrv send "PULL_AND_TEST: feature/user-list-gui" --server local
```

**Local environment:**

```bash
# idlergear listener receives command
# Executes:
git fetch origin
git checkout feature/user-list-gui
git pull origin feature/user-list-gui

# Restart GUI with new code
pkill -f "python -m src.gui.user_list"
python -m src.gui.user_list &
PID=$!

# Stream logs
idlergear logs collect --pid $PID --stream-to eddi

# Send confirmation
eddi-msgsrv send "GUI restarted with latest code. Test the user click again." --server local
```

**User tests locally:**

```
User clicks on Alice again...

Logs (streamed to Claude):
LOG: 2025-11-18T10:35:15Z INFO user_click user_id=1
LOG: 2025-11-18T10:35:15Z INFO show_user_details user_id=1
# Dialog shows: "User ID: 1\nName: Alice"

✓ Bug fixed! Everything works.
```

**Local sends success message:**

```bash
eddi-msgsrv send "GUI_TEST_PASSED: User click now shows details dialog correctly." --server local
```

### Cycle 5: Claude Creates PR

**Claude Code Web (sees success message):**

```bash
# Run full test suite
eddi-msgsrv send "EXEC: pytest tests/ -v --cov=src" --server local

# Output:
# ==================== 4 passed in 0.20s ====================
# src/gui/user_list.py    100%

# Create PR
gh pr create \
  --title "Add user list GUI with search" \
  --body "Implements user list with search functionality.

Features:
- Display list of users
- Search users by name
- Click to show details dialog

Tests: 4 passed, Coverage: 100%
GUI tested locally: All interactions work correctly."

# Output:
# https://github.com/marctjones/my-gui-app/pull/1
```

**Notify local Gemini:**

```bash
eddi-msgsrv send "PR_CREATED: #1 - User list GUI ready for review" --server local
```

---

## The Complete Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     LOCAL TERMINAL                            │
│                                                               │
│  1. idlergear new my-gui-app                                 │
│     ↓                                                         │
│  2. cd my-gui-app                                            │
│     ↓                                                         │
│  3. idlergear tools launch gemini                            │
│     ↓                                                         │
│  4. "Show me the connection code for Claude Code Web"        │
│     → TOR-XYZ789                                             │
└──────────────────────────────────────────────────────────────┘
                            ↓
                    Connection Code
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                  CLAUDE CODE WEB (Browser)                    │
│                                                               │
│  5. git clone github.com/marctjones/my-gui-app               │
│     cd my-gui-app                                            │
│     ↓                                                         │
│  6. eddi-msgsrv connect --code TOR-XYZ789 ... --alias local │
│     ✓ Connected to local environment!                        │
│     ↓                                                         │
│  7. "Build a GUI app with user list and search"             │
│     ↓                                                         │
│  8. Writes tests (TDD)                                       │
│     ↓                                                         │
│  9. Runs tests: eddi-msgsrv send "EXEC: pytest ..." --server local │
│     ← Tests fail (no implementation yet)                     │
│     ↓                                                         │
│  10. Implements code                                         │
│     ↓                                                         │
│  11. Runs tests again: eddi-msgsrv send "EXEC: pytest ..."  │
│     ← Tests pass! ✓                                          │
│     ↓                                                         │
│  12. Commits code                                            │
│     ↓                                                         │
│  13. Tells local to run GUI:                                 │
│      eddi-msgsrv send "RUN_GUI: src.gui.user_list" --server local │
└──────────────────────────────────────────────────────────────┘
                            ↓
                    RUN_GUI command
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                  LOCAL ENVIRONMENT                            │
│                                                               │
│  14. Receives: RUN_GUI: src.gui.user_list                    │
│      ↓                                                        │
│  15. Executes: python -m src.gui.user_list                   │
│      ↓                                                        │
│  16. GUI window opens (user can see it)                      │
│      ↓                                                        │
│  17. Starts log collection: idlergear logs collect --stream  │
│      ↓                                                        │
│  18. User interacts with GUI                                 │
│      ↓                                                        │
│  19. Error occurs: "AttributeError: ... show_user_details"   │
│      ↓                                                        │
│  20. Logs streamed to Claude Code Web via eddi               │
└──────────────────────────────────────────────────────────────┘
                            ↓
                      Error logs
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                  CLAUDE CODE WEB                              │
│                                                               │
│  21. Receives error logs in real-time                        │
│      ↓                                                        │
│  22. Analyzes error: Missing show_user_details method        │
│      ↓                                                        │
│  23. Implements fix                                          │
│      ↓                                                        │
│  24. Writes test for new method                              │
│      ↓                                                        │
│  25. Runs tests: eddi-msgsrv send "EXEC: pytest ..."        │
│      ← Tests pass! ✓                                         │
│      ↓                                                        │
│  26. Commits fix                                             │
│      ↓                                                        │
│  27. Tells local to pull & retest:                           │
│      eddi-msgsrv send "PULL_AND_TEST: feature/..." --server local │
└──────────────────────────────────────────────────────────────┘
                            ↓
                    PULL_AND_TEST command
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                  LOCAL ENVIRONMENT                            │
│                                                               │
│  28. git pull origin feature/user-list-gui                   │
│      ↓                                                        │
│  29. Restarts GUI with new code                              │
│      ↓                                                        │
│  30. User tests again                                        │
│      ↓                                                        │
│  31. Bug fixed! ✓                                            │
│      ↓                                                        │
│  32. Sends success: eddi-msgsrv send "GUI_TEST_PASSED" ...   │
└──────────────────────────────────────────────────────────────┘
                            ↓
                      Success message
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                  CLAUDE CODE WEB                              │
│                                                               │
│  33. Receives: GUI_TEST_PASSED                               │
│      ↓                                                        │
│  34. Runs full test suite: pytest tests/ -v --cov           │
│      ← All tests pass, coverage 100% ✓                       │
│      ↓                                                        │
│  35. Creates PR: gh pr create ...                            │
│      ↓                                                        │
│  36. Notifies local Gemini: eddi-msgsrv send "PR_CREATED" ..│
└──────────────────────────────────────────────────────────────┘
                            ↓
                      PR created! ✓
```

---

## Automation Scripts

### Local Listener Script

**File: `~/.idlergear/listeners/gui-tester.sh`**

```bash
#!/bin/bash
# Automatic GUI testing listener
# Monitors eddi messages and handles GUI testing requests

PROJECT_DIR="$(pwd)"

# Listen for messages from Claude Code Web
eddi-msgsrv listen --server local | while read -r msg; do
  case "$msg" in

    RUN_GUI:*)
      # Extract GUI module name
      module="${msg#RUN_GUI: }"

      echo "▶️  Starting GUI: $module"

      # Run GUI in background
      python -m "$module" &
      GUI_PID=$!

      # Start log collection and streaming
      idlergear logs collect --pid $GUI_PID --stream-to eddi &
      LOG_PID=$!

      # Store PIDs for cleanup
      echo "$GUI_PID" > /tmp/idlergear-gui.pid
      echo "$LOG_PID" > /tmp/idlergear-log.pid

      # Notify Claude
      eddi-msgsrv send "GUI started: $module (PID: $GUI_PID). Logs streaming." --server local
      ;;

    STOP_GUI)
      echo "⏹️  Stopping GUI"

      # Kill GUI and log collector
      if [ -f /tmp/idlergear-gui.pid ]; then
        kill $(cat /tmp/idlergear-gui.pid) 2>/dev/null
        rm /tmp/idlergear-gui.pid
      fi
      if [ -f /tmp/idlergear-log.pid ]; then
        kill $(cat /tmp/idlergear-log.pid) 2>/dev/null
        rm /tmp/idlergear-log.pid
      fi

      eddi-msgsrv send "GUI stopped." --server local
      ;;

    PULL_AND_TEST:*)
      # Extract branch name
      branch="${msg#PULL_AND_TEST: }"

      echo "🔄 Pulling branch: $branch"

      # Stop current GUI
      pkill -f "python -m src.gui" 2>/dev/null

      # Pull latest code
      git fetch origin
      git checkout "$branch"
      git pull origin "$branch"

      # Restart GUI
      python -m src.gui.user_list &
      GUI_PID=$!

      # Restart log collection
      idlergear logs collect --pid $GUI_PID --stream-to eddi &

      eddi-msgsrv send "Pulled $branch and restarted GUI. Test again!" --server local
      ;;

    EXEC:*)
      # Execute command
      cmd="${msg#EXEC: }"

      echo "⚙️  Executing: $cmd"

      # Run command and stream output
      eval "$cmd" 2>&1 | while read -r line; do
        eddi-msgsrv send "LOG: $line" --server local
      done

      eddi-msgsrv send "EXEC_COMPLETE: Exit code $?" --server local
      ;;

  esac
done
```

**Start the listener:**

```bash
# In local terminal (runs in background)
~/.idlergear/listeners/gui-tester.sh &

# Or use idlergear command (automatically starts listener)
idlergear eddi listen --handle-gui --handle-exec
```

---

## Key Benefits of This Workflow

### ✅ Best of Both Worlds

| Capability | Claude Code Web | Local Environment |
|------------|-----------------|-------------------|
| **Planning** | ✅ Excellent | ⚠️ Limited |
| **Coding** | ✅ Full codebase access | ✅ Full codebase access |
| **Headless Tests** | ✅ Via eddi → local | ✅ Direct |
| **GUI Testing** | ❌ No display | ✅ Full GUI access |
| **Log Collection** | ❌ Can't capture | ✅ Full access |
| **Long Tasks** | ❌ Timeouts | ✅ Unlimited |
| **Context** | ✅ All docs via git | ✅ All docs local |
| **Speed (headless)** | ⚡ Fast (cloud) | 🐌 Slower (SSH lag) |
| **Speed (GUI)** | ❌ N/A | ⚡ Instant (local) |

### ✅ Division of Labor

**Claude Code Web (Headless Development):**
- Planning and architecture
- Writing tests (TDD)
- Implementing business logic
- Running headless tests (pytest, unit tests)
- Code review and refactoring
- Creating PRs

**Local Environment (Interactive Testing):**
- Running GUI applications
- Interactive user testing
- Log collection from running apps
- Performance testing
- Integration testing with local services
- Database testing

**Gemini CLI (Coordination):**
- Project overview and status
- Reviewing changes from both environments
- Managing branches and PRs
- Providing context and documentation
- Code review

### ✅ Automatic Context

**Gemini reads on startup:**
```
AI_INSTRUCTIONS/README.md → All best practices
AI_INSTRUCTIONS/TESTING.md → TDD requirements
AI_INSTRUCTIONS/LOGGING.md → Logging guidelines
AI_INSTRUCTIONS/COLLABORATION.md → Multi-LLM workflow
VISION.md → Project goals
DESIGN.md → Technical architecture
TODO.md → Current tasks
```

**Claude Code Web reads from git:**
- Same documentation (synced via git)
- Always up-to-date
- No manual copy-paste

### ✅ Seamless Communication

**Three channels, all automatic:**

1. **Git** (code sync)
   - Claude commits → Local pulls
   - Always in sync

2. **eddi** (real-time commands)
   - `RUN_GUI` → Local executes
   - Logs stream back → Claude sees
   - 2-5 second latency

3. **MCP** (local Gemini)
   - Instant access to project state
   - No network latency
   - Rich data structures

### ✅ Complete Workflow

```
Create project → Launch Gemini → Get code → Connect Claude Web
                                                    ↓
                                            Plan & develop
                                                    ↓
                                            Run headless tests
                                                    ↓
                                            Tests pass? → Commit
                                                    ↓
                                            Tell local: RUN_GUI
                                                    ↓
Local: Run GUI ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
    ↓
Collect logs → Stream to Claude → → → → → → → → → →
                                                    ↓
                                            Analyze logs
                                                    ↓
                                            Find bugs
                                                    ↓
                                            Fix bugs
                                                    ↓
                                            Run headless tests
                                                    ↓
                                            Tests pass? → Commit
                                                    ↓
                                            Tell local: PULL_AND_TEST
                                                    ↓
Local: Pull & restart GUI ← ← ← ← ← ← ← ← ← ← ← ←
    ↓
Test again
    ↓
Bug fixed? ✓ → Notify Claude → → → → → → → → → →
                                                    ↓
                                            Create PR
                                                    ↓
                                            Done! 🎉
```

---

## Common Commands Cheatsheet

### Initial Setup (Once)

```bash
# Create project
idlergear new my-app --lang python --llm-tools gemini,claude --enable-logs --enable-messaging

# Enter directory
cd my-app

# Launch local LLM
idlergear tools launch gemini

# Get connection code for web
# (In Gemini): "Show me the connection code for Claude Code Web"
# Output: TOR-XYZ789
```

### Claude Code Web (Browser)

```bash
# Clone and connect (once)
git clone https://github.com/user/my-app.git
cd my-app
eddi-msgsrv connect --code TOR-XYZ789 --namespace claude-web@my-app --alias local

# Run tests
eddi-msgsrv send "EXEC: pytest tests/ -v" --server local

# Run GUI for testing
eddi-msgsrv send "RUN_GUI: src.gui.main" --server local

# Stop GUI
eddi-msgsrv send "STOP_GUI" --server local

# Pull and restart with new code
eddi-msgsrv send "PULL_AND_TEST: feature/my-branch" --server local

# Get logs
eddi-msgsrv send "LOGS: show --errors-only --since='10 minutes'" --server local
```

### Local Environment

```bash
# Start GUI listener (automatic handler)
idlergear eddi listen --handle-gui --handle-exec

# Or manual listener
~/.idlergear/listeners/gui-tester.sh &

# Check status
idlergear status

# View logs
idlergear logs show --since "1 hour ago"
idlergear logs stream --follow
```

### Local Gemini CLI

```bash
# Get project status
"Show me the project status"

# Get connection info
"Show me the connection code for Claude Code Web"

# Review changes
"What has Claude Code Web been working on?"

# Check logs
"Show me error logs from the last hour"

# Get test coverage
"What's our test coverage?"
```

---

## Advanced: Screenshot Capture

**For GUI debugging, you can also capture screenshots:**

### Enhanced Listener Script

```bash
# Add to ~/.idlergear/listeners/gui-tester.sh

SCREENSHOT)
  echo "📸 Capturing screenshot"

  # Capture screenshot
  import -window root /tmp/screenshot.png

  # Convert to base64
  base64 /tmp/screenshot.png > /tmp/screenshot.b64

  # Send to Claude (in chunks if needed)
  eddi-msgsrv send "SCREENSHOT: $(cat /tmp/screenshot.b64)" --server local

  # Cleanup
  rm /tmp/screenshot.png /tmp/screenshot.b64
  ;;
```

### Claude requests screenshot

```bash
# When Claude sees an error it doesn't understand
eddi-msgsrv send "SCREENSHOT" --server local

# Receives base64-encoded image
# Claude can analyze GUI state visually
```

---

## Summary

This workflow gives you:

✅ **Zero-friction setup** - One command creates everything
✅ **Automatic LLM context** - All documentation read automatically
✅ **Seamless local/web collaboration** - Simple connection code
✅ **Real-time feedback loop** - Logs stream instantly
✅ **Best of both worlds** - Web for coding, local for GUI testing
✅ **Complete automation** - Listeners handle all the complexity

**The killer feature:** Claude Code Web can develop and test headless code, then delegate interactive testing to your local machine, receive logs in real-time, fix bugs, and repeat - all without you manually copying logs or switching contexts.

**Next steps:**
1. Try it: `idlergear new my-first-app`
2. Launch Gemini: `idlergear tools launch gemini`
3. Connect Claude Web with the code
4. Start building!
