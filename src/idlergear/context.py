"""Context gathering for AI session start.

Provides a unified view of project knowledge to help AI assistants
understand the project context quickly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectContext:
    """Aggregated project context for AI consumption."""

    vision: str | None = None
    current_plan: dict[str, Any] | None = None
    open_tasks: list[dict[str, Any]] = field(default_factory=list)
    open_explorations: list[dict[str, Any]] = field(default_factory=list)
    recent_notes: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    backends: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def gather_context(
    project_path: Path | None = None,
    include_references: bool = False,
    max_tasks: int = 10,
    max_notes: int = 5,
    max_explorations: int = 5,
) -> ProjectContext:
    """Gather all relevant project context.

    Args:
        project_path: Path to the project (defaults to cwd)
        include_references: Include reference documents in output
        max_tasks: Maximum number of tasks to include
        max_notes: Maximum number of recent notes to include
        max_explorations: Maximum number of explorations to include

    Returns:
        ProjectContext with all gathered knowledge
    """
    from idlergear.backends.registry import get_backend, get_configured_backend_name
    from idlergear.config import find_idlergear_root

    if project_path is None:
        project_path = find_idlergear_root()

    ctx = ProjectContext()

    # Record backend configuration
    for backend_type in ["task", "note", "explore", "reference", "plan", "vision"]:
        ctx.backends[backend_type] = get_configured_backend_name(
            backend_type, project_path=project_path
        )

    # Gather vision
    try:
        vision_backend = get_backend("vision", project_path=project_path)
        ctx.vision = vision_backend.get()
    except Exception as e:
        ctx.errors.append(f"Vision: {e}")

    # Gather current plan
    try:
        plan_backend = get_backend("plan", project_path=project_path)
        # Try get_current first, fall back to listing
        if hasattr(plan_backend, "get_current"):
            ctx.current_plan = plan_backend.get_current()
        else:
            plans = plan_backend.list()
            # Find current/active plan
            for plan in plans:
                if plan.get("current") or plan.get("active"):
                    ctx.current_plan = plan
                    break
            # If no current plan, use first one if exists
            if ctx.current_plan is None and plans:
                ctx.current_plan = plans[0]
    except Exception as e:
        ctx.errors.append(f"Plan: {e}")

    # Gather open tasks
    try:
        task_backend = get_backend("task", project_path=project_path)
        tasks = task_backend.list(state="open")
        # Sort by priority if available
        priority_order = {"high": 0, "medium": 1, "low": 2, None: 3}
        tasks.sort(key=lambda t: priority_order.get(t.get("priority"), 3))
        ctx.open_tasks = tasks[:max_tasks]
    except Exception as e:
        ctx.errors.append(f"Tasks: {e}")

    # Gather open explorations
    try:
        explore_backend = get_backend("explore", project_path=project_path)
        explorations = explore_backend.list(state="open")
        ctx.open_explorations = explorations[:max_explorations]
    except Exception as e:
        ctx.errors.append(f"Explorations: {e}")

    # Gather recent notes
    try:
        note_backend = get_backend("note", project_path=project_path)
        notes = note_backend.list()
        # Notes are typically sorted by recency already
        ctx.recent_notes = notes[:max_notes]
    except Exception as e:
        ctx.errors.append(f"Notes: {e}")

    # Optionally gather references
    if include_references:
        try:
            reference_backend = get_backend("reference", project_path=project_path)
            ctx.references = reference_backend.list()
        except Exception as e:
            ctx.errors.append(f"References: {e}")

    return ctx


def format_context(ctx: ProjectContext, verbose: bool = False) -> str:
    """Format project context as readable text.

    Args:
        ctx: The gathered project context
        verbose: Include more detail if True

    Returns:
        Formatted text suitable for display or AI consumption
    """
    lines = []
    lines.append("# Project Context")
    lines.append("")

    # Vision
    lines.append("## Vision")
    if ctx.vision:
        # Indent vision content
        for line in ctx.vision.strip().split("\n"):
            lines.append(line)
    else:
        lines.append("*No vision defined*")
    lines.append("")

    # Current Plan
    lines.append("## Current Plan")
    if ctx.current_plan:
        title = ctx.current_plan.get("title", ctx.current_plan.get("name", "Unnamed"))
        lines.append(f"**{title}**")
        if ctx.current_plan.get("body"):
            lines.append("")
            # Include first few lines of plan body
            body_lines = ctx.current_plan["body"].strip().split("\n")
            for line in body_lines[:10]:
                lines.append(line)
            if len(body_lines) > 10:
                lines.append("...")
    else:
        lines.append("*No active plan*")
    lines.append("")

    # Open Tasks
    task_count = len(ctx.open_tasks)
    lines.append(f"## Open Tasks ({task_count})")
    if ctx.open_tasks:
        for task in ctx.open_tasks:
            task_id = task.get("id", "?")
            title = task.get("title", "Untitled")
            priority = task.get("priority")
            priority_str = f" [{priority}]" if priority else ""
            labels = task.get("labels", [])
            label_str = f" ({', '.join(labels)})" if labels else ""
            lines.append(f"- #{task_id}{priority_str}: {title}{label_str}")
    else:
        lines.append("*No open tasks*")
    lines.append("")

    # Open Explorations
    if ctx.open_explorations:
        explore_count = len(ctx.open_explorations)
        lines.append(f"## Open Explorations ({explore_count})")
        for exp in ctx.open_explorations:
            exp_id = exp.get("id", "?")
            title = exp.get("title", "Untitled")
            lines.append(f"- #{exp_id}: {title}")
        lines.append("")

    # Recent Notes
    if ctx.recent_notes:
        note_count = len(ctx.recent_notes)
        lines.append(f"## Recent Notes ({note_count})")
        for note in ctx.recent_notes:
            content = note.get("content", "")
            # Truncate long notes
            if len(content) > 80:
                content = content[:77] + "..."
            lines.append(f"- {content}")
        lines.append("")

    # References (only if included)
    if ctx.references:
        ref_count = len(ctx.references)
        lines.append(f"## Reference Documents ({ref_count})")
        for ref in ctx.references:
            title = ref.get("title", "Untitled")
            lines.append(f"- {title}")
        lines.append("")

    # Backend configuration (verbose mode)
    if verbose:
        lines.append("## Backend Configuration")
        for backend_type, backend_name in ctx.backends.items():
            lines.append(f"- {backend_type}: {backend_name}")
        lines.append("")

    # Errors (if any)
    if ctx.errors:
        lines.append("## Warnings")
        for error in ctx.errors:
            lines.append(f"- {error}")
        lines.append("")

    return "\n".join(lines)


def format_context_json(ctx: ProjectContext) -> dict[str, Any]:
    """Format project context as JSON-serializable dict.

    Args:
        ctx: The gathered project context

    Returns:
        Dict suitable for JSON serialization
    """
    return {
        "vision": ctx.vision,
        "current_plan": ctx.current_plan,
        "open_tasks": ctx.open_tasks,
        "open_explorations": ctx.open_explorations,
        "recent_notes": ctx.recent_notes,
        "references": ctx.references,
        "backends": ctx.backends,
        "errors": ctx.errors if ctx.errors else None,
    }
