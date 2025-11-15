# GitHub Copilot CLI Instructions

## Your Role

You are assisting with this project. Your job is to **follow the established practices**, not create new ones.

## Step 1: Read the Universal Development Practices

**Before doing anything else, read `DEVELOPMENT.md`** - it contains all the standard practices that apply to every contributor (human or AI).

## Step 2: Understand Copilot CLI Capabilities

As the GitHub Copilot CLI, you have these capabilities:
- Execute shell commands via `bash` tool
- Read and edit files
- Search codebases with `grep` and `glob`
- Access GitHub API for repository operations

## Step 3: Follow the Workflow

When you start a session:
1. ✅ Check if isolated environment exists and is activated
2. ✅ Read charter documents (VISION.md, DESIGN.md, TODO.md, IDEAS.md)
3. ✅ Run existing tests to establish baseline
4. ✅ Make changes following TDD principles
5. ✅ Run tests after changes
6. ✅ Commit with meaningful messages

## Copilot-Specific Tips

- Use parallel tool calling when possible (read multiple files at once)
- Chain bash commands with `&&` for efficiency
- Always activate the isolated environment before running code
- Use `--no-pager` with git commands to avoid interactive prompts

## Key Reminders

- The project's charter documents (VISION, DESIGN, TODO, IDEAS) are the **single source of truth**
- Never deviate from established architecture without explicit confirmation
- Follow the language-specific best practices outlined in DEVELOPMENT.md
- Test everything before reporting completion

---

**Remember:** You're here to execute the plan, not design a new one. When in doubt, ask for clarification.

