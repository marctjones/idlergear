"""Plan Objects - Scale-flexible development tracking.

Plans track development work from micro (minutes) to macro (months) scales.
They provide workflow-aware context for file annotations and enable automatic
annotation updates through plan lifecycle events.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Plan:
    """Represents a development plan at any scale.

    Plans can be:
    - Ephemeral (minutes-hours): AI multi-step workflows
    - Feature (days): Small feature work (3-5 files)
    - Roadmap (weeks): Medium initiatives (10-20 files)
    - Initiative (months): Large projects with sub-plans
    """

    name: str
    description: str
    status: str = "active"  # "active", "completed", "deprecated", "archived"
    type: str = "feature"  # "ephemeral", "feature", "roadmap", "initiative"

    # Content
    files: List[str] = None
    deprecated_files: List[str] = None
    tasks: List[int] = None
    references: List[str] = None

    # Hierarchy
    sub_plans: List[str] = None
    parent_plan: Optional[str] = None

    # Lifecycle
    milestone: Optional[str] = None
    supersedes_plan: Optional[str] = None
    successor_plan: Optional[str] = None

    # Automation
    auto_archive: bool = False

    # GitHub sync (optional)
    github_milestone_id: Optional[int] = None
    github_project_id: Optional[int] = None

    # Timestamps
    created: Optional[str] = None
    completed_at: Optional[str] = None
    deprecated_at: Optional[str] = None
    archived_at: Optional[str] = None

    def __post_init__(self):
        """Initialize lists and timestamps."""
        if self.files is None:
            self.files = []
        if self.deprecated_files is None:
            self.deprecated_files = []
        if self.tasks is None:
            self.tasks = []
        if self.references is None:
            self.references = []
        if self.sub_plans is None:
            self.sub_plans = []
        if self.created is None:
            self.created = datetime.now().isoformat()

        # Auto-archive ephemeral plans by default
        if self.type == "ephemeral" and not self.auto_archive:
            self.auto_archive = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Plan":
        """Create Plan from dictionary."""
        return cls(**data)


# Storage functions


def get_plans_dir(root: Path) -> Path:
    """Get plans directory, create if needed."""
    plans_dir = root / ".idlergear" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    return plans_dir


def save_plan(plan: Plan, root: Path) -> None:
    """Save plan to JSON file."""
    plans_dir = get_plans_dir(root)
    file_path = plans_dir / f"{plan.name}.json"

    with open(file_path, "w") as f:
        json.dump(plan.to_dict(), f, indent=2)

    logger.info(f"Saved plan: {plan.name}")


def load_plan(name: str, root: Path) -> Plan:
    """Load plan from JSON file.

    Args:
        name: Plan name (without .json extension)
        root: Project root directory

    Returns:
        Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plans_dir = get_plans_dir(root)
    file_path = plans_dir / f"{name}.json"

    if not file_path.exists():
        raise FileNotFoundError(f"Plan not found: {name}")

    with open(file_path) as f:
        data = json.load(f)

    return Plan.from_dict(data)


def list_plans(root: Path, status: Optional[str] = None, type_filter: Optional[str] = None) -> List[Plan]:
    """List all plans, optionally filtered by status or type.

    Args:
        root: Project root directory
        status: Filter by status (active, completed, deprecated, archived)
        type_filter: Filter by type (ephemeral, feature, roadmap, initiative)

    Returns:
        List of Plan objects matching filters
    """
    plans_dir = get_plans_dir(root)
    plans = []

    for file_path in plans_dir.glob("*.json"):
        try:
            plan = load_plan(file_path.stem, root)

            # Apply filters
            if status and plan.status != status:
                continue
            if type_filter and plan.type != type_filter:
                continue

            plans.append(plan)
        except Exception as e:
            logger.warning(f"Could not load plan {file_path.stem}: {e}")

    # Sort by created date (newest first)
    plans.sort(key=lambda p: p.created or "", reverse=True)

    return plans


