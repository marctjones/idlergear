# GitHub Copilot CLI Instructions

## Critical First Steps

**Before doing ANY code development or dependency installation, you MUST:**

1. **Read the Project Charter Documents** in this exact order:
   - `VISION.md` - Understand the project's core mission and goals
   - `DESIGN.md` - Understand technical architecture and implementation phases
   - `TODO.md` - See current tasks and what needs to be done
   - `IDEAS.md` - Understand what is out-of-scope

2. **Verify or Create Isolated Development Environment:**
   - **Python:** Check for `venv/` directory. If missing, run `python -m venv venv`
   - **Node.js:** Check for `node_modules/` and `package.json`. If missing, run `npm init` or `yarn init`
   - **Rust:** Verify `Cargo.toml` exists
   - **Go:** Verify `go.mod` exists
   - **Always activate the environment BEFORE installing dependencies or running code**
   - For Python: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)

3. **Install Dependencies in Isolated Environment:**
   - Never install globally
   - Use the project's requirements/package files
   - Python: `pip install -r requirements.txt`
   - Node.js: `npm install` or `yarn install`

## Core Workflow

1. **Always work within the activated isolated environment**
2. **Follow Test-Driven Development (TDD):**
   - Write tests before implementation
   - Run existing tests to establish baseline
   - Run tests after changes to verify nothing broke
3. **Use version control properly:**
   - Make small, frequent commits
   - Work in feature branches
   - Never commit secrets or sensitive data
4. **Follow language-specific best practices:**
   - Python: Use `black`, `ruff`, `pytest`
   - Check the project for existing linters/formatters and use them

## Project Context Requirements

These charter documents are the **single source of truth**. You must:
- Ground all actions and responses in the project's established context
- Never deviate from the plans, principles, or architecture without explicit confirmation
- Your primary function is to execute the plan laid out in these documents

## Development Principles to Follow

- **Isolated Development Environments:** ALWAYS use language-specific isolated environments
- **Iterative & TDD:** Write tests for every feature
- **Git Workflow:** Feature branches, frequent commits
- **Working Demos:** Create working demos before combining features
- **Language Best Practices:** Follow established conventions
- **Dependency & Licensing:** Prefer permissive licenses (MIT, Apache 2.0)
- **Guard Against Scope Creep:** Stay focused on the defined goals

## What This Means for You

1. When you join a project, FIRST verify the isolated environment is set up and activated
2. THEN read the charter documents to understand context
3. THEN check what tests exist and run them
4. ONLY THEN start making changes
5. Test your changes before reporting completion

## Checklist for Every Session

- [ ] Isolated environment verified/created and activated
- [ ] Charter documents read (VISION, DESIGN, TODO, IDEAS)
- [ ] Existing tests run to establish baseline
- [ ] Changes made following TDD principles
- [ ] Tests pass after changes
- [ ] Changes committed with meaningful messages

---

**Remember:** The goal is to be a helpful assistant that follows the established project practices, not to impose new patterns or skip existing workflows.
