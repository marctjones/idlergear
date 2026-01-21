---
id: 58
title: Fix version number inconsistencies across IdlerGear codebase
state: closed
created: '2026-01-07T06:12:15.824785Z'
labels:
- bug
- quality
priority: medium
---
## Problem

There are **three different version numbers** currently in the codebase:

1. **pyproject.toml**: `0.3.1`
2. **CLI (`idlergear --version`)**: `0.3.0`
3. **MCP server (`idlergear_version()`)**: `0.2.0`
4. **`__init__.py`**: `0.1.0`

This creates confusion when debugging issues, checking compatibility, and installing the package.

## Root Cause

Version is defined in multiple places without a single source of truth:
- `pyproject.toml` - Package metadata
- `src/idlergear/__init__.py` - Python module version
- MCP server may be reading from a different location

## Expected Behavior

**Single source of truth**: All version queries should return the same value.

## Proposed Solution

1. **Use `pyproject.toml` as the single source of truth**
2. **Update `__init__.py`** to read version from `pyproject.toml` dynamically:
   ```python
   from importlib.metadata import version
   __version__ = version("idlergear")
   ```
3. **Update MCP server** to use the same method
4. **Verify** `idlergear --version` reads from the correct source

## Testing

```bash
# Should all return the same version
idlergear --version                    # CLI
python -c "import idlergear; print(idlergear.__version__)"  # Module
idlergear-mcp # call idlergear_version tool  # MCP
pip show idlergear | grep Version     # Package
```

## Current State (2026-01-07)

- **pyproject.toml**: 0.3.1
- **Editable install** at `/home/marc/Projects/idlergear`
- **pipx install** also present at `/home/marc/.local/share/pipx/venvs/idlergear/`

## Priority

**Medium** - Causes confusion but not blocking functionality