def delete_plan(name: str, root: Path, permanent: bool = False) -> None:
    """Delete or archive a plan.

    Args:
        name: Plan name
        root: Project root directory
        permanent: If True, permanently delete. If False, archive first.

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)

    if not permanent and plan.status != "archived":
        # Archive first
        plan.status = "archived"
        plan.archived_at = datetime.now().isoformat()
        save_plan(plan, root)
        logger.info(f"Archived plan: {name}")
    else:
        # Permanently delete
        plans_dir = get_plans_dir(root)
        file_path = plans_dir / f"{name}.json"
        file_path.unlink()
        logger.info(f"Permanently deleted plan: {name}")


def plan_exists(name: str, root: Path) -> bool:
    """Check if a plan exists.

    Args:
        name: Plan name
        root: Project root directory

    Returns:
        True if plan exists, False otherwise
    """
    plans_dir = get_plans_dir(root)
    file_path = plans_dir / f"{name}.json"
    return file_path.exists()


# CRUD operations


def create_plan(
    name: str,
    description: str,
    root: Path,
    type: str = "feature",
    milestone: Optional[str] = None,
    parent_plan: Optional[str] = None,
    auto_archive: bool = False,
) -> Plan:
    """Create a new plan.

    Args:
        name: Plan name (must be unique)
        description: Plan description
        root: Project root directory
        type: Plan type (ephemeral, feature, roadmap, initiative)
        milestone: Milestone name or date
        parent_plan: Parent plan name for hierarchical plans
        auto_archive: Whether to auto-archive when completed

    Returns:
        Created Plan object

    Raises:
        ValueError: If plan already exists
    """
    if plan_exists(name, root):
        raise ValueError(f"Plan already exists: {name}")

    # Validate parent plan exists
    if parent_plan and not plan_exists(parent_plan, root):
        raise ValueError(f"Parent plan not found: {parent_plan}")

    plan = Plan(
        name=name,
        description=description,
        type=type,
        milestone=milestone,
        parent_plan=parent_plan,
        auto_archive=auto_archive,
    )

    save_plan(plan, root)

    # Add to parent's sub_plans if applicable
    if parent_plan:
        parent = load_plan(parent_plan, root)
        if name not in parent.sub_plans:
            parent.sub_plans.append(name)
            save_plan(parent, root)

    logger.info(f"Created plan: {name} (type={type})")
    return plan


def update_plan(name: str, root: Path, **updates) -> Plan:
    """Update a plan's fields.

    Args:
        name: Plan name
        root: Project root directory
        **updates: Fields to update (description, status, milestone, etc.)

    Returns:
        Updated Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)

    # Update fields
    for key, value in updates.items():
        if hasattr(plan, key):
            setattr(plan, key, value)
        else:
            logger.warning(f"Unknown plan field: {key}")

    save_plan(plan, root)
    logger.info(f"Updated plan: {name}")
    return plan


# Lifecycle management (Phase 2)


def complete_plan(name: str, root: Path) -> Plan:
    """Mark a plan as completed.

    Args:
        name: Plan name
        root: Project root directory

    Returns:
        Completed Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = update_plan(
        name, root, status="completed", completed_at=datetime.now().isoformat()
    )
    logger.info(f"Completed plan: {name}")
    return plan


def deprecate_plan(
    name: str, root: Path, successor_name: Optional[str] = None, reason: str = ""
) -> Plan:
    """Mark a plan as deprecated, optionally specifying a successor.

    Args:
        name: Plan name to deprecate
        root: Project root directory
        successor_name: Name of plan that replaces this one
        reason: Reason for deprecation

    Returns:
        Deprecated Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
        ValueError: If successor doesn't exist
    """
    # Validate successor exists
    if successor_name and not plan_exists(successor_name, root):
        raise ValueError(f"Successor plan not found: {successor_name}")

    plan = load_plan(name, root)
    plan.status = "deprecated"
    plan.deprecated_at = datetime.now().isoformat()
    if successor_name:
        plan.successor_plan = successor_name

        # Update successor to reference this plan
        successor = load_plan(successor_name, root)
        successor.supersedes_plan = name
        save_plan(successor, root)

    save_plan(plan, root)
    logger.info(f"Deprecated plan: {name} (successor: {successor_name})")
    return plan


def archive_plan(name: str, root: Path) -> Plan:
    """Archive a plan (soft archive, can be restored).

    Args:
        name: Plan name
        root: Project root directory

    Returns:
        Archived Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = update_plan(
        name, root, status="archived", archived_at=datetime.now().isoformat()
    )
    logger.info(f"Archived plan: {name}")
    return plan


