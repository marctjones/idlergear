# idlergear
### Usage

```bash
# Create a new project in the current directory
idlergear new my-awesome-project

# Create a new project in a specific location
idlergear new my-awesome-project --path ~/projects

# Create a project with a specific language
idlergear new my-go-app --lang go --path ~/projects
```

### Features

- Automatically creates a private GitHub repository from a template
- Sets up project charter documents (VISION.md, TODO.md, IDEAS.md, etc.)
- Configures language-specific `.gitignore`
- Initializes with proper development practices and AI instructions
- Warns if creating inside the idlergear repository itself

### Claude ↔ Codex Handshake

Use the built-in messaging plus sync commands to trade updates between a local OpenAI Codex session and Claude Code Web:

1. **Codex/local:** `idlergear message send --to web --body "Ping from Codex" --from codex`
2. **Codex/local:** `idlergear sync push --include-untracked` (note the sync branch name in the output)
3. **Claude Web:** `git fetch && git checkout <sync-branch>` then `idlergear message list --filter-to web`
4. **Claude Web response:** `idlergear message respond --id <message-id> --body "Reply from Claude" --from claude` followed by `idlergear sync push --include-untracked`
5. **Codex/local receive:** `idlergear sync pull` then `idlergear message list --filter-from claude`

This mirrors the roadmap workflow: Codex pushes a sync branch with messages, Claude reads/responds on that branch, then Codex pulls the response back.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for complete development practices and workflow.

## Project Structure

- `src/` - Main source code
- `tests/` - Test suite
- `AI_INSTRUCTIONS/` - Instructions for AI coding assistants
- Charter documents: `VISION.md`, `DESIGN.md`, `TODO.md`, `IDEAS.md`

## Contributing

This project follows Test-Driven Development (TDD). All changes must include tests.
