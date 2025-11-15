# IdlerGear: TODO List

This file tracks the high-level feature and bug list for the `IdlerGear` project.

## Phase 1: The Template-Based Scaffolder

*   [ ] **Task:** Design the CLI structure using `typer` or `click`.
*   [ ] **Task:** Implement GitHub Authentication (using Personal Access Token).
*   [ ] **Task:** Create a new private GitHub repository to serve as the project template (e.g., `idlergear-template`).
    *   [ ] Populate it with the base files: `VISION.md`, `TODO.md`, `IDEAS.md`, `README.md`.
    *   [ ] Create `AI_INSTRUCTIONS/` directory and populate it with a generic `GEMINI.md` file.
    *   [ ] Use placeholders like `{{PROJECT_NAME}}` in the template files.
*   [ ] **Task:** Implement the `idlergear new <project-name> --lang <language>` command.
    *   [ ] Use the GitHub API to create a new repository from the template.
    *   [ ] Clone the newly created repository.
    *   [ ] Customize the cloned files (replace placeholders).
    *   [ ] Fetch and apply the correct language-specific `.gitignore`.
    *   [ ] Create the project-specific `.idlergear.toml` configuration file.
    *   [ ] Perform the initial `git commit` and push to the new remote repository.
*   [ ] **Task:** Implement the Configuration System.
    *   [ ] Create logic to load global config from `~/.config/idlergear/config.toml`.
    *   [ ] Create logic to load project-specific config from `<project-dir>/.idlergear.toml`.
    *   [ ] Ensure project-specific settings override global settings.
*   [ ] **Task:** Add unit tests for the `new` command.
*   [ ] **Task:** Set up the basic Python project structure (`src`, `tests`, etc.).
*   [ ] **Task:** Set up Testing Framework.
    *   [ ] Create a `tests/` directory.
    *   [ ] Add a basic `test_main.py` with a placeholder test.
    *   [ ] Ensure `pytest` runs successfully.
