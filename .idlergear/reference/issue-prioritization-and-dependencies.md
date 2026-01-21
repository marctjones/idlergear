---
id: 1
title: Issue Prioritization and Dependencies
created: '2026-01-09T05:11:37.419584Z'
updated: '2026-01-09T05:11:37.419604Z'
---
# Issue Prioritization and Dependencies

*Updated: 2026-01-09*

## Priority Summary

**HIGH (6 issues):** #117, #110, #88, #55, #80, #112
**MEDIUM (8 issues):** #87, #116, #103, #104, #82, #72, #100, #38
**LOW (16 issues):** Everything else

## Dependency Chains

### GitHub Wiki Chain
```
#88 (wiki master branch) 
 └─> #87 (auto-init wiki)
      └─> #117 (fix wiki sync) 
           └─> #116 (reference sync)
```

### Filesystem Chain
```
#55 (filesystem schema)
 └─> #112 (watch mode)
 └─> #60 (default tools)
```

### Language Support Chain
```
#100 (pluggable languages)
 └─> #97, #98 (language defaults)
      └─> #99 (env activate)
 └─> #33 (language templates)
```

### Project Wizard Chain
```
#38 (secrets) + #100 (languages)
 └─> #49 (project wizard)
```

## Recommended Work Order

1. **#110** - AGENTS.md flagged incorrectly (quick fix)
2. **#88** - GitHub wiki master branch (blocks wiki features)
3. **#117** - Fix wiki sync (blocks #116)
4. **#87** - Auto-init wiki
5. **#55** - Filesystem schema (enables #112)
6. **#80** - Event Bus (daemon enhancement)
7. **#112** - Watch mode (high user value)
8. **#103/#104** - Import/Export (adoption)
9. **#72** - Claude Code Plugin (distribution)
10. **#100** - Pluggable languages (enables many features)

## Issue Categories

### Bugs
- #117 - GitHubReferenceBackend wiki sync
- #110 - AGENTS.md flagged as misplaced
- #88 - GitHub wiki uses 'master' not 'main'

### Core Infrastructure (core-v1)
- #55 - Filesystem schema
- #80 - Daemon Event Bus
- #112 - Watch mode
- #116 - Reference sync
- #72 - Claude Code Plugin
- #60 - Default tool implementations
- #28 - Local wiki viewers

### GitHub Integration
- #117, #88, #87, #116 - Wiki-related
- Component label: `component:github`

### Language/Environment
- #100 - Pluggable language config
- #97 - Language-specific test defaults
- #98 - Language-specific dev setup
- #99 - MCP env activate tool
- #33 - Additional language templates

### Knowledge Types
- #82 - Plans link to issues
- #83 - Design reference subtype
- #84 - Decision/ADR subtype

### Data Management
- #103 - Import command
- #104 - Export command
- #106 - Archive functionality
- #107 - Template customization

### Adoption/Distribution
- #72 - Claude Code Plugin
- #93 - Multi-assistant install
- #94 - AI adoption training

### Convenience
- #111 - Self-update
- #115 - Release command
- #49 - Project setup wizard
- #38 - Secrets management

### Ongoing
- #109 - Test plan (~350 additional tests)
