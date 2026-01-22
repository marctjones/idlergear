# IdlerGear v0.6.0 - Features Status & Setup Guide

## ✅ What Works AUTOMATICALLY (Zero Setup)

### File Registry (v0.6.0) ✅ AUTOMATIC

**Status:** ✅ Fully functional, automatic MCP interception enabled

**What happens automatically:**
- When you use `idlergear file deprecate`, files are immediately registered
- AI assistants using IdlerGear MCP tools get **automatic protection**
- Reads to deprecated files are **blocked automatically**
- Access attempts are **logged automatically** to `.idlergear/access_log.jsonl`

**How to verify it's working:**

```bash
# 1. Create test files
echo "old code" > old_api.py
echo "new code" > new_api.py

# 2. Deprecate the old file
idlergear file deprecate old_api.py --successor new_api.py

# 3. Try to read via MCP (in Python or via AI assistant)
# This will be BLOCKED automatically
python3 << 'EOF'
from idlergear.mcp_server import _check_file_access
allowed, warning = _check_file_access("old_api.py", "read")
print(f"Allowed: {allowed}")
print(f"Warning: {warning}")
EOF

# 4. Check access log
cat .idlergear/access_log.jsonl | jq .
```

**Expected output:**
```
Allowed: False
Warning: ⚠️  old_api.py is deprecated. Use new_api.py instead.
```

**When AI assistants use it:**
- Any MCP tool that reads files (`idlergear_fs_read_file`, etc.) is intercepted
- AI gets clear error message: "⚠️ old_api.py is deprecated. Use new_api.py instead."
- AI is **forced** to use the new file
- You see activity in `.idlergear/access_log.jsonl`

### File Annotations (v0.6.0) ✅ AUTOMATIC (after manual annotation)

**Status:** ✅ Fully functional, search works automatically

**What happens automatically:**
- After you annotate a file once, search is instant (200 tokens vs 15,000)
- AI can use `idlergear_file_search` instead of grep
- Results are cached and fast

**How to verify:**

```bash
# 1. Annotate a file
idlergear file annotate src/api/auth.py \
  --description "REST API authentication endpoints" \
  --tags api,auth,jwt

# 2. Search (fast, low tokens)
idlergear file search --query "authentication"
idlergear file search --tags auth

# 3. AI assistants can now use:
# idlergear_file_search(query="auth") → 200 tokens
# vs grep + read 10 files → 15,000 tokens
```

**What you'll see different:**
- AI finds files **instantly** without grepping
- Token usage drops by **93%** for file discovery
- Search results include descriptions, tags, components

### Multi-Agent Coordination (v0.6.0) ✅ AUTOMATIC (if daemon running)

**Status:** ✅ Works automatically when daemon is running

**What happens automatically:**
- When one agent deprecates a file, all agents are notified within 1 second
- Agents invalidate their cache automatically
- No manual sync needed

**How to verify:**

```bash
# Terminal 1: Start daemon
idlergear daemon start

# Terminal 2: Deprecate a file
idlergear file deprecate test.py --successor test_v2.py

# All connected agents receive broadcast notification
# Check daemon logs
cat ~/.idlergear/daemon.log
```

**What you'll see different:**
- Multiple AI assistants stay in sync
- One agent's changes visible to all others immediately
- Daemon log shows broadcast events

---

## ⚙️ What Requires MANUAL SETUP (Opt-In)

### Knowledge Graph 📊 MANUAL SETUP REQUIRED

**Status:** ✅ Implemented, ❌ Not enabled by default

**Why not automatic:** Requires initial indexing (can take time on large repos)

**How to enable:**

```bash
# 1. Populate graph with git history
idlergear_graph_populate_git()

# 2. Populate graph with code symbols
idlergear_graph_populate_code()

# 3. Verify schema
idlergear_graph_schema_info()
```

**MCP Tools available (after setup):**
- `idlergear_graph_query_task` - Get task context (95% token savings)
- `idlergear_graph_query_file` - Get file relationships
- `idlergear_graph_query_symbols` - Find functions/classes fast
- `idlergear_graph_populate_git` - Index git history
- `idlergear_graph_populate_code` - Index Python code

**What you'll see different (after setup):**
- AI can find related files without grep: "What files import auth.py?"
- Symbol search is instant: "Find all functions named handle_*"
- Task context includes related commits and files automatically
- **95-98% token savings** on context queries

