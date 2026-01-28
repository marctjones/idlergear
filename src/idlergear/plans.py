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
