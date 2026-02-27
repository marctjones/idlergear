# IdlerGear Vision

---

### Mission

**IdlerGear is structured project management for AI-assisted development.**

It provides a command-based API that both humans and AI assistants can use to track work, capture knowledge, and maintain project context across sessions.

### The Problem

AI coding assistants are stateless. Every session starts fresh. You constantly re-explain:
- What the project is trying to achieve
- What you learned last session about how something works
- What issues were discovered but deferred
- What the current implementation plan is
- What happened when you ran that script

### The Solution

A **command-based API** that manages project knowledge across sessions, machines, and teams.

Six knowledge types. Backend-agnostic. Works across all AI assistants.

### Key Insight

**AI assistants AND humans need structured, high-quality persistent memory across sessions.**

That's why IdlerGear has categories (tasks, notes, references, vision, plans, runs) instead of a single blob of context. Structure enables:

- **Efficiency** - Query just what you need (`task list --label bug`) instead of loading everything
- **Quality** - Each type has appropriate fields (tasks have priority, references have titles)
- **Flow** - Knowledge moves through stages (note → task → plan, or note → reference)
- **Token savings** - 97% reduction (17K → 570 tokens) via structured queries

A structured API serves both humans and AI better than unstructured markdown files.

### IdlerGear vs AGENTS.md

AGENTS.md defines **file naming conventions** in natural language:
> "Look for the vision in docs/VISION.md"

IdlerGear provides a **structured command-based API**:
```bash
idlergear vision show    # Returns the vision, wherever it's stored
```

The difference:
- **Consistent interface** - Same command across all projects
- **Backend-agnostic** - Could be local file, GitHub, Jira, or central server
- **Configurable** - Project decides where data lives, command stays the same
- **Deterministic** - No AI interpretation needed, just run the command
- **Write capability** - AI can store knowledge, not just read it

**IdlerGear IS the structured version of AGENTS.md**, implemented as an API instead of prose.

**Compatibility:** AGENTS.md can reference IdlerGear: "Use `idlergear task list` for issues, `idlergear vision show` for project direction."

### The Adoption Challenge

IdlerGear works, but getting AI assistants to use it consistently requires:

| Direction | Challenge | Solution |
|-----------|-----------|----------|
| **Read** | AI prefers file search | MCP tools appear as native |
| **Write** | AI doesn't think to store discoveries | Hooks, slash commands, training |

**The goal:** A virtuous cycle where AI queries IdlerGear for context, stores discoveries via API, and knowledge accumulates across sessions instead of resetting.

See issue #94 for adoption strategies.

### What IdlerGear Is NOT

- **Not an IDE** - It manages project knowledge, not editing
- **Not a build system** - Use make, cargo, npm for that
- **Not an AI wrapper** - It provides context TO AI tools
- **Not a cloud service** - Runs locally, your data stays local
- **Not enterprise-only** - Works solo, scales to teams

### Cross-Assistant Strategy

IdlerGear is **AI-assistant agnostic**. It works identically across:
- Claude Code
- Gemini CLI
- GitHub Copilot CLI
- OpenAI Codex CLI
- Aider
- Block's Goose

**Why this matters:** Developers use multiple AI assistants. Project knowledge should persist regardless of which assistant is active.

**How it works:**
1. **MCP-first** - Universal tool protocol supported by all major assistants
2. **CLI fallback** - Same commands work via shell when MCP isn't available
3. **Project instructions** - Generate appropriate files for each assistant

---