def restore_plan(name: str, root: Path, new_status: str = "active") -> Plan:
    """Restore an archived plan.

    Args:
        name: Plan name
        root: Project root directory
        new_status: Status to restore to (default: active)

    Returns:
        Restored Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
        ValueError: If plan is not archived
    """
    plan = load_plan(name, root)
    if plan.status != "archived":
        raise ValueError(f"Plan '{name}' is not archived (status: {plan.status})")

    plan.status = new_status
    plan.archived_at = None
    save_plan(plan, root)
    logger.info(f"Restored plan: {name} to status: {new_status}")
    return plan


# File-plan integration (Phase 3)


def add_file_to_plan(name: str, file_path: str, root: Path) -> Plan:
    """Add a file to a plan.

    Args:
        name: Plan name
        file_path: File path to add (relative to root)
        root: Project root directory

    Returns:
        Updated Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)

    # Normalize file path (relative to root)
    if file_path.startswith("/"):
        # Convert absolute to relative
        try:
            file_path = str(Path(file_path).relative_to(root))
        except ValueError:
            # Path is outside root, keep as-is
            pass

    # Add if not already present
    if file_path not in plan.files:
        plan.files.append(file_path)
        save_plan(plan, root)
        logger.info(f"Added file '{file_path}' to plan '{name}'")

        # Update file annotation
        _update_file_annotation(file_path, plan, root)

    return plan


def remove_file_from_plan(name: str, file_path: str, root: Path) -> Plan:
    """Remove a file from a plan.

    Args:
        name: Plan name
        file_path: File path to remove
        root: Project root directory

    Returns:
        Updated Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)

    if file_path in plan.files:
        plan.files.remove(file_path)
        save_plan(plan, root)
        logger.info(f"Removed file '{file_path}' from plan '{name}'")

        # Clear file annotation
        _clear_file_annotation(file_path, root)

    return plan


def deprecate_file_in_plan(name: str, file_path: str, root: Path) -> Plan:
    """Move a file from active to deprecated in a plan.

    Args:
        name: Plan name
        file_path: File path to deprecate
        root: Project root directory

    Returns:
        Updated Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)

    if file_path in plan.files:
        plan.files.remove(file_path)
        if file_path not in plan.deprecated_files:
            plan.deprecated_files.append(file_path)
        save_plan(plan, root)
        logger.info(f"Deprecated file '{file_path}' in plan '{name}'")

        # Update file annotation
        _update_file_annotation(file_path, plan, root, deprecated=True)

    return plan


def get_plan_files(name: str, root: Path, include_deprecated: bool = False) -> List[str]:
    """Get all files associated with a plan.

    Args:
        name: Plan name
        root: Project root directory
        include_deprecated: Include deprecated files

    Returns:
        List of file paths

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)
    files = plan.files.copy()
    if include_deprecated:
        files.extend(plan.deprecated_files)
    return files


