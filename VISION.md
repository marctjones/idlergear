# Project Vision: IdlerGear

## Core Mission

To design and build a command-line tool that automates the repetitive "toil" of project setup and development, acting as a "meta-assistant" that manages the developer's workflow and their interaction with various LLM coding tools.

The primary goals are to:
1.  **Scaffold New Projects:** Automate the creation of local directories, `git` initialization, and **private-by-default** GitHub repositories, complete with language-specific `.gitignore` files.
2.  **Establish Project Context:** Automatically create and maintain a set of "charter" documents (`VISION.md`, `TODO.md`, `IDEAS.md`) to define the project's purpose, track tasks, and prevent scope creep.
3.  **Unify LLM Interaction:** Act as a "wrapper" for calling different LLM CLIs (`gemini`, `claude`, etc.), automatically providing them with the full project context (the charter files, recent logs, etc.) on every invocation.
4.  **Enforce Best Practices:** Nudge the developer and the LLMs to adhere to Test-Driven Development (TDD), write extensive unit/integration tests, maintain high code coverage, and produce granular developer-focused logging.
5.  **Streamline Development:** Manage a simple, consistent `./run.sh` script for testing, which captures detailed logs from the last run for easy debugging with an LLM.
6.  **Manage Multi-LLM Workflows:** Simplify switching between LLM assistants, enable them to "check" each other's work, and (in the future) manage syncing code and data files between local and web-based environments (like Claude Web).

## Development Principles

* **Dogfooding:** We will use `IdlerGear` to build and manage the `IdlerGear` project itself as soon as it is minimally viable.
* **Iterative & TDD:** This tool *must* be built using TDD. We will write unit and integration tests for every feature.
* **Git Workflow:** All new features will be in branches and merged via PRs. We will commit frequently.
* **Working Demos:** We will create simple, working demos for each major feature before combining them.
* **Language Best Practices:** We will follow all best practices for the chosen language.
* **Dependency & Licensing:** We will **strongly prefer** permissive licenses (MIT, Apache 2.0). All Copyleft (GPL, etc.) dependencies must be explicitly approved.
* **Guard Against Scope Creep:** `IdlerGear` does one thing: it manages the *workflow* and *context* of a project. It is *not* an IDE, a new shell, or a build system. Out-of-scope ideas will be logged in this tool's own `IDEAS.md` file.
