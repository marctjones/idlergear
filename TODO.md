# IdlerGear: TODO List

This file tracks the high-level feature and bug list for the `IdlerGear` project.

## Phase 1: The Template-Based Scaffolder ✅

*   [x] **Task:** Design the CLI structure using `typer` or `click`.
*   [x] **Task:** Implement GitHub Authentication (using Personal Access Token).
*   [x] **Task:** Create a new private GitHub repository to serve as the project template (e.g., `idlergear-template`).
    *   [x] Populate it with the base files: `VISION.md`, `TODO.md`, `IDEAS.md`, `README.md`, `DEVELOPMENT.md`.
    *   [x] Create `AI_INSTRUCTIONS/` directory with a single universal `README.md` file.
    *   [x] Use placeholders like `{{PROJECT_NAME}}` in the template files.
*   [x] **Task:** Implement the `idlergear new <project-name> --lang <language>` command.
    *   [x] Use the GitHub API to create a new repository from the template.
    *   [x] Clone the newly created repository.
    *   [x] Customize the cloned files (replace placeholders).
    *   [ ] Set up language-specific isolated environment (venv for Python, etc.).
    *   [ ] Fetch and apply the correct language-specific `.gitignore`.
    *   [ ] Create the project-specific `.idlergear.toml` configuration file.
    *   [x] Perform the initial `git commit` and push to the new remote repository.
*   [ ] **Task:** Implement the Configuration System.
    *   [ ] Create logic to load global config from `~/.config/idlergear/config.toml`.
    *   [ ] Create logic to load project-specific config from `<project-dir>/.idlergear.toml`.
    *   [ ] Ensure project-specific settings override global settings.
*   [x] **Task:** Add unit tests for the `new` command.
*   [x] **Task:** Set up the basic Python project structure (`src`, `tests`, etc.).
*   [x] **Task:** Set up Testing Framework.
    *   [x] Create a `tests/` directory.
    *   [x] Add a basic `test_main.py` with a placeholder test.
    *   [x] Ensure `pytest` runs successfully.

**Phase 1 Status:** Core functionality complete! Projects can be scaffolded from template. Remaining: language-specific environment setup, .gitignore fetching, and configuration system.
