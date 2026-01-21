---
id: 1
title: MCP Servers Review 2026
created: '2026-01-18T02:57:41.231130Z'
updated: '2026-01-18T02:57:41.231152Z'
---
# MCP Servers Review (January 2026)

**Date:** 2026-01-17
**Context:** Issue #261 - Review official MCP servers for integration opportunities
**Decision:** NO integrations recommended at this time

## Executive Summary

Reviewed 100+ MCP servers from the official registry and reference servers.

**Recommendation: WAIT - SDK v2 breaking changes coming Q1 2026**

## Key Decisions

### 1. GitHub Backend - Stick with `gh` CLI

**Current:** GitHub backend using `gh` CLI wrapper  
**Alternative:** GitHub MCP server  
**Status:** MCP server ARCHIVED (moved to servers-archived)  
**Decision:** Continue using `gh` CLI + GraphQL API for Projects v2

**Rationale:**
- Archived servers have quality/maintenance concerns
- Our `gh` CLI wrapper works reliably
- GraphQL API better for Projects v2 (#257)

### 2. Git Integration - Keep Our Tools

**Current:** 18 task-aware git MCP tools  
**Alternative:** Git MCP server  
**Decision:** Keep our superior implementation

**Rationale:**
- Our tools support task-linked commits
- Full git lifecycle already covered
- No value add from MCP server

### 3. Structured Info - Consider Memory MCP

**Current:** Flat files (tasks, notes, references)  
**Alternative:** Memory MCP (knowledge graph)  
**Decision:** Prototype for #267 (NetworkX), DON'T integrate yet

**Rationale:**
- Knowledge graphs could enhance structured info (#264)
- BUT: Adds dependency, migration complexity
- Prototype only if NetworkX investigation promising

### 4. All Other Servers - Not Relevant

**Evaluated:**
- Search servers (Exa, Parallel, Seltz) - we have WebSearch
- Filesystem server - we have 11 filesystem tools
- Enterprise servers (Salesforce, Shopify) - out of scope
- Cloud servers (Contabo, SpotDB) - not relevant

**Decision:** No integration needed

## SDK v2 Breaking Changes

**Critical blocker for all integrations:**

- Python SDK: v2 anticipated Q1 2026
- TypeScript SDK: v2 anticipated Q1 2026
- Breaking changes expected
- **Integration now = rewrite in 3 months**

**Recommendation:** Wait for SDK v2 stable (Q2 2026), then re-evaluate.

## Reference Servers Reviewed

1. **Everything** - Demo/test server (not useful)
2. **Fetch** - Web content extraction (we have WebFetch)
3. **Filesystem** - File operations (we have 11 tools)
4. **Git** - Repository management (we have 18 tools)
5. **Memory** - Knowledge graph (worth exploring for #264)
6. **Sequential Thinking** - AI reasoning (not our use case)
7. **Time** - Timezone conversion (not needed)

## Registry Servers (100+)

Most third-party servers fell into:
- Business tools (CRM, e-commerce) - out of scope
- Cloud infrastructure - not relevant
- Specialized dev tools - too niche
- Research tools - potential future consideration

## Follow-up Actions

1. **Q2 2026:** Re-evaluate MCP servers after SDK v2 stable
2. **If #267 succeeds:** Prototype Memory MCP for structured info
3. **v0.9.0+:** Consider research-focused servers (Exa, Academia MCP)

## Related Issues

- #257 - GitHub Projects v2 (use GraphQL, not MCP)
- #264 - Structured info epic (Memory MCP could help)
- #267 - NetworkX investigation (prerequisite for Memory MCP)

## Constraints Honored

Per #261 requirements:
- ✅ Optional integration only (none recommended anyway)
- ✅ Graceful degradation (core features independent)
- ✅ Clear value proposition (none found = no integration)
- ✅ NOT building MCP management tool (correct scope)

## Sources

- https://github.com/modelcontextprotocol/servers
- https://registry.modelcontextprotocol.io/
- https://www.anthropic.com/news/model-context-protocol
- https://github.com/modelcontextprotocol/python-sdk
