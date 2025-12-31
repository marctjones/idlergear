# Knowledge Types

IdlerGear manages 6 knowledge types (with 5 more planned for future releases).

## Implemented (v0.2.0)

### 1. Tasks
Things that need to be done. Have a lifecycle (open → closed). Can be prioritized and labeled.

```bash
idlergear task create "Fix parser bug"
idlergear task list
idlergear task show 1
idlergear task close 1
```

**Storage:** `.idlergear/tasks/`
**GitHub Backend:** Issues with "task" label

### 2. Notes
Quick capture - the post-it note. Unstructured, temporary. May become tasks, reference, or explorations later.

```bash
idlergear note create "Parser quirk with compound words"
idlergear note list
idlergear note promote 1 --to task
```

**Storage:** `.idlergear/notes/`
**GitHub Backend:** Issues with "note" label

### 3. Explorations
Open-ended questions being explored with context and reasoning. More thought-out than notes - meant to last and be understandable later.

```bash
idlergear explore create "Should we support Windows?"
idlergear explore list
idlergear explore show 1
idlergear explore close 1
```

**Storage:** `.idlergear/explorations/`
**GitHub Backend:** Issues with "explore" label

### 4. Vision
The "why" - purpose, mission, long-term direction. Protected, rarely changes. Guides decisions across the project.

```bash
idlergear vision show
idlergear vision edit
```

**Storage:** `.idlergear/vision.md`
**GitHub Backend:** VISION.md file in repository

### 5. Plans
How to achieve a specific goal. Groups related tasks, defines sequence. More tactical than vision, more structured than explorations.

```bash
idlergear plan create "auth-system" --title "Authentication System"
idlergear plan list
idlergear plan show auth-system
idlergear plan switch auth-system
```

**Storage:** `.idlergear/plans/`
**GitHub Backend:** GitHub Projects v2

### 6. References
Explanations of how things work - design decisions, technical docs, world knowledge. Persists long-term.

```bash
idlergear reference add "GGUF-Format" --body "..."
idlergear reference list
idlergear reference search "quantization"
```

**Storage:** `.idlergear/reference/`
**GitHub Backend:** GitHub Wiki pages

## Planned (Future)

### 7. Outputs
Results from executed processes. Logs, test results, script output.

```bash
idlergear run ./train.sh --name training
idlergear run status
idlergear run logs training --tail 50
```

### 8. Contexts
AI session state - conversation history, model configuration, system prompts.

```bash
idlergear context save "before-refactor"
idlergear context restore "before-refactor"
```

### 9. Configuration
Instance-specific settings. API keys, local paths.

```bash
idlergear config set github.token "..."
idlergear config get github.token
```

### 10. Resources
Files and data the project operates on - tracked with labels.

```bash
idlergear resource add ./assets/logo.png --label "approved-logo"
idlergear resource list --label "approved-logo"
```

### 11. Codebase
Source code, tests - everything managed by git.

```bash
idlergear code status
idlergear code changed
```

## Four Quadrants

Knowledge exists across two dimensions:

```
                VOLATILE                      PERSISTENT
          ┌─────────────────────────┬─────────────────────────┐
          │  LOCAL VOLATILE         │  LOCAL PERSISTENT       │
  LOCAL   │  • Contexts             │  • .idlergear/ storage  │
          │  • Live outputs         │  • Local config         │
          ├─────────────────────────┼─────────────────────────┤
          │  SHARED VOLATILE        │  SHARED PERSISTENT      │
  SHARED  │  • Multi-agent coord    │  • GitHub repo          │
          │  • Running process info │  • GitHub/Jira issues   │
          └─────────────────────────┴─────────────────────────┘
```
