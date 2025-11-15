# IdlerGear: Future Ideas & Scope Boundaries

This document tracks ideas that are interesting but out-of-scope for the current development phase. This helps prevent scope creep while ensuring good ideas are not lost.

---

## Phase 3 Rethinking: IdlerGear as Infrastructure, Not a Wrapper

**Original Phase 3 idea:** `idlergear ask gemini "write a test"` - wrapper around LLM CLIs
**Better architecture:** IdlerGear provides tools and context that ANY LLM can discover and use

### The Real Vision:
1. **Setup:** `idlergear new my-project` creates project with all best practices baked in
2. **Discovery:** Any LLM tool (Gemini CLI, Claude CLI, Copilot CLI, Claude Web) reads `DEVELOPMENT.md` and `AI_INSTRUCTIONS/README.md` automatically
3. **Tools:** IdlerGear exposes commands that LLMs can invoke as tools:
   - `idlergear status` - Project health (git status, test results, coverage, recent commits)
   - `idlergear context` - Get full project context (charter docs + recent activity)
   - `idlergear logs` - Get recent run logs for debugging
   - `idlergear check` - Best practice nudges and reminders
4. **Use Your Preferred Interface:** Keep using your favorite LLM interface (Gemini, Claude, Copilot, Web UIs)

### Why This Is Better:
- ✅ Don't force users to change their workflow
- ✅ Works with ANY LLM tool (current and future)
- ✅ Composable - works alongside other tools
- ✅ IdlerGear focuses on what it's good at: project structure, best practices, and introspection
- ✅ LLMs can register IdlerGear commands as tools they can invoke

### Potential: Model Context Protocol (MCP) Server
- IdlerGear could implement MCP (Model Context Protocol)
- Claude Desktop and other MCP-compatible tools could connect to it
- Provides standardized tools for project introspection
- LLMs get rich context without manual prompting

---

## Next Phase Priorities

### Phase 3: Enhanced Project Introspection Tools
Commands that LLMs (or humans) can invoke to understand project state:
- `idlergear status` - Comprehensive project status
- `idlergear context` - Generate LLM-ready project context
- `idlergear logs` - Access and filter run logs
- `idlergear test` - Run tests with LLM-friendly output

### Phase 4: Run Script Manager
- `idlergear run-script create` - Generate standardized `./run.sh`
- Capture detailed logs for debugging
- Integrate with testing frameworks

### Phase 5: Git Sync for Web UIs
- `idlergear sync push` - Push everything to temp branch for web-based LLM tools
- `idlergear sync pull` - Pull changes back from web sessions
- Use case: Work seamlessly between local CLI and Claude Web

---

## Alternative Architectures (Future Exploration)

These are alternative designs that were considered but are out of scope for the current project.

*   **A-1: Rust-Based (V2):** A full rewrite in Rust for a single, fast, cross-platform binary. This is the planned V2.
*   **A-2: Metaprogramming (Scheme/Racket):** Exploring how a Lisp-like language could *generate* the project structure and context-aware wrappers.
*   **A-3: Direct LLM IPC:** A more advanced version of the LLM wrapper where two local LLM CLIs could "talk" to each other via file-based message passing, managed by `IdlerGear`.
*   **A-4: GitHub Template Repo:** `IdlerGear` could maintain a *personal GitHub template repository* for you, and new projects would be a "clone" of this template, ensuring all your preferences are pre-configured.
*   **A-5: "LLM-in-LLM" Detection:** The feature where a program *being built* by `IdlerGear` can auto-detect it's running *inside* an LLM (like Claude Web) and use it as a service backend.

## Potential New Features (Post-V1)

*   **Interactive Mode:** An interactive `idlergear init` command that walks the user through setting up a new project.
*   **Configuration File:** A `~/.idlergear/config.toml` file for setting default author, GitHub username, preferred LLM, etc.
*   **Plugin System:** A system for adding new languages, frameworks, or LLM wrappers.
*   **LLM Cost & Credit Management:** A feature where `idlergear` could check the API credit status for various LLM services and recommend the most cost-effective tool for a given task.
*   **Real-time Telemetry Service:** A background service managed by `idlergear` that could capture and stream real-time telemetry (e.g., via OpenTelemetry) from a running application directly into an LLM's context for live debugging.
*   **IDE/Editor Integration:** A command like `idlergear open` that launches a specified IDE (e.g., VS Code) and automatically opens the key project context files (`VISION.md`, `TODO.md`, etc.) to prepare the workspace for an AI assistant.
*   **Automate Interactive Prompts:** A helper tool or module within `idlergear` to automate interactive terminal prompts, potentially using libraries like `pexpect` or concepts from `expect` (Tcl/Tk).
