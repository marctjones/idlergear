---
id: 1
title: Skills-Based Integration Roadmap
created: '2026-01-08T00:12:03.159108Z'
updated: '2026-01-08T00:12:03.159135Z'
---
# Skills-Based Integration Roadmap

## Overview

This roadmap outlines the transition from CLAUDE.md-based integration to Claude Code Skills, following Anthropic's SKILL.md best practices. Skills provide automatic triggering, progressive disclosure, and better token efficiency.

## Vision Alignment

From IdlerGear vision:
> "The Adoption Challenge: Getting AI assistants to use it consistently requires hooks, slash commands, training"

Skills directly address this by providing **automatic triggering** based on semantic matching - no training required.

## Priority Matrix

| Issue | Title | Priority | Vision Alignment | Effort |
|-------|-------|----------|------------------|--------|
| **#59** | Create IdlerGear Skill (SKILL.md) | **HIGH** | Adoption + Token Efficiency | Medium |
| **#60** | Progressive disclosure (references/) | **HIGH** | Token Efficiency (97% goal) | Medium |
| **#61** | Trigger keywords in description | **HIGH** | Adoption (auto-trigger) | Small |
| **#66** | Update `idlergear install` | **HIGH** | Works across assistants | Medium |
| **#62** | Bundle helper scripts | Medium | Token Efficiency | Small |
| **#63** | Specialized sub-skills | Medium | Token Efficiency + Adoption | Large |
| **#64** | allowed-tools variants | Low | Security (nice-to-have) | Small |
| **#65** | Model field optimization | Low | Cost/Speed (nice-to-have) | Small |

## Implementation Order

### Phase 1: Core Skill (High Priority)
1. **#59** - Create main SKILL.md with proper frontmatter
2. **#61** - Write comprehensive trigger description
3. **#60** - Move detailed docs to references/

### Phase 2: Deployment (High Priority)
4. **#66** - Update `idlergear install` to create skill structure
5. **#62** - Bundle helper scripts for zero-context execution

### Phase 3: Optimization (Medium Priority)
6. **#63** - Create specialized sub-skills (tasks, notes, session, daemon)

### Phase 4: Polish (Low Priority)
7. **#64** - Add security-focused allowed-tools variants
8. **#65** - Add model field for speed/quality optimization

## Expected Outcomes

### Token Savings
| Stage | Current | With Skills |
|-------|---------|-------------|
| Startup | ~2000 tokens | ~100 tokens |
| Triggered | - | ~500 tokens |
| Full docs | - | ~2000 on-demand |

**Result**: 75-95% reduction in typical sessions

### Adoption Improvement
| Metric | Current | Expected |
|--------|---------|----------|
| Session start compliance | ~60% | ~95% (auto-trigger) |
| Knowledge capture | ~40% | ~80% (skill prompts) |
| Forbidden file violations | ~10% | 0% (skill + hooks) |

## Key Best Practices Applied

1. **Progressive Disclosure** - Core instructions in SKILL.md, details in references/
2. **Trigger-Rich Description** - Natural language keywords users actually say
3. **Zero-Context Scripts** - Execute without loading into context
4. **Focused Sub-Skills** - Load only what's needed
5. **Tool Restrictions** - Security variants for sensitive operations

## References

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [skill-creator SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)

## Related Issues

- #59: Create IdlerGear Skill for Claude Code
- #60: Apply progressive disclosure pattern
- #61: Improve skill description with trigger keywords
- #62: Bundle helper scripts for zero-context execution
- #63: Create specialized sub-skills
- #64: Add allowed-tools variants
- #65: Add model field for model selection
- #66: Update idlergear install to generate skill structure
