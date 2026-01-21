---
id: 54
title: Implement Goose-specific hooks/integration patterns
state: closed
created: '2026-01-07T04:29:31.749077Z'
labels:
- goose-integration
- enhancement
priority: high
---
Goose doesn't have lifecycle hooks like Claude Code - it uses MCP extensions instead. However, we can:

1. Update .goosehints to include **instructions** for using IdlerGear effectively in Goose
2. Add system prompt recommendations for session management
3. Create Goose-specific extension configurations
4. Document best practices for Goose CLI vs GUI

**Approach:**
- .goosehints already exists with MCP server recommendations
- Add "Recommended Session Flow" section
- Document prompts for beginning/end of session
- Create example Goose configuration snippets
