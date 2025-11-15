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

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for complete development practices and workflow.

## Project Structure

- `src/` - Main source code
- `tests/` - Test suite
- `AI_INSTRUCTIONS/` - Instructions for AI coding assistants
- Charter documents: `VISION.md`, `DESIGN.md`, `TODO.md`, `IDEAS.md`

## Contributing

This project follows Test-Driven Development (TDD). All changes must include tests.
