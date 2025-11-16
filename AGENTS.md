# Repository Guidelines

## Project Structure & Module Organization
`src/` holds the CLI modules (e.g., `logs.py`, `sync.py`, `mcp_server.py`) and `main.py` wires commands together. Tests live in `tests/` with feature-focused suites such as `test_logs_pipe.py` and `test_new_command.py`. Charter docs (`VISION.md`, `DESIGN.md`, `ROADMAP.md`) capture intent, while `AI_INSTRUCTIONS/` defines assistant policies. Use `run.sh` as the single entry point; it bootstraps the `venv`, installs deps, runs quality gates, and invokes `src/main.py`.

## Build, Test, and Development Commands
```bash
python -m venv venv && source venv/bin/activate  # one-time env setup
pip install -r requirements.txt                  # manual install when skipping run.sh
./run.sh                                         # formatter, linter, tests, app
python -m pytest --cov=src --cov-report=term-missing  # focused test runs
python -m black src/ && python -m ruff check src/     # format + lint before commits
```
Keep dependencies synced via `pip-compile`/`pip-sync` (already automated inside `run.sh`).

## Coding Style & Naming Conventions
Python files use 4-space indentation, PEP 8 naming (modules/functions snake_case, classes PascalCase, constants UPPER_SNAKE). Run `black` for formatting and `ruff` for linting; do not hand-edit style. Logs should use the existing helpers in `src/logs.py` rather than ad-hoc `print` so output stays uniform.

## Testing Guidelines
`pytest` drives unit and integration coverage; target ≥80% coverage (enforced via `run.sh`). Name suites `tests/test_<feature>.py` and functions `test_<behavior>`. Favor fixtures for GitHub or filesystem contexts, and use async-aware tests per `pytest.ini`. Add regression tests for every bugfix, even if only exercising CLI parsing.

## Commit & Pull Request Guidelines
Follow the Conventional Commit pattern observed in history (`feat:`, `fix:`, etc.) plus a short subject (e.g., `feat: implement log coordinator`). Each PR should include: problem statement, summary of changes, tests run (`./run.sh` output), linked issue or TODO reference, and screenshots/terminal snippets for UX changes. Ensure docs (README, charter files) reflect behavioral shifts before requesting review.
