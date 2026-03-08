"""
IdlerGear Core Services

This module contains the core business logic for IdlerGear, shared between
the CLI and MCP server interfaces.

Architecture:
- CLI wraps core services (formatting for humans)
- MCP server wraps core services (formatting for AI)
- Core services contain all business logic

Principles:
- Single source of truth (core is canonical)
- DRY (don't repeat yourself)
- Interface-independent logic
- Easy to test (test once, works everywhere)
"""

from idlergear.core.tasks import TaskService

__all__ = ["TaskService"]
