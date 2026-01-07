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

### Daemon Integration Tests

For testing multi-agent coordination features (daemon, queue, agents, locks):

```bash
# Run daemon integration tests
python -m pytest tests/test_daemon_integration.py -v

# Test specific scenario
python -m pytest tests/test_daemon_integration.py::test_multi_agent_coordination -v
```

**Test structure:**
- Use `pytest-asyncio` for async tests
- Create temporary storage with `temp_storage` fixture
- Test agent registry, command queue, and lock manager independently
- Verify full coordination scenarios work end-to-end

**What to test:**
- Agent registration, heartbeat, status updates
- Command queueing, priority ordering, assignment
- Lock acquisition, release, timeout
- Multi-agent coordination workflows
- Data persistence across restarts

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

## Version Management

**CRITICAL: Single Source of Truth**

IdlerGear uses `pyproject.toml` as the **single source of truth** for version numbers.

### Version Number Strategy

1. **Primary source**: `pyproject.toml` - This is the authoritative version
2. **All code reads from package metadata**: Use `importlib.metadata.version("idlergear")`
3. **Never hardcode versions** in Python files

### Implementation Pattern

```python
# ✅ CORRECT: Read from package metadata
try:
    from importlib.metadata import version as get_version
    __version__ = get_version("idlergear")
except Exception:
    # Fallback for development/editable installs
    __version__ = "0.3.1"  # Match pyproject.toml
```

```python
# ❌ WRONG: Hardcoded version
__version__ = "0.2.0"
```

### When to Update Version

1. **Update `pyproject.toml` only** - Change the `version = "X.Y.Z"` line
2. **All other files auto-sync** - They read from package metadata
3. **For templates**: Update fallback version to match current version

### Files Affected by Version Changes

- `pyproject.toml` - Primary source (update this)
- `src/idlergear/__init__.py` - Reads from metadata (auto-syncs)
- `src/idlergear/mcp_server.py` - Imports from `__init__.py` (auto-syncs)
- `src/idlergear/templates/python.py` - Template pattern (uses same strategy)

### Versioning Scheme

IdlerGear follows [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `0.3.1`)
- **MAJOR**: Breaking API changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Why This Matters

**Previous problem**: Version numbers were hardcoded in multiple files:
- `pyproject.toml`: 0.3.1
- `__init__.py`: 0.1.0
- `mcp_server.py`: 0.2.0

This caused confusion and incorrect version reporting.

**Current solution**: One version in `pyproject.toml`, all code reads from it.

### Releasing a New Version

```bash
# 1. Update version in pyproject.toml
vim pyproject.toml  # Change version = "0.3.2"

# 2. Verify all code sees the new version
pip install -e .
python -c "import idlergear; print(idlergear.__version__)"  # Should print 0.3.2
idlergear --version  # Should print 0.3.2

# 3. Commit and tag
git add pyproject.toml
git commit -m "chore: bump version to 0.3.2"
git tag v0.3.2
git push && git push --tags
```

## Security

- Never commit secrets, tokens, or passwords
- Use `.env` for sensitive data (in `.gitignore`)
- Use permissive licenses (MIT, Apache 2.0)
