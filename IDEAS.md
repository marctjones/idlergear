# IdlerGear: Future Ideas & Scope Boundaries

This document tracks ideas that are interesting but out-of-scope for the current development phase. This helps prevent scope creep while ensuring good ideas are not lost.

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