def update_file_annotations_for_plan(name: str, root: Path) -> int:
    """Update file annotations for all files in a plan.

    Called when plan status changes to propagate changes to file annotations.

    Args:
        name: Plan name
        root: Project root directory

    Returns:
        Number of files updated

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)
    updated = 0

    # Update active files
    for file_path in plan.files:
        _update_file_annotation(file_path, plan, root)
        updated += 1

    # Update deprecated files
    for file_path in plan.deprecated_files:
        _update_file_annotation(file_path, plan, root, deprecated=True)
        updated += 1

    logger.info(f"Updated {updated} file annotations for plan '{name}'")
    return updated


def _update_file_annotation(
    file_path: str, plan: Plan, root: Path, deprecated: bool = False
) -> None:
    """Update file annotation with plan metadata.

    Internal helper that integrates with file registry.

    Args:
        file_path: File path
        plan: Plan object
        root: Project root directory
        deprecated: Whether file is deprecated
    """
    try:
        from idlergear.file_registry import annotate_file, get_file_annotation

        # Build annotation metadata
        annotation = {
            "plan": plan.name,
            "plan_status": plan.status,
            "plan_type": plan.type,
        }

        if deprecated:
            annotation["deprecated"] = True
            annotation["deprecation_reason"] = f"Part of deprecated plan: {plan.name}"

        if plan.milestone:
            annotation["milestone"] = plan.milestone

        if plan.successor_plan:
            annotation["successor_plan"] = plan.successor_plan

        # Check if file already has annotation
        existing = get_file_annotation(str(root / file_path))
        if existing:
            # Merge with existing annotation
            annotation = {**existing, **annotation}

        # Update annotation
        annotate_file(
            path=str(root / file_path),
            description=annotation.get("description", ""),
            tags=annotation.get("tags", []),
            components=annotation.get("components", []),
            related_files=annotation.get("related_files", []),
            metadata=annotation,
        )

    except ImportError:
        # File registry not available (tests?)
        logger.debug(f"File registry not available, skipping annotation for {file_path}")
    except Exception as e:
        logger.warning(f"Failed to update annotation for {file_path}: {e}")


def _clear_file_annotation(file_path: str, root: Path) -> None:
    """Clear plan-related metadata from file annotation.

    Args:
        file_path: File path
        root: Project root directory
    """
    try:
        from idlergear.file_registry import annotate_file, get_file_annotation

        existing = get_file_annotation(str(root / file_path))
        if not existing:
            return

        # Remove plan-related fields
        metadata = existing.get("metadata", {})
        metadata.pop("plan", None)
        metadata.pop("plan_status", None)
        metadata.pop("plan_type", None)
        metadata.pop("deprecated", None)
        metadata.pop("deprecation_reason", None)
        metadata.pop("milestone", None)
        metadata.pop("successor_plan", None)

        # Update annotation
        annotate_file(
            path=str(root / file_path),
            description=existing.get("description", ""),
            tags=existing.get("tags", []),
            components=existing.get("components", []),
            related_files=existing.get("related_files", []),
            metadata=metadata,
        )

    except ImportError:
        logger.debug(f"File registry not available, skipping clear for {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clear annotation for {file_path}: {e}")


# AI Workflow Integration (Phase 5)


def create_ephemeral_plan_from_ai_report(
    steps: List[dict], root: Path, task_id: Optional[int] = None
) -> Plan:
    """Create ephemeral plan from AI multi-step workflow report.

    Automatically called when AI reports a multi-step plan via
    idlergear_ai_report_plan MCP tool.

    Args:
        steps: List of planned steps from AI report
                Each step: {"action": str, "target": str, "reason": str}
        root: Project root directory
        task_id: Associated task ID (if working on a task)

    Returns:
        Created ephemeral Plan object

    Example:
        >>> steps = [
        ...     {"action": "read file", "target": "config.py", "reason": "check settings"},
        ...     {"action": "edit file", "target": "main.py", "reason": "update logic"},
        ...     {"action": "run tests", "target": "pytest", "reason": "verify changes"}
        ... ]
        >>> plan = create_ephemeral_plan_from_ai_report(steps, root, task_id=278)
    """
    # Generate plan name from timestamp and task
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if task_id:
        name = f"ephemeral-task{task_id}-{timestamp}"
    else:
        name = f"ephemeral-{timestamp}"

    # Build description from steps
    description = "AI multi-step workflow:\n"
    for i, step in enumerate(steps, 1):
        action = step.get("action", "unknown")
        target = step.get("target", "")
        description += f"{i}. {action}: {target}\n"

    plan = create_plan(
        name=name,
        description=description,
        root=root,
        type="ephemeral",
        auto_archive=True,
    )

    # Add task to plan if provided
    if task_id:
        plan.tasks.append(task_id)
        save_plan(plan, root)

    logger.info(f"Created ephemeral plan from AI report: {name} ({len(steps)} steps)")
    return plan


def auto_complete_ephemeral_plan(name: str, root: Path) -> Plan:
    """Auto-complete and archive an ephemeral plan.

    Called when AI completes a multi-step workflow. Ephemeral plans with
    auto_archive=True are automatically archived when completed.

    Args:
        name: Plan name
        root: Project root directory

    Returns:
        Completed and archived Plan object

    Raises:
        FileNotFoundError: If plan doesn't exist
        ValueError: If plan is not ephemeral or doesn't have auto_archive enabled
    """
    plan = load_plan(name, root)

    if plan.type != "ephemeral":
        raise ValueError(f"Plan '{name}' is not ephemeral (type: {plan.type})")

    if not plan.auto_archive:
        raise ValueError(f"Plan '{name}' does not have auto_archive enabled")

    # Mark as completed
    plan.status = "completed"
    plan.completed_at = datetime.now().isoformat()

    # Immediately archive (auto_archive behavior)
    plan.status = "archived"
    plan.archived_at = datetime.now().isoformat()

    save_plan(plan, root)
    logger.info(f"Auto-completed and archived ephemeral plan: {name}")
    return plan


# Hierarchical Plans (Phase 6)


def get_plan_hierarchy(name: str, root: Path, max_depth: int = 10) -> dict:
    """Get complete plan hierarchy starting from a plan.

    Recursively fetches all sub-plans to build hierarchy tree.

    Args:
        name: Plan name (can be parent or child)
        root: Project root directory
        max_depth: Maximum recursion depth (prevents infinite loops)

    Returns:
        Hierarchy dictionary with structure:
        {
            "name": "plan-name",
            "type": "initiative",
            "status": "active",
            "sub_plans": [
                {"name": "sub1", "type": "feature", "status": "active", "sub_plans": []},
                {"name": "sub2", "type": "feature", "status": "completed", "sub_plans": []}
            ]
        }

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)

    def _build_hierarchy(plan_name: str, depth: int = 0) -> dict:
        """Recursive helper to build hierarchy."""
        if depth >= max_depth:
            logger.warning(f"Max depth {max_depth} reached at plan '{plan_name}'")
            return {"name": plan_name, "error": "max_depth_reached"}

        try:
            p = load_plan(plan_name, root)
            node = {
                "name": p.name,
                "type": p.type,
                "status": p.status,
                "description": p.description,
                "created": p.created,
                "sub_plans": [],
            }

            # Recursively add sub-plans
            for sub_name in p.sub_plans:
                node["sub_plans"].append(_build_hierarchy(sub_name, depth + 1))

            return node

        except FileNotFoundError:
            logger.warning(f"Sub-plan not found: {plan_name}")
            return {"name": plan_name, "error": "not_found"}

    return _build_hierarchy(name)


