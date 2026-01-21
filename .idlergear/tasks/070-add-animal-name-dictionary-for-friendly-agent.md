---
id: 70
title: Add animal name dictionary for friendly agent identification
state: open
created: '2026-01-08T23:55:48.580276Z'
labels:
- feature
- 'component: daemon'
priority: medium
---
## Overview

Instead of hard-to-remember agent IDs like `claude-code-4ebf3b24`, auto-assign friendly animal names like `turtle`, `rabbit`, `fox`.

## Requirements

1. Curate a list of 512-1024 unique animal names
   - Common animals: mammals, birds, fish, reptiles, insects
   - Easy to spell and remember
   - Avoid duplicates and confusing similar names

2. Random assignment on agent registration
   - Hash agent_id to get consistent animal name
   - Or assign randomly and persist in `.idlergear/agents/names.json`

3. Sources to consider:
   - Wikipedia list of animals
   - Curated wordlists from GitHub
   - NPM `animals` package (~300 names)

## Example

```bash
idlergear agent list
# turtle (claude-code-4ebf3b24) - active
# rabbit (claude-code-39957650) - active
```
