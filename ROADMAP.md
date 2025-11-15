# IdlerGear Roadmap: Complete Vision

## Current State: Phase 1 ✅
- Template-based project scaffolding
- GitHub repo creation and cloning
- Best practices documentation included
- Works with any LLM that can read files

## Phase 3: Project Introspection & LLM Tooling (NEXT)

### Commands for LLM Tools to Invoke:

1. **`idlergear status`** - Project health at a glance
   - Git status, branch, uncommitted changes
   - Recent commits
   - Test results and coverage
   - Charter document freshness

2. **`idlergear context`** - Generate LLM-ready context
   - All charter documents concatenated
   - Recent git activity
   - Current status
   - Formatted for easy LLM consumption

3. **`idlergear logs`** - Access run logs
   - Last test run output
   - Last build output
   - Filterable and parseable

4. **`idlergear check`** - Best practice nudges
   - Analyze git history for test additions
   - Check charter document freshness
   - Identify uncommitted work

### LLM Tool Integration:
- **Copilot CLI** - Can invoke idlergear commands as tools
- **Claude Code** - Can call idlergear commands
- **Gemini CLI** - Can use idlergear commands
- **Web UIs** - Can read idlergear output

## Phase 4: Environment Automation

### Automatic Environment Setup:
- **Language detection** - Detect project language from files
- **Auto-create isolated environment:**
  - Python: `python -m venv venv && pip install -r requirements.txt`
  - Node: `npm install` or `yarn install`
  - Rust: `cargo build`
  - Go: `go mod download`
- **Command:** `idlergear setup` or auto-run on `idlergear new`

### LLM Tool Installation & Launch:
- **`idlergear tools install <tool>`** - Install LLM coding tool
  - `idlergear tools install gemini` - Install Gemini CLI
  - `idlergear tools install claude` - Install Claude CLI
  - `idlergear tools install copilot` - Install GitHub Copilot CLI
- **`idlergear tools launch <tool>`** - Launch the right tool for this project
  - Reads project config to determine preferred tool
  - Launches with proper context

### API Key Management (Future):
- **`idlergear keys setup`** - Interactive API key setup
- Store in system keychain (not in repo!)
- Auto-configure for Gemini, Claude, OpenAI, etc.
- Per-project or global configuration

## Phase 5: Web ↔ Local Coordination

### The Problem:
- You work in Claude Code Web
- You also work locally with Gemini CLI
- Need to coordinate branches, share files, sync state

### The Solution:

1. **`idlergear sync push`** - Push to web environment
   - Creates temporary branch (e.g., `idlergear-web-sync`)
   - Adds ALL files (including data, temp files, .env templates)
   - Pushes to GitHub
   - Web UI can pull this branch

2. **`idlergear sync pull`** - Pull from web environment
   - Fetches the web sync branch
   - Merges changes
   - Cleans up sync branch
   - Keeps main history clean

3. **`idlergear sync status`** - Show sync state
   - What's in web that's not local?
   - What's local that's not in web?

4. **File Transfer Without Git History:**
   - Sync files that shouldn't be in permanent history
   - Data files, temporary results, experiment outputs
   - Use the sync branch as a transfer mechanism

### Cross-LLM Coordination:
- **Scenario:** Gemini CLI locally + Claude Web remotely
- **Workflow:**
  1. Work locally with Gemini CLI
  2. `idlergear sync push` - Push state to sync branch
  3. Open Claude Web, switch to sync branch
  4. Work in Claude Web
  5. `idlergear sync pull` - Pull changes back locally
  6. Continue with Gemini CLI

### IPC Between Local & Web LLMs:
- **Structured communication via sync branch:**
  - `.idlergear/messages/` directory
  - Local LLM writes message file
  - `idlergear sync push`
  - Web LLM reads message, responds
  - `idlergear sync pull`
  - Local LLM reads response

## Phase 6: Advanced Features

### The "Nudger" - Intelligent Reminders:
- **`idlergear check`** analyzes your workflow:
  - "You haven't added tests in the last 3 commits"
  - "TODO.md hasn't been updated in 2 weeks"
  - "You have 10 uncommitted files"
  - "VISION.md is stale (not updated in 30 days)"

### Configuration System:
- **Global:** `~/.config/idlergear/config.toml`
  ```toml
  [user]
  name = "marctjones"
  github_username = "marctjones"
  preferred_llm = "gemini"
  
  [llm.gemini]
  cli_path = "/usr/local/bin/gemini"
  api_key_source = "keychain"
  
  [llm.claude]
  cli_path = "/usr/local/bin/claude"
  ```

- **Per-Project:** `<project>/.idlergear.toml`
  ```toml
  [project]
  name = "my-awesome-project"
  language = "python"
  preferred_llm = "claude"
  
  [environment]
  python_version = "3.13"
  ```

### Run Script Manager:
- **`idlergear run-script create`** - Generate `./run.sh`
  - Sets up environment
  - Runs tests with detailed logging
  - Captures output to `.logs/last_run.log`
  - LLM tools can read logs for debugging

## Implementation Priority

### Immediate (Next Sprint):
1. ✅ Phase 1 Complete
2. 🚧 **Phase 3 Core:** `idlergear status` command
3. 🚧 **Phase 3 Core:** `idlergear context` command

### Short Term (Next Month):
4. Phase 3: `idlergear logs` and `idlergear check`
5. Phase 4: Auto environment setup on `idlergear new`
6. Phase 4: Language-specific `.gitignore` fetching

### Medium Term (Next Quarter):
7. Phase 5: `idlergear sync push/pull` for web coordination
8. Phase 4: LLM tool installation helpers
9. Configuration system (global and per-project)

### Long Term (Future):
10. API key management and auto-configuration
11. MCP (Model Context Protocol) server implementation
12. Cross-LLM IPC mechanisms
13. Advanced "nudger" features

## Key Principles

1. **Don't wrap LLM tools** - Provide infrastructure they can use
2. **Work with ANY LLM** - Present and future
3. **Keep users in their preferred workflow** - Don't force a new interface
4. **Discoverable** - LLMs can find and use idlergear features
5. **Composable** - Works alongside other tools
6. **Cross-platform** - Local CLI and Web UIs
7. **Security-first** - Never commit secrets

---

**This roadmap represents the complete vision for IdlerGear as an LLM coding infrastructure tool.**
