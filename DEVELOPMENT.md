# Development Setup and Workflow

This document describes the standard development practices for this project.

## Initial Setup

```bash
git clone https://github.com/marctjones/idlergear.git
cd idlergear
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## Development Workflow

### Before Every Session
1. Activate environment: `source venv/bin/activate`
2. Pull latest: `git pull`
3. Read VISION.md for context

### During Development
1. Follow Test-Driven Development (TDD)
   - Write tests first
   - Implement code to pass tests
   - Refactor while keeping tests green
2. Make small, focused commits

### Before Committing
1. Run tests: `./run.sh`
2. Run formatter/linter: `black src/` and `ruff check src/`
3. Verify no secrets in changes

## Testing

- Every feature must have tests
- Use pytest: `python -m pytest`
- Aim for >80% coverage

## Adding Dependencies

Before adding any dependency:
1. Research at least 3 alternatives
2. Check: maintenance, adoption, security, license
3. Document reasoning in commit message

**Red flags:**
- Last updated >1 year ago
- <100 GitHub stars for critical functionality
- No documentation
- Copyleft license (GPL/AGPL) without approval

## Git Workflow

- Work in feature branches: `git checkout -b feature/my-feature`
- Commit frequently with clear messages
- Create Pull Requests for review
- Merge only after tests pass

## Python Practices

- Formatter: `black`
- Linter: `ruff`
- Tests: `pytest`
- Follow PEP 8

## Security

- Never commit secrets, tokens, or passwords
- Use `.env` for sensitive data (in `.gitignore`)
- Use permissive licenses (MIT, Apache 2.0)