**Why use it:**
- Token-efficient context retrieval
- Understand code relationships without reading every file
- AI can answer "what changed?" queries instantly

### Mem0 Plugin 🧠 MANUAL SETUP REQUIRED

**Status:** ✅ Implemented, ⚙️ Requires local server OR API key

**Why not automatic:** Requires running Mem0 server (local or cloud)

**⚠️ RESOURCE WARNING:** Mem0 local deployment may be resource-intensive (requires LLM + vector database). Actual CPU/memory requirements are not well documented. Consider **cloud deployment** or use **Knowledge Graph** instead for local token savings.

**Option 1: Local Deployment ⚠️**

**No API key needed! Runs 100% locally. (But may be heavy on resources)**

```bash
# 1. Install Mem0
pip install mem0ai

# 2. Run local Mem0 server (check Mem0 docs for setup)
# https://github.com/mem0ai/mem0
mem0 serve --port 8000  # Or use Docker

# 3. Configure IdlerGear to use local Mem0
cat >> .idlergear/config.toml << 'EOF'

[plugins.mem0]
enabled = true
host = "http://localhost:8000"
# No API key needed for local! ✅
EOF

# 4. Mem0 automatically learns from your IdlerGear usage
```

**Option 2: Cloud API (Recommended for Mem0) ✅**

```bash
# Recommended: Offloads resource usage to Mem0's cloud infrastructure
# 1. Get API key from https://app.mem0.ai

# 2. Add to config.toml
cat >> .idlergear/config.toml << 'EOF'

[plugins.mem0]
enabled = true
api_key = "m0-your-key-here"
EOF
```

**What it does (when enabled):**
- Learns patterns from your tasks and decisions
- Provides smart suggestions based on history
- 90% token savings on session context
- Remembers team patterns and best practices

**What you'll see different:**
- AI gets suggestions based on past patterns
- "You usually create tests after adding API endpoints"
- Context includes learned patterns, not just current session

**Why use it:**
- Learn from past sessions
- Get smarter suggestions over time
- Share team knowledge automatically

**💡 Local Alternative:** If you want token savings without running extra services, use **Knowledge Graph** instead (see above). It provides 95-98% token savings with just an embedded database (~50-100MB), no separate server needed.

### LlamaIndex Plugin 🔍 MANUAL SETUP REQUIRED

**Status:** ✅ Implemented, ❌ Requires config and indexing

**Why not automatic:** Requires indexing step

**How to enable:**

```bash
# Add to config.toml
[plugins.llamaindex]
enabled = true

# Index your docs (manual step)
idlergear plugin index llamaindex
```

**What it does:**
- Vector search over documentation
- Semantic search for relevant context
- RAG-based context retrieval

---

## 🎯 What AI Assistants Use AUTOMATICALLY

### Claude Code (via MCP)
**Automatic features:**
- ✅ File registry interception (deprecation protection)
- ✅ File annotations search (if files are annotated)
- ✅ Multi-agent coordination (if daemon running)
- ❌ Knowledge graph (requires manual population)
- ❌ Mem0 (requires API key)

### Other AI Assistants (Aider, Goose, etc.)
**Automatic features:**
- ✅ CLI commands work (`idlergear file deprecate`)
- ❌ MCP interception (only via MCP-enabled assistants)
- ✅ Multi-agent coordination (if daemon running)

---

## 📊 Token Savings Comparison

| Feature | Setup | Token Savings | Automatic? |
|---------|-------|---------------|------------|
| File Annotations | Manual annotation | 93% (200 vs 15,000) | ✅ Search is automatic |
| Knowledge Graph | Manual population | 95-98% (200 vs 10,000) | ❌ Requires setup |
| Mem0 | API key + config | 90% session context | ❌ Requires setup |
| File Registry | None | N/A (prevents errors) | ✅ Fully automatic |

---

## 🔍 How to Know It's Working

### File Registry Protection

**Test 1: Deprecate a file**
```bash
echo "test" > old.py
idlergear file deprecate old.py --successor new.py
idlergear file list --status deprecated
```

**Expected:** You see `old.py` listed as deprecated

**Test 2: Check access log**
```bash
# After AI tries to read old.py
cat .idlergear/access_log.jsonl
```

**Expected:** JSON log entry showing blocked access

**Test 3: AI behavior**
- AI tries to read `old.py` via MCP
- Gets error: "⚠️ old.py is deprecated. Use new.py instead."
- AI automatically switches to `new.py`

