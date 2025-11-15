# Development Setup and Workflow

This document describes the standard development practices for this project. **All contributors (human and AI assistants) must follow these practices.**

## Initial Setup

### 1. Clone and Enter the Project
```bash
git clone <repository-url>
cd <project-name>
```

### 2. Set Up Isolated Development Environment

**Python:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

**Node.js:**
```bash
npm install
# or
yarn install
```

**Rust:**
```bash
cargo build
```

**Go:**
```bash
go mod download
```

### 3. Read Project Context

Before making any changes, read these files in order:
1. **`VISION.md`** - Project goals and mission
2. **`DESIGN.md`** - Technical architecture and phases
3. **`TODO.md`** - Current tasks
4. **`IDEAS.md`** - Out-of-scope items

## Daily Development Workflow

### Before Every Work Session
1. ✅ Activate isolated environment
2. ✅ Pull latest changes: `git pull`
3. ✅ Review relevant charter documents
4. ✅ Run existing tests to establish baseline

### During Development
1. ✅ Follow Test-Driven Development (TDD)
   - Write tests first
   - Implement code to pass tests
   - Refactor while keeping tests green
2. ✅ Make small, focused commits
3. ✅ Keep charter documents updated as you work

### Before Committing
1. ✅ Run all tests: `./run.sh` (or language-specific test command)
2. ✅ Run linter/formatter (e.g., `black`, `ruff`, `eslint`)
3. ✅ Verify no secrets or sensitive data in changes
4. ✅ Write meaningful commit messages

## Testing Requirements

- Every feature must have tests
- Aim for high code coverage (>80%)
- Tests should be fast and deterministic
- Use the project's `./run.sh` script when available

## Git Workflow

- Work in feature branches: `git checkout -b feature/my-feature`
- Commit frequently with clear messages
- Create Pull Requests for review
- Merge only after tests pass

## Language-Specific Best Practices

**Python:**
- Use `black` for formatting
- Use `ruff` for linting
- Use `pytest` for testing
- Follow PEP 8

**Node.js:**
- Use `prettier` for formatting
- Use `eslint` for linting
- Use `jest` or `mocha` for testing

**Rust:**
- Use `rustfmt` for formatting
- Use `clippy` for linting
- Use built-in test framework

## Security

- **Never** commit secrets, tokens, or passwords
- Use environment variables for sensitive data (`.env` files)
- Ensure `.env` is in `.gitignore`
- Use permissive licenses (MIT, Apache 2.0) for dependencies
- Get approval before using copyleft licenses (GPL, etc.)

## Documentation

- Update README.md when adding major features
- Update TODO.md as tasks are completed
- Add out-of-scope ideas to IDEAS.md
- Keep VISION.md and DESIGN.md as single source of truth

---

**For AI Assistants:** See `AI_INSTRUCTIONS/<tool-name>.md` for tool-specific guidance on following these practices.
