# DESIGN.md: Project "IdlerGear"

This document outlines the design and implementation tasks for a command-line tool designed to automate project scaffolding and manage development workflows across multiple LLM-based coding assistants.

All AI-assisted development (via `gemini cli`, `copilot cli`, `claude cli`, etc.) should refer to this document as the single source of truth for goals, constraints, and tasks.

## 1. Project Metadata

* **Owner:** marctjones
* **Project Name:** `IdlerGear`
* **GitHub Repo:** `https://github.com/marctjones/idlergear`

## 2. Core Mission

To design and build a command-line tool that automates the repetitive "toil" of project setup and development, acting as a "meta-assistant" that manages the developer's workflow and their interaction with various LLM coding tools.

The primary goals are to:
1.  **Scaffold New Projects:** Automate the creation of local directories, `git` initialization, and **private-by-default** GitHub repositories, complete with language-specific `.gitignore` files.
2.  **Establish Project Context:** Automatically create and maintain a set of "charter" documents (`VISION.md`, `TODO.md`, `IDEAS.md`) to define the project's purpose, track tasks, and prevent scope creep.
3.  **Unify LLM Interaction:** Act as a "wrapper" for calling different LLM CLIs (`gemini`, `claude`, etc.), automatically providing them with the full project context (the charter files, recent logs, etc.) on every invocation.
4.  **Enforce Best Practices:** Nudge the developer and the LLMs to adhere to Test-Driven Development (TDD), write extensive unit/integration tests, maintain high code coverage, and produce granular developer-focused logging.
5.  **Streamline Development:** Manage a simple, consistent `./run.sh` script for testing, which captures detailed logs from the last run for easy debugging with an LLM.
6.  **Manage Multi-LLM Workflows:** Simplify switching between LLM assistants, enable them to "check" each other's work, and (in the future) manage syncing code and data files between local and web-based environments (like Claude Web).

## 3. Development Principles & Methodology

This project will adhere to the following principles to ensure quality, security, and maintainability.

* **Isolated Development Environments:** All projects *must* use language-specific isolated environments (e.g., Python `venv`, Node.js local `node_modules`, Rust workspaces, Go modules). Dependencies are installed into the project's isolated environment, never globally. This ensures reproducibility and prevents version conflicts.
* **Dogfooding:** We will use `IdlerGear` to build and manage the `IdlerGear` project itself as soon as it is minimally viable.
* **Iterative & TDD:** This tool *must* be built using TDD. We will write unit and integration tests for every feature.
* **Git Workflow:** All new features will be in branches and merged via PRs. We will commit frequently.
* **Working Demos:** We will create simple, working demos for each major feature (e.g., scaffolding, the LLM wrapper) before combining them.
* **Language Best Practices:** We will follow all best practices for the chosen language (e.g., `clippy`/`rustfmt` for Rust, `black`/`flake8` for Python).
* **Dependency & Licensing:** We will **strongly prefer** permissive licenses (MIT, Apache 2.0). All Copyleft (GPL, etc.) dependencies must be explicitly approved.
* **Guard Against Scope Creep:** `IdlerGear` does one thing: it manages the *workflow* and *context* of a project. It is *not* an IDE, a new shell, or a build system. Out-of-scope ideas will be logged in this tool's own `IDEAS.md` file.

## 4. Core Architectural Constraints

* **CLI-First:** The tool must be a pure command-line interface.
* **Cross-Platform (Target):** The tool must work on Ubuntu (primary) and Windows 11 (secondary).
* **External Tool Interaction:** The tool will need to execute other shell commands (e.g., `git`, `gemini`, `claude`, `gh`).
* **API-Driven:** The tool will need to interact with the GitHub API for repo creation and management.

## 5. Technology Stack (Proposed)

* **Language:** **Python 3** (with `typer` or `click`).
    * *Rationale:* This is the user's strongest language, allowing for rapid prototyping of the complex logic. Key libraries (`GitPython`, `PyGithub`, `python-dotenv`) are mature.
* **Authentication:** GitHub Personal Access Tokens (PATs) or OAuth, to be stored securely in the system keychain or an environment file (e.g., `.env`).

## 6. Phase 1: The Local Scaffolder

The first "working demo."