### File Annotations Working

**Test:**
```bash
idlergear file annotate test.py --description "Test file" --tags test
idlergear file search --tags test
```

**Expected:** Instant search results, shows test.py with annotations

### Daemon Coordination Working

**Test:**
```bash
# Terminal 1
idlergear daemon status

# Expected: "Daemon is running"

# Terminal 2
idlergear file deprecate x.py --successor y.py

# Terminal 1 - check logs
tail -f ~/.idlergear/daemon.log
```

**Expected:** Log shows broadcast event for file.deprecated

---

## 🚀 Quick Setup Checklist

### For Maximum Features (5 minutes)

```bash
# 1. Start daemon (enables multi-agent coordination)
idlergear daemon start

# 2. Populate knowledge graph (enables 95% token savings)
# In Python/AI assistant:
idlergear_graph_populate_git()
idlergear_graph_populate_code()

# 3. Annotate your key files (enables 93% token savings on those files)
idlergear file annotate src/main.py \
  --description "Main entry point" \
  --tags core,main

# 4. (Optional) Enable Mem0 for pattern learning
# Get key from https://app.mem0.ai
echo 'export MEM0_API_KEY="m0-your-key"' >> ~/.bashrc
echo -e '\n[plugins.mem0]\nenabled = true' >> .idlergear/config.toml
```

### For File Registry Only (30 seconds)

```bash
# Just use it! It's automatic.
idlergear file deprecate old_code.py --successor new_code.py

# AI assistants automatically blocked from old_code.py
```

---

## 📈 What You Should See Different

### Before v0.6.0:
```
AI Assistant: Let me read old_api.py to understand the authentication flow
> Reads old_api.py (deprecated version from 3 months ago)
> Writes code using outdated patterns
```

### After v0.6.0 (with file registry):
```
AI Assistant: Let me read old_api.py to understand the authentication flow
> Blocked: ⚠️ old_api.py is deprecated. Use new_api.py instead.
AI Assistant: Let me read new_api.py instead
> Reads current version
> Writes code using current patterns ✅
```

### With File Annotations:
```
Before: "Let me grep for authentication files..."
> Runs grep, reads 15 files
> 15,000 tokens used
> 30 seconds

After: "Let me search annotations for authentication..."
> idlergear_file_search(query="auth")
> 200 tokens used ✅
> Instant results ✅
```

### With Knowledge Graph:
```
Before: "What files import this module?"
> Greps entire codebase
> Reads dozens of files
> 20,000 tokens

After: "What files import this module?"
> idlergear_graph_query_file(path="module.py")
> Returns: related files, imports, symbols
> 500 tokens ✅
> Instant ✅
```

---

## ❓ FAQ

**Q: Do AI assistants automatically use file annotations?**
A: Only if you annotate files first. After annotation, they can use `idlergear_file_search` (93% token savings).

**Q: Is file registry protection automatic?**
A: YES! As soon as you run `idlergear file deprecate`, the MCP server automatically blocks access.

**Q: Does the knowledge graph work automatically?**
A: NO. You must populate it first with `idlergear_graph_populate_git()` and `idlergear_graph_populate_code()`.

**Q: Can I run Mem0 locally without cloud API?**
A: YES! Mem0 is open source. Just run `mem0 serve` locally and configure `host = "http://localhost:8000"` in config.toml. No API key needed!

**Q: How do I know if Mem0 is working?**
A: Check config.toml has `[plugins.mem0] enabled = true` and either `host` (local) or `api_key` (cloud) is set. Run `idlergear plugin status mem0` to verify.

**Q: Can I use file registry without MCP?**
A: Yes via CLI, but automatic interception only works with MCP-enabled AI assistants (Claude Code, etc.).

---

## 🎯 Recommended Setup for v0.6.0

**Minimal (works immediately):**
```bash
# Just deprecate files as needed
idlergear file deprecate old.py --successor new.py
# Protection is automatic!
```

**Recommended (5 min setup, maximum benefit):**
```bash
# 1. Enable daemon
idlergear daemon start

# 2. Populate graph (via AI assistant)
idlergear_graph_populate_git()
idlergear_graph_populate_code()

# 3. Annotate key files
idlergear file annotate src/*.py --description "..." --tags ...

# Done! You now have:
# - File deprecation protection (automatic)
# - 93% token savings on annotated files
# - 95% token savings on graph queries
# - Multi-agent coordination
```