def get_plan_rollup_status(name: str, root: Path) -> dict:
    """Calculate rollup status from all sub-plans.

    Aggregates status, counts, and completion % from sub-plans.

    Args:
        name: Plan name (typically initiative or roadmap)
        root: Project root directory

    Returns:
        Rollup statistics:
        {
            "total_sub_plans": 5,
            "completed": 2,
            "active": 2,
            "deprecated": 1,
            "completion_pct": 40.0,
            "files": 25,  # Total files across all sub-plans
            "tasks": 12,  # Total tasks across all sub-plans
        }

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)

    rollup = {
        "total_sub_plans": 0,
        "completed": 0,
        "active": 0,
        "deprecated": 0,
        "archived": 0,
        "completion_pct": 0.0,
        "files": len(plan.files),
        "tasks": len(plan.tasks),
    }

    def _count_sub_plans(plan_name: str):
        """Recursive helper to count sub-plans."""
        try:
            p = load_plan(plan_name, root)
            rollup["total_sub_plans"] += 1

            # Count by status
            if p.status == "completed":
                rollup["completed"] += 1
            elif p.status == "active":
                rollup["active"] += 1
            elif p.status == "deprecated":
                rollup["deprecated"] += 1
            elif p.status == "archived":
                rollup["archived"] += 1

            # Aggregate files and tasks
            rollup["files"] += len(p.files)
            rollup["tasks"] += len(p.tasks)

            # Recurse into sub-plans
            for sub_name in p.sub_plans:
                _count_sub_plans(sub_name)

        except FileNotFoundError:
            logger.warning(f"Sub-plan not found: {plan_name}")

    # Count all sub-plans recursively
    for sub_name in plan.sub_plans:
        _count_sub_plans(sub_name)

    # Calculate completion percentage
    if rollup["total_sub_plans"] > 0:
        rollup["completion_pct"] = (
            rollup["completed"] / rollup["total_sub_plans"]
        ) * 100

    return rollup


def get_root_plan(name: str, root: Path, max_depth: int = 10) -> str:
    """Find the root (top-level) plan in hierarchy.

    Walks up the parent_plan chain until reaching a plan with no parent.

    Args:
        name: Plan name (can be anywhere in hierarchy)
        root: Project root directory
        max_depth: Maximum recursion depth (prevents infinite loops)

    Returns:
        Root plan name

    Raises:
        FileNotFoundError: If plan doesn't exist
    """
    plan = load_plan(name, root)

    # Walk up parent chain
    current_name = name
    for _ in range(max_depth):
        current_plan = load_plan(current_name, root)
        if not current_plan.parent_plan:
            # Found root
            return current_name
        current_name = current_plan.parent_plan

    # Hit max depth
    logger.warning(f"Max depth {max_depth} reached finding root for '{name}'")
    return current_name
