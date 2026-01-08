"""Python project template."""

# Python-specific .gitignore additions
GITIGNORE_PYTHON = """\
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv/

# Testing
.tox/
.nox/
.coverage
.coverage.*
htmlcov/
.pytest_cache/
.hypothesis/

# Type checking
.mypy_cache/
.dmypy.json
dmypy.json

# Jupyter
.ipynb_checkpoints/

# pyenv
.python-version
"""

# pyproject.toml template
PYPROJECT_TOML = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{package_name}"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.black]
line-length = 88
target-version = ["py310"]

[tool.ruff]
line-length = 88
target-version = "py310"
"""

# README.md template
README_MD = """\
# {project_name}

{description}

## Development

The virtual environment is automatically activated when using Claude Code.

For manual development:
```bash
source venv/bin/activate  # or `venv\\Scripts\\activate` on Windows
pip install -e ".[dev]"
pytest
```

## Project Management

This project uses [IdlerGear](https://github.com/marctjones/idlergear) for knowledge management.

```bash
idlergear vision show    # View project vision
idlergear task list      # List open tasks
idlergear plan show      # View current plan
```
"""

# src/__init__.py template
SRC_INIT = '''\
"""{project_name}."""

try:
    from importlib.metadata import version as get_version
    __version__ = get_version("{package_name}")
except Exception:
    # Fallback for development/editable installs
    __version__ = "0.1.0"
'''

# tests/__init__.py
TESTS_INIT = '"""Tests for {project_name}."""\n'

# tests/test_placeholder.py
TEST_PLACEHOLDER = """\
\"\"\"Placeholder test.\"\"\"


def test_placeholder():
    \"\"\"Placeholder test to verify pytest works.\"\"\"
    assert True
"""

# .claude/rules/ig_python.md - Python-specific rules
CLAUDE_RULES_PYTHON = """\
---
description: Python development conventions
paths: "**/*.py"
---

# Python Development Rules

## Code Style

- Follow PEP 8 conventions
- Use type hints for function signatures
- Maximum line length: 88 characters (Black default)
- Use docstrings for modules, classes, and functions

## Testing

- Write tests in `tests/` directory
- Use pytest for testing
- Run tests with `pytest` before committing

## Virtual Environment

The venv is automatically activated for this session. Python commands use the venv.
"""

# Python-specific Claude settings (merged with base settings)
CLAUDE_SETTINGS_PYTHON = {
    "env": {
        # Set PATH to include venv/bin first
        "PATH": "./venv/bin:${env:PATH}",
        # Set VIRTUAL_ENV for tools that check it
        "VIRTUAL_ENV": "./venv",
    },
}

# SessionStart hook script to activate venv
VENV_ACTIVATE_HOOK = """\
#!/bin/bash
# Activate Python venv for Claude Code session

if [ -d "./venv" ]; then
    # Export venv activation to Claude's environment file
    if [ -n "$CLAUDE_ENV_FILE" ]; then
        echo 'export PATH="./venv/bin:$PATH"' >> "$CLAUDE_ENV_FILE"
        echo 'export VIRTUAL_ENV="./venv"' >> "$CLAUDE_ENV_FILE"
    fi
fi
exit 0
"""
