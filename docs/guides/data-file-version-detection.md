# Data File Version Detection

IdlerGear can detect when your Python scripts reference old versions of data files, preventing bugs caused by using outdated datasets after AI assistants create improved versions.

## The Problem

During AI-assisted development, this common scenario causes bugs:

1. **AI creates an improved dataset**: `better_dataset.csv` or `data_v2.json`
2. **AI updates some scripts** to fix bugs or add features
3. **AI forgets to update file references** in other scripts
4. **Scripts still load old data**: `old_dataset.csv` or `data_v1.json`
5. **Tests pass with old data, production fails with new data**

## Solution: Automatic Detection

IdlerGear automatically:

1. **Detects versioned files** using patterns like `_old`, `_v2`, `_backup`
2. **Scans Python code** for file path references in:
   - `open()` calls
   - `pd.read_csv()`, `pd.read_json()`
   - `json.load()`, `yaml.load()`
   - Any function that takes file paths
3. **Identifies stale references** when scripts reference non-current versions
4. **Suggests updates** to use the current version instead

## Quick Start

Check for stale data file references:

```bash
idlergear watch versions
```

Output:

```
⚠️  analysis.py:15
    References stale: data/old_dataset.csv
    → Use instead: data/dataset.csv
    Function: read_csv

⚠️  process.py:42
    References stale: config_v1.json
    → Use instead: config.json
    Function: open

Summary: 2 stale file references detected
```

## Usage

### CLI Command

```bash
# Check for stale references
idlergear watch versions

# JSON output for AI agents
idlergear --output json watch versions
```

### MCP Tool

AI assistants can use the `idlergear_watch_versions` tool:

```json
{
  "name": "idlergear_watch_versions",
  "arguments": {}
}
```

Response:

```json
{
  "warnings_count": 2,
  "warnings": [
    {
      "source_file": "analysis.py",
      "line": 15,
      "stale_file": "data/old_dataset.csv",
      "current_file": "data/dataset.csv",
      "reference_path": "data/old_dataset.csv",
      "function": "read_csv",
      "base_name": "data/dataset.csv"
    }
  ]
}
```

### Integrated with `watch check`

The detection runs automatically with `idlergear watch check`:

```bash
idlergear watch check
```

Stale data file references appear in suggestions with category `data_version`.

## Version Patterns Detected

IdlerGear recognizes these version patterns:

| Pattern | Example | Detected As |
|---------|---------|-------------|
| `_v[0-9]+` | `data_v2.csv` | Version number |
| `_old` | `config_old.json` | Old version |
| `_new` | `handler_new.py` | New version |
| `_backup` | `dataset_backup.csv` | Backup |
| `.bak` | `data.csv.bak` | Backup |
| `_[YYYYMMDD]` | `log_20250119.txt` | Timestamp |
| `_copy` | `data_copy.json` | Copy |
| `_tmp`/`_temp` | `output_tmp.csv` | Temporary |
| `_draft` | `config_draft.yaml` | Draft |

## File Types Detected

Automatically detects references to:

- **Data formats**: CSV, JSON, JSONL, Parquet, Feather, Arrow
- **Config formats**: YAML, XML, TOML
- **Binary formats**: Pickle, HDF5, NPY, NPZ
- **Databases**: SQLite, SQL scripts
- **Text files**: TXT, TSV, DAT

## How Current Version is Determined

IdlerGear uses these heuristics (in order):

1. **No version suffix** = current (e.g., `data.csv` > `data_old.csv`)
2. **Highest version number** = current (e.g., `api_v3.py` > `api_v2.py`)
3. **`_new` suffix** = current (overrides base name)
4. **Most recent git commit** (if git history available)

## Configuration

Control behavior in `.idlergear/config.toml`:

```toml
[watch]
# Enable/disable data version checking
check_data_versions = true

# Custom version patterns (regex)
version_patterns = [
    "_v[0-9]+$",     # file_v2.py
    "_old$",         # file_old.py
    "_backup$",      # file_backup.py
]
```

## Examples

### Example 1: Pandas DataFrame

**Before (stale reference)**:

```python
import pandas as pd

def load_training_data():
    # AI created better_dataset.csv but forgot to update here
    df = pd.read_csv("data/old_dataset.csv")
    return df
```

**Detection**:

```
⚠️  train.py:5
    References stale: data/old_dataset.csv
    → Use instead: data/dataset.csv
    Function: read_csv
```

**After (fixed)**:

```python
import pandas as pd

def load_training_data():
    df = pd.read_csv("data/dataset.csv")  # Updated to current version
    return df
```

### Example 2: Configuration Files

**Before (stale reference)**:

```python
import json

with open("config_v1.json") as f:
    config = json.load(f)
```

**Detection**:

```
⚠️  main.py:3
    References stale: config_v1.json
    → Use instead: config.json
    Function: open
```

### Example 3: Multiple Stale References

**Before**:

```python
import pandas as pd
import yaml

# Load old input data
df = pd.read_csv("input_old.csv")

# Load old config
with open("settings_backup.yaml") as f:
    settings = yaml.safe_load(f)
```

**Detection**:

```
⚠️  process.py:5
    References stale: input_old.csv
    → Use instead: input.csv
    Function: read_csv

⚠️  process.py:9
    References stale: settings_backup.yaml
    → Use instead: settings.yaml
    Function: open

Summary: 2 stale file references detected
```

## Limitations

- **Python only**: Currently only scans Python files (`.py`)
- **Static analysis**: Can't detect dynamically constructed paths
- **Simple patterns**: Won't catch all versioning schemes
- **No runtime checks**: Detection is static, not runtime

## Future Enhancements

Potential improvements:

- **Multi-language support**: JavaScript, Rust, Go, etc.
- **Dynamic path detection**: Template strings, f-strings with variables
- **Auto-fix capability**: `idlergear watch versions --fix`
- **Git hooks**: Block commits with stale references
- **IDE integration**: Real-time warnings in editor

## Troubleshooting

### "No stale references found" but I know there are some

1. Check file actually has version suffix (e.g., `_old`, `_v2`)
2. Verify both versions exist in repository
3. Check script is using recognized function (`open`, `read_csv`, etc.)
4. Try `idlergear watch check` to see full analysis

### False positives

If a file is intentionally old but marked as stale:

1. Use `.idlergerignore` to exclude files
2. Or remove version suffix from filename
3. Or add metadata comment: `# idlergear:version=current`

### Performance issues on large repos

Scanning many Python files can be slow. Optimize:

```toml
[watch]
# Disable if too slow
check_data_versions = false
```

## Related

- [Watch Mode Overview](./watch-mode.md)
- [Knowledge Capture Guide](./knowledge-capture.md)
- [Git Integration](./git-integration.md)