* **Command:** `idlergear new <project-name> --lang <language>`
* **Actions:**
    1.  Creates directory `<project-name>`.
    2.  Runs `git init`.
    3.  Fetches a language-specific `.gitignore` (e.g., from `gitignore.io`) and saves it.
    4.  Creates `README.md` with `# <project-name>`.
    5.  Creates `VISION.md` (from a template).
    6.  Creates `IDEAS.md` (from a template, for out-of-scope items).
    7.  Creates `TODO.md` (a simple checklist for bugs/features).
    8.  Performs the initial `git commit`.
* **Out of Scope for Phase 1:** GitHub API interaction. This phase is local-only.

## 7. Core Design Modules & Future Phases

This outlines the major components to be built after Phase 1.

* **Module 1: GitHub Integration (Phase 2):**
    * **Command:** `idlergear github create`
    * **Action:** Reads GitHub auth, creates a **private** repo on `github.com/marctjones`, adds the `origin` remote, and pushes the initial commit.

* **Module 2: The LLM Wrapper (Phase 3 - The Core Feature):**
    * **Command:** `idlergear ask <llm-name> "My prompt..."` (e.g., `idlergear ask gemini "Write a test for the main function"`)
    * **Action:**
        1.  Collects context: Reads `VISION.md`, `TODO.md`, and (optionally) the last run log from `./run.sh`.
        2.  Constructs a "system prompt" containing this context.
        3.  Executes the *actual* LLM command (e.g., `gemini -p "--- PROJECT CONTEXT --- ... --- END CONTEXT --- My prompt..."`).

* **Module 3: Run Script Manager (Phase 4):**
    * **Command:** `idlergear run-script create`
    * **Action:** Creates a `./run.sh` script that:
        1.  Sets up the environment (e.g., `python -m venv venv`, `source venv/bin/activate`).
        2.  Sets granular logging levels (e.g., `export LOG_LEVEL=DEBUG`).
        3.  Runs the project's main command (e.g., `python -m src.main`)
        4.  **Pipes** detailed `stdout` and `stderr` to a version-controlled log file (e.g., `.logs/last_run.log`). The `idlergear ask` command will be configured to read this file.

* **Module 4: Git Sync (Phase 5 - Advanced):**
    * **Commands:** `idlergear sync push`, `idlergear sync pull`
    * **Action:** Implements the "Web UI Sync" feature. `sync push` will create a temp branch, add *all* files (even data files), and push. `sync pull` will fetch that branch, merge it, and optionally clean it up. This is for syncing with tools like Claude Web.

* **Module 5: The "Nudger" (Phase 6):**
    * **Command:** `idlergear check`
    * **Action:** Analyzes `git log` and file timestamps to provide "best practice" reminders:
        * "You haven't added a test in the last 3 commits."
        * "Your `VISION.md` hasn't been updated in 30 days."
        * "You haven't committed to `main` in 24 hours."

## 8. Security & Logging

* **Logging:** `IdlerGear` itself will use extensive, granular logging (via Python `logging`).
* **Security:** GitHub PATs/OAuth tokens are sensitive. They **must not** be stored in plain text. We will use the system keychain (e.g., `keyring`) or a `.env` file (with a `.gitignore` entry) as a first step.

## 9. Next Steps (Task List for AI)

1.  [X] **Task:** Confirm the project name. *(Done: "IdlerGear")*
2.  [ ] **Task:** Confirm the Technology Stack (Python for V1).
3.  [ ] **Task:** Begin implementation of **Phase 1: The Local Scaffolder**. (I can help you write the `click` or `typer` code for this first command).

## 10. Appendix: Alternative Architectures (Future Exploration)

This section documents alternative designs that were discussed. They are considered **out of scope** for the current project.

* **A-2: Metaprogramming (Scheme/Racket):** Exploring how a Lisp-like language could *generate* the project structure and context-aware wrappers.
* **A-3: Direct LLM IPC:** A more advanced version of Module 4 where two local LLM CLIs could "talk" to each other via file-based message passing, managed by `IdlerGear`.
* **A-4: GitHub Template Repo:** `IdlerGear` could maintain a *personal GitHub template repository* for you, and new projects would be a "clone" of this template, ensuring all your preferences are pre-configured.
* **A-5: "LLM-in-LLM" Detection:** The feature where a program *being built* by `IdlerGear` can auto-detect it's running *inside* an LLM (like Claude Web) and use it as a service backend.
