---
id: 79
title: Auto-detect and upgrade projects when IdlerGear version changes
state: closed
created: '2026-01-09T02:23:57.142379Z'
labels:
- enhancement
- ux
priority: medium
---
When a new version of IdlerGear is run in a project for the first time, it should:

1. Store the IdlerGear version in `.idlergear/config.toml` (e.g., `idlergear_version = "0.3.17"`)
2. On any command, check if installed version > project version
3. If upgrade needed:
   - Either auto-upgrade and notify user
   - Or prompt "IdlerGear 0.3.17 is available (you have 0.3.14). Upgrade? [Y/n]"
4. Update `.claude/` files with new hooks, commands, skills, rules
5. Update version in config after successful upgrade

This eliminates the need for users to manually run `idlergear install --upgrade` in each project.

Implementation:
- Add `idlergear_version` to config schema
- Add version check in CLI entry point or install command
- Add `--force` flag to `install` for forcing reinstall
- Consider adding `idlergear upgrade` as alias for `idlergear install --force`
