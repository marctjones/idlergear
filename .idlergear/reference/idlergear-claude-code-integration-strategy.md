---
id: 1
title: '# IdlerGear + Claude Code Integration Strategy'
created: '2026-01-03T04:57:04.737696Z'
updated: '2026-01-03T04:57:04.737723Z'
---
## Executive Summary

Getting AI assistants to reliably use knowledge management tools is fundamentally a **behavioral change problem**, not a technical one. The MCP integration exists and works, but Claude Code defaults to file-based patterns because they're simpler in the moment, even when worse long-term.

**Core insight:** We need to make IdlerGear usage the path of least resistance, not just the "right" way.

## 1. Core Philosophy

### The Integration Mandate

**"Context first, code second"**

Every Claude Code session should establish project context BEFORE writing any code. This means:
1. Understanding the vision (why this project exists)
2. Knowing what tasks are open (what needs doing)
3. Accessing recent discoveries (what we learned last time)
4. Checking the current plan (what we're building toward)

This is not optional. This is required for good AI-assisted development.

### Three-Tier Strategy

| Tier | Mechanism | Goal |
|------|-----------|------|
| **Mandatory** | System integration | Cannot be skipped |
| **Prompted** | Strong encouragement | Very hard to ignore |
| **Optional** | Available when needed | Discoverable |

## 2. Pain Point Mapping

| Claude Code Challenge | IdlerGear Solution | Integration Method |
|-----------------------|-------------------|-------------------|
| **Context loss between sessions** | `idlergear context` returns full project state | Mandatory session start hook |
| **No progress visibility** | Task lifecycle tracking | TodoWrite + IdlerGear tasks |
| **Incomplete execution** | Explicit task closing | Require task update before marking complete |
| **Over-engineering** | Vision + scoped tasks | Vision guards decisions |
| **File-based sprawl** | Structured API | Forbidden file patterns |
| **Lost decisions** | References | Prompted after major choices |

## 3. Integration Architecture

### Session Start (MANDATORY)

**Current problem:** CLAUDE.md says "run idlergear context" but Claude often skips it.

**Solution - Multi-layer enforcement:**

```
Layer 1: Slash command /start (easiest for user)
Layer 2: MCP tool description "MANDATORY AT SESSION START"
Layer 3: System prompt injection (if possible via hooks)
Layer 4: First-message detection + auto-prompt
```

**Implementation:**

1. **Make /start the entry point**
   - Rename `/context` → `/start` (more obvious)
   - Put it in statusline: "Run /start to begin"
   - Make it the FIRST thing in CLAUDE.md

2. **Auto-detect first message**
   - If first user message AND no `idlergear_context` called yet
   - Auto-inject: "Before proceeding, run /start to load project context"

3. **Hook integration (if available)**
   - `pre-session.sh`: Auto-run `idlergear context` and inject into prompt
   - Make context part of system message, not user request

### Task Creation (PROMPTED)

**Current problem:** Claude doesn't think to create tasks for bugs/debt found.

**Solution - Pattern detection + prompting:**

```python
# In CLAUDE.md
When you:
- Fix a bug → idlergear task create "..." --label bug
- Make design decision → idlergear reference add "..."
- Leave TODO → idlergear task create "..." --label tech-debt
- Discover quirk → idlergear note create "..."
```

**Enhanced MCP descriptions:**
- "MANDATORY: Create a task when you find a bug" (not just "Create a task")
- Give SPECIFIC triggers in tool description

**Claude Code TodoWrite bridging:**
- When Claude uses TodoWrite, suggest: "Convert these todos to idlergear tasks for persistence?"

### Decision Capture (PROMPTED)

**Current problem:** Design decisions happen in conversation, then lost.

**Solution - Explicit checkpoints:**

After major decisions:
1. Claude makes architectural choice
2. Auto-prompt: "Document this decision with `idlergear reference add`"
3. Make it ONE command away

**Trigger patterns:**
- Multiple approaches discussed
- User asks "which should we use?"
- Implementation approach chosen
- Trade-off explained

### File Operation Prevention (ENFORCED)

**Current problem:** Claude creates TODO.md instead of using IdlerGear.

**Solution - Active blocking:**

1. **CLAUDE.md**: List ALL forbidden files (already done)

2. **Pre-commit hook** (future):
   ```bash
   # Reject commits with forbidden files
   if git diff --cached --name-only | grep -E 'TODO.md|NOTES.md|SESSION'; then
     echo "ERROR: Use idlergear commands instead"
     exit 1
   fi
   ```

3. **Watch mode** (issue #112):
   - Detect TODO comments in diffs
   - Auto-suggest: "Create task instead: idlergear task create '...'"

## 4. Adoption Strategy

### Make IdlerGear Usage Easier Than Alternatives

| Task | File-based approach | IdlerGear approach | Make easier by... |
|------|--------------------|--------------------|-------------------|
| Add TODO | `// TODO: fix this` | `idlergear task create "fix this"` | MCP tool is 1 call |
| Check tasks | Read TODO.md | `idlergear task list` | MCP returns JSON |
| Save discovery | Write to NOTES.md | `idlergear note create "..."` | MCP tool autocompletes |
| Check vision | Search for VISION.md | `idlergear vision show` | Always works, no search |

**Key:** IdlerGear MCP tools should be FASTER than file operations for Claude.

### Training Through Repetition

**Pattern: Consistent prompting**

In CLAUDE.md, repeat the pattern:
```
Instead of X → Use idlergear Y
Instead of X → Use idlergear Y
Instead of X → Use idlergear Y
```

Not "IdlerGear provides task management" but concrete substitutions.

### Social Proof in Descriptions

MCP tool descriptions should say:
- "MANDATORY: ..." (authority)
- "CALL AT SESSION START" (explicit trigger)
- "NEVER write TODO comments" (prohibition)
- "This note WILL be available in your next session" (benefit)

Make it clear this is THE way, not A way.

## 5. Implementation Roadmap

### Phase 1: Session Start Reliability (Week 1)
- [ ] Rename /context → /start
- [ ] Add "MANDATORY" to idlergear_context MCP description
- [ ] Update CLAUDE.md to put /start FIRST
- [ ] Add statusline hint: "Run /start"

### Phase 2: Task Creation Adoption (Week 2)
- [ ] Add specific triggers to task_create MCP description
- [ ] Create task from bug/decision/debt patterns
- [ ] Bridge TodoWrite → IdlerGear tasks

### Phase 3: Decision Capture (Week 3)
- [ ] Add reference_add prompts after decisions
- [ ] Pattern detection for "which approach" discussions
- [ ] Auto-suggest reference creation

### Phase 4: File Prevention (Week 4)
- [ ] Pre-commit hook for forbidden files
- [ ] Watch mode for TODO comment detection
- [ ] Auto-suggest IdlerGear alternatives

### Phase 5: Measurement & Iteration (Ongoing)
- [ ] Track: % sessions that start with /start
- [ ] Track: Tasks created vs TODO comments written
- [ ] Track: References added vs decisions discussed
- [ ] Iterate based on data

## 6. Success Metrics

### Leading Indicators (Behavior)
- **90%+** of sessions start with `idlergear context` or /start
- **80%+** of bugs found result in task creation
- **0** TODO.md files created
- **50%+** of design decisions documented in references

### Lagging Indicators (Outcomes)
- **Reduced context re-explanation time** (measured by tokens in session starts)
- **Knowledge accumulation** (growing notes/refs/tasks over time)
- **Session continuity** (fewer "what were we doing?" questions)

### Qualitative Signals
- User reports: "I don't have to re-explain anymore"
- AI accuracy: "Claude remembers decisions from last week"
- Consistency: "Same knowledge across Claude/Copilot/Aider"

## 7. Key Insights

### Why AI Resists External Tools

1. **Extra cognitive load** - Must remember tool exists
2. **Uncertainty** - Not sure when to use it
3. **Habit** - File operations are default
4. **Immediate vs long-term** - Files work NOW, IdlerGear helps LATER

### How to Overcome Resistance

1. **Make it mandatory** - Remove the choice
2. **Make it specific** - "When X, do Y" not "consider using"
3. **Make it immediate** - MCP tools are faster than file search
4. **Make it rewarding** - Show the benefit (context in next session)

### The Adoption Paradox

**Problem:** AI won't use IdlerGear consistently until it sees the value, but won't see the value until it uses it consistently.

**Solution:** Force the behavior first (mandatory session start), then let benefits reinforce.

## 8. Recommended Immediate Actions

1. **Update MCP descriptions** - Add "MANDATORY", "CALL AT SESSION START", specific triggers
2. **Enhance /start command** - Make it obvious and first
3. **Add to system prompt** (if possible) - "Every session begins with project context"
4. **Create adoption dashboard** - Show % of best practices followed

## 9. Long-term Vision

**Ideal state:** Claude Code treats IdlerGear as infrastructure, not a tool.

Like git - you don't think "should I use git?", you just use it. IdlerGear should become automatic for:
- Session start → context
- Bug found → task
- Decision made → reference
- Quirk discovered → note

This requires both technical integration AND habit formation.

---

**Next step:** Implement Phase 1 (session start reliability) and measure adoption rate.
