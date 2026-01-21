# File Registry Workflow Examples

This document provides real-world scenarios and step-by-step workflows for using the IdlerGear file registry.

## Table of Contents

1. [Data Science: Dataset Evolution](#data-science-dataset-evolution)
2. [Web Development: API Refactoring](#web-development-api-refactoring)
3. [Machine Learning: Model Versioning](#machine-learning-model-versioning)
4. [Team Collaboration: Multi-Agent Workflow](#team-collaboration-multi-agent-workflow)
5. [Research Project: Experiment Archiving](#research-project-experiment-archiving)
6. [Code Migration: Legacy System Deprecation](#code-migration-legacy-system-deprecation)

---

## Data Science: Dataset Evolution

### Scenario

You're a data scientist improving a training dataset. The original dataset has quality issues: missing labels, duplicates, and validation errors. You create an improved version and want to ensure all AI assistants (and teammates) use the new version.

### Initial State

```
data/
├── training_data.csv  (original, has issues)
└── scripts/
    └── train_model.py  (uses training_data.csv)
```

### Workflow

```bash
# Step 1: Back up original dataset
cp data/training_data.csv data/training_data_v1.csv

# Step 2: Create improved dataset
python scripts/clean_data.py  # outputs cleaned_training_data.csv

# Step 3: Replace original
mv data/cleaned_training_data.csv data/training_data.csv

# Step 4: Deprecate old version
idlergear file deprecate data/training_data_v1.csv \
  --successor data/training_data.csv \
  --reason "Fixed: missing labels (120 rows), removed duplicates (45 rows), added validation"

# Step 5: Annotate new version for discovery
idlergear file annotate data/training_data.csv \
  --description "Training dataset v2: 10K samples, validated labels, no nulls, balanced classes" \
  --tags data,training,ml,cleaned \
  --components ModelTrainer,DataLoader

# Step 6: Update documentation
echo "Dataset v2: Cleaned and validated (Jan 2026)" >> data/CHANGELOG.md
```

### Result

- ✅ AI assistants will always use `training_data.csv`
- ✅ If an AI tries to read `training_data_v1.csv`, they get a warning with the successor
- ✅ Future AI agents can search `idlergear file search --tags training` to find the right dataset
- ✅ The reason for deprecation is preserved for future reference

### After 2 Weeks (Cleanup)

```bash
# Remove old dataset after grace period
rm data/training_data_v1.csv
idlergear file unregister data/training_data_v1.csv
```

---

## Web Development: API Refactoring

### Scenario

You're refactoring a synchronous Flask API to an async FastAPI implementation. The old API needs to remain for a transition period, but new development should use the new async version.

### Initial State

```
src/
├── api/
│   └── app.py  (Flask, synchronous)
└── models/
    └── user.py
```

### Workflow

```bash
# Step 1: Rename old API
git mv src/api/app.py src/api/app_sync.py

# Step 2: Create new async API
# ... write new FastAPI app.py ...

# Step 3: Deprecate old synchronous version
idlergear file deprecate src/api/app_sync.py \
  --successor src/api/app.py \
  --reason "Migrating to FastAPI for async support and better performance. Old sync version kept for transition period (remove after 2026-02-01)."

# Step 4: Annotate new API
idlergear file annotate src/api/app.py \
  --description "FastAPI async REST API: user endpoints, authentication, rate limiting" \
  --tags api,fastapi,async,rest \
  --components UserAPI,AuthMiddleware,RateLimiter \
  --related src/models/user.py,src/auth/jwt.py

# Step 5: Mark old API as archived (not deprecated) to allow reference
idlergear file register src/api/app_sync.py \
  --status archived \
  --reason "Historical reference only. Use src/api/app.py for new work."

# Step 6: Create migration task
idlergear task create "Remove app_sync.py after 2026-02-01" \
  --due 2026-02-01 \
  --label migration
```

### Result

- ✅ New AI agents will use async `app.py`
- ✅ Old `app_sync.py` remains for reference but marked as archived
- ✅ Clear migration timeline with task reminder
- ✅ Related files documented for context

### After Migration Period

```bash
# Remove old synchronous API
rm src/api/app_sync.py
idlergear file unregister src/api/app_sync.py
idlergear task close <task_id>  # Close migration task
```

---

## Machine Learning: Model Versioning

### Scenario

You're training ML models iteratively. Each experiment produces artifacts: model weights, config files, and evaluation results. You want to track which versions are current vs experimental.

### Initial State

```
models/
├── model_v1.pth
├── config_v1.yaml
└── eval_v1.json
```

### Workflow: Experiment Tracking

```bash
# Experiment 1: Baseline model
idlergear file annotate models/model_v1.pth \
  --description "Baseline CNN: 85% accuracy, 3 conv layers" \
  --tags model,baseline,cnn \
  --components CNNModel \
  --related models/config_v1.yaml,models/eval_v1.json

# Experiment 2: Improved model
python train.py --layers 5 --lr 0.001  # outputs model_v2.pth

idlergear file annotate models/model_v2.pth \
  --description "Improved CNN: 89% accuracy, 5 conv layers, better regularization" \
  --tags model,improved,cnn \
  --components CNNModel

# Mark v1 as deprecated
idlergear file deprecate models/model_v1.pth \
  --successor models/model_v2.pth \
  --reason "Improved accuracy from 85% to 89% with deeper architecture"

# Experiment 3: Transformer (failed)
python train_transformer.py  # outputs model_v3_transformer.pth
# ... results are worse (82% accuracy) ...

idlergear file register models/model_v3_transformer.pth \
  --status problematic \
  --reason "Experiment failed: 82% accuracy (worse than baseline). Transformer may need more data."

# Experiment 4: Final production model
python train.py --layers 5 --lr 0.0005 --augment  # outputs model_v4.pth

idlergear file annotate models/model_v4.pth \
  --description "Production CNN: 91% accuracy, 5 conv layers, data augmentation, ready for deployment" \
  --tags model,production,cnn,deployed \
  --components CNNModel

idlergear file deprecate models/model_v2.pth \
  --successor models/model_v4.pth \
  --reason "Production model: 91% accuracy with data augmentation"
```

### Cleanup: Archive Old Experiments

```bash
# After model is deployed, archive experimental versions
mkdir -p models/archive
mv models/model_v1.pth models/model_v2.pth models/model_v3_transformer.pth models/archive/

for file in models/archive/*.pth; do
  idlergear file register "$file" \
    --status archived \
    --reason "Historical experiment, not for production"
done
```

### Result

- ✅ Clear model evolution history
- ✅ Failed experiments marked as problematic with reasons
- ✅ Current production model clearly identified
- ✅ AI assistants know which model to deploy

---

## Team Collaboration: Multi-Agent Workflow

### Scenario

Multiple AI agents (Claude Code, Aider, Cursor) are working on the project simultaneously. One agent creates a new database schema, and all agents need to update their code to use it.

### Setup

```bash
# Terminal 1: Start daemon for multi-agent coordination
idlergear daemon start

# Terminal 2: Claude Code (auto-registers as agent)
# Terminal 3: Aider (auto-registers as agent)
# Terminal 4: Cursor (auto-registers as agent)
```

### Workflow

**Agent 1 (Claude Code): Creates New Schema**

```bash
# Create new schema with better indexing
python generate_schema.py  # outputs schema_v2.sql

idlergear file deprecate db/schema.sql \
  --successor db/schema_v2.sql \
  --reason "Added indexes on user_id and created_at for query performance"

idlergear file annotate db/schema_v2.sql \
  --description "Database schema v2: improved indexing for user queries" \
  --tags database,schema,postgresql \
  --components UserTable,PostTable

# Broadcast to all agents
idlergear daemon send "📢 Database schema updated: db/schema_v2.sql (added indexes)"
```

**Agent 2 (Aider): Receives Notification**

```bash
# Aider automatically receives:
# 📢 Message from Claude Code:
#    Database schema updated: db/schema_v2.sql (added indexes)

# Aider checks the new schema
idlergear file status db/schema_v2.sql
# Output: current

# Aider reads annotation
idlergear file search --query "database schema"
# Returns: db/schema_v2.sql with description

# Aider updates migration script
# ... edits migrations/001_add_indexes.sql ...
```

**Agent 3 (Cursor): Auto-Receives Registry Update**

```bash
# Cursor automatically notified via daemon:
# 📢 File Registry Update:
#    db/schema.sql has been deprecated
#    → Use db/schema_v2.sql instead
#    Reason: Added indexes on user_id and created_at

# Cursor updates ORM models
# ... edits src/models/*.py to match new schema ...
```

### Result

- ✅ All agents immediately aware of schema change
- ✅ No agent uses old schema
- ✅ Coordinated updates across the team
- ✅ Clear communication via daemon

---

## Research Project: Experiment Archiving

### Scenario

You're finishing a research project with dozens of experiment scripts. Most didn't work. You want to archive them but keep the successful ones accessible.

### Initial State

```
experiments/
├── baseline_v1.py
├── baseline_v2.py
├── experiment_attention.py
├── experiment_lstm.py
├── experiment_transformer.py
├── experiment_hybrid_01.py
├── experiment_hybrid_02.py
└── final_model.py  (this one worked!)
```

### Workflow

```bash
# Step 1: Annotate successful experiment
idlergear file annotate experiments/final_model.py \
  --description "Final successful model: hybrid attention+LSTM, 94% accuracy" \
  --tags model,success,production \
  --components HybridModel

# Step 2: Move failed experiments to archive
mkdir -p experiments/archive
mv experiments/baseline_*.py experiments/archive/
mv experiments/experiment_*.py experiments/archive/

# Step 3: Bulk-register as archived
for file in experiments/archive/*.py; do
  idlergear file register "$file" \
    --status archived \
    --reason "Failed experiment, kept for reference only"
done

# Step 4: Add notes about why they failed
idlergear note create "Experiment notes:
- baseline_v1/v2: Too simple, 72% accuracy
- attention: Overfitting, 68% validation accuracy
- lstm: Better (85%) but slower than final model
- transformer: Good (89%) but computationally expensive
- hybrid_01: Promising (90%), improved in hybrid_02
- hybrid_02: Some improvement (91%), finalized in final_model
- final_model: Best balance of accuracy (94%) and speed
" --tag research

# Step 5: Create final documentation
idlergear reference add "Research Project Final Results" \
  --body "Final model (experiments/final_model.py) achieved 94% accuracy using hybrid attention+LSTM architecture. See .idlergear/notes/ for experiment log."
```

### Result

- ✅ Clear distinction between successful and failed experiments
- ✅ Failed experiments archived but accessible for reference
- ✅ AI assistants won't mistakenly use failed approaches
- ✅ Research notes captured for future reference

---

## Code Migration: Legacy System Deprecation

### Scenario

You're migrating from a legacy Python 2 codebase to Python 3. The old code needs to remain during the migration, but new development should only touch Python 3 files.

### Initial State

```
src/
├── legacy/  (Python 2)
│   ├── core.py
│   ├── utils.py
│   └── api.py
└── modern/  (Python 3)
    ├── core.py
    ├── utils.py
    └── api.py
```

### Workflow

```bash
# Step 1: Mark entire legacy directory as deprecated
for file in src/legacy/*.py; do
  # Find corresponding modern file
  modern_file="src/modern/$(basename $file)"

  idlergear file deprecate "$file" \
    --successor "$modern_file" \
    --reason "Legacy Python 2 code. Migration to Python 3 complete. Use modern/ instead."
done

# Step 2: Annotate modern files
idlergear file annotate src/modern/core.py \
  --description "Core application logic (Python 3): business rules, validation" \
  --tags python3,core,production \
  --components CoreService,Validator

idlergear file annotate src/modern/utils.py \
  --description "Utility functions (Python 3): helpers, formatters" \
  --tags python3,utils \
  --components DateUtils,StringUtils

idlergear file annotate src/modern/api.py \
  --description "REST API (Python 3): FastAPI endpoints" \
  --tags python3,api,fastapi \
  --components UserAPI,ProductAPI

# Step 3: Create migration tracking task
idlergear task create "Remove Python 2 legacy code after migration validation" \
  --label migration \
  --due 2026-03-01

# Step 4: Add migration documentation
idlergear reference add "Python 2 to Python 3 Migration" \
  --body "Migration completed Jan 2026. All new code in src/modern/.
  Legacy Python 2 code in src/legacy/ deprecated, will be removed March 2026 after validation period.

  Key changes:
  - Print statements → print()
  - dict.iteritems() → dict.items()
  - xrange → range
  - Unicode handling improved
  "
```

### Result

- ✅ AI assistants will only edit Python 3 code
- ✅ Legacy code preserved during validation
- ✅ Clear migration timeline
- ✅ Documentation for why migration happened

### After Validation (March 2026)

```bash
# Remove legacy code
rm -rf src/legacy/
idlergear file unregister src/legacy/*.py
idlergear task close <migration_task_id>
```

---

## Best Practices Summary

### 1. Always Provide Successors

❌ Bad:
```bash
idlergear file deprecate old_file.py
```

✅ Good:
```bash
idlergear file deprecate old_file.py --successor new_file.py --reason "Refactored for async support"
```

### 2. Use Status Appropriately

| Use Case | Status |
|----------|--------|
| Current active file | `current` |
| Old version with replacement | `deprecated` |
| Historical reference only | `archived` |
| Known bugs/issues | `problematic` |

### 3. Annotate For Discovery

Always annotate files with:
- **Description**: What it does (1-2 sentences)
- **Tags**: Searchable keywords (3-5 tags)
- **Components**: Key classes/functions
- **Related files**: Dependencies or related code

### 4. Clean Up Eventually

- Set reminder tasks for cleanup
- Remove deprecated files after grace period (2-4 weeks typical)
- Unregister deleted files to keep registry clean

### 5. Use Daemon for Team Collaboration

When multiple agents/developers work together:
```bash
idlergear daemon start
```
All registry updates broadcast automatically.

---

## See Also

- [File Registry User Guide](../guides/file-registry.md)
- [MCP Tools Reference](../../src/idlergear/skills/idlergear/references/mcp-tools.md)
- [Multi-Agent Coordination](../guides/daemon.md)
