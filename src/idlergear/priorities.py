"""Project priorities registry for IdlerGear.

Provides structured priority tracking for:
- Feature areas (what we're building)
- Backends (what we integrate with)
- AI assistants (what we support)
- Validation matrices (test coverage)
- Coverage requirements (docs, tests, examples)
- Release requirements (what's needed for versions)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
import yaml

from idlergear.config import find_idlergear_root


class PriorityTier(str, Enum):
    """Priority tier for features/backends/assistants."""

    TIER_1 = "tier_1"  # Critical for v1.0
    TIER_2 = "tier_2"  # Important but not blocking
    TIER_3 = "tier_3"  # Nice to have
    CRITICAL = "critical"  # Must work
    HIGH = "high"  # High priority
    MEDIUM = "medium"  # Medium priority
    LOW = "low"  # Low priority


class Status(str, Enum):
    """Implementation/validation status."""

    COMPLETE = "complete"
    IN_PROGRESS = "in_progress"
    NOT_STARTED = "not_started"
    VALIDATED = "validated"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_TESTED = "not_tested"
    EXCELLENT = "excellent"
    BASIC = "basic"
    RESEARCH_NEEDED = "research_needed"


class FeatureArea(BaseModel):
    """A feature area being developed."""

    name: str = Field(..., description="Short name (e.g., 'test_integration')")
    full_name: str = Field(..., description="Full display name")
    milestone: Optional[str] = Field(None, description="Target milestone (e.g., 'v0.4.0')")
    status: Status = Field(Status.NOT_STARTED, description="Current status")
    completion: int = Field(0, ge=0, le=100, description="Completion percentage (0-100)")
    epic: Optional[int] = Field(None, description="GitHub epic issue number")
    notes: Optional[str] = Field(None, description="Additional notes")


class Backend(BaseModel):
    """A backend integration (local, GitHub, GitLab, etc.)."""

    name: str = Field(..., description="Backend name (e.g., 'github')")
    status: Status = Field(Status.NOT_STARTED, description="Implementation status")
    priority_level: Optional[PriorityTier] = Field(None, description="Priority level")
    features: dict[str, str] = Field(
        default_factory=dict, description="Feature support status"
    )
    notes: Optional[str] = Field(None, description="Additional notes")


class AIAssistant(BaseModel):
    """An AI assistant integration (Claude Code, Gemini, Goose, etc.)."""

    name: str = Field(..., description="Assistant name (e.g., 'claude_code')")
    status: Status = Field(Status.NOT_STARTED, description="Integration status")
    context: Optional[str] = Field(None, description="Context file/method")
    commands: Optional[str] = Field(None, description="Commands available")
    hooks: Optional[str] = Field(None, description="Hooks support")
    notes: Optional[str] = Field(None, description="Additional notes")


class ValidationStatus(str, Enum):
    """Validation matrix status icons."""

    VALIDATED = "✅ validated"
    PARTIAL = "⚠️ partial"
    NOT_TESTED = "⬜ not_tested"
    FAILED = "❌ failed"
    NO_SUPPORT = "❌ no_support"


class ValidationMatrix(BaseModel):
    """Validation matrix tracking tested combinations."""

    backend_features: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Backend × Feature combinations (e.g., github.tasks: '✅ validated')",
    )
    assistant_features: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Assistant × Feature combinations",
    )


class CoverageRequirements(BaseModel):
    """Coverage requirements for features/backends/assistants."""

    tier_1_feature: list[str] = Field(
        default_factory=lambda: [
            "implementation: Feature works end-to-end",
            "tests: 85%+ test coverage",
            "documentation: User guide + reference docs",
            "examples: At least 2 working examples",
            "validation: Tested with 2+ backends or assistants",
        ],
        description="Requirements for tier 1 features",
    )
    critical_backend: list[str] = Field(
        default_factory=lambda: [
            "implementation: All CRUD operations work",
            "tests: Backend test suite passes",
            "documentation: Setup guide in README",
            "examples: Example configuration",
        ],
        description="Requirements for critical backends",
    )


class ReleaseRequirements(BaseModel):
    """Requirements for v1.0 release."""

    feature_coverage: dict[str, Any] = Field(
        default_factory=dict, description="Feature area requirements"
    )
    backend_coverage: dict[str, Any] = Field(
        default_factory=dict, description="Backend requirements"
    )
    assistant_coverage: dict[str, Any] = Field(
        default_factory=dict, description="AI assistant requirements"
    )
    validation_matrix_minimum: dict[str, int] = Field(
        default_factory=dict, description="Minimum validation counts"
    )
    bugs_blocking_release: list[int] = Field(
        default_factory=list, description="Issue numbers blocking release"
    )
    documentation_required: list[str] = Field(
        default_factory=list, description="Required documentation"
    )


class PrioritiesRegistry(BaseModel):
    """Complete priorities registry."""

    version: str = Field("1.0.0", description="Schema version")
    last_updated: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Last update timestamp",
    )

    # Feature areas by tier
    feature_areas: dict[PriorityTier, list[FeatureArea]] = Field(
        default_factory=dict, description="Feature areas grouped by tier"
    )

    # Backends by priority
    backends: dict[PriorityTier, list[Backend]] = Field(
        default_factory=dict, description="Backends grouped by priority"
    )

    # AI assistants by tier
    ai_assistants: dict[PriorityTier, list[AIAssistant]] = Field(
        default_factory=dict, description="AI assistants grouped by tier"
    )

    # Validation matrix
    validation_matrix: ValidationMatrix = Field(
        default_factory=ValidationMatrix,
        description="Validation matrix tracking coverage",
    )

    # Coverage requirements
    coverage_requirements: CoverageRequirements = Field(
        default_factory=CoverageRequirements,
        description="Coverage requirements for quality gates",
    )

    # Release requirements
    v1_0_requirements: ReleaseRequirements = Field(
        default_factory=ReleaseRequirements,
        description="Requirements for v1.0 release",
    )

    @classmethod
    def load(cls, root: Optional[Path] = None) -> PrioritiesRegistry:
        """Load priorities registry from file.

        Args:
            root: IdlerGear root directory. If None, auto-detect.

        Returns:
            PrioritiesRegistry instance

        Raises:
            FileNotFoundError: If priorities.yaml doesn't exist
        """
        if root is None:
            root = find_idlergear_root()
            if not root:
                raise ValueError("Not in an IdlerGear project")

        priorities_file = root / ".idlergear" / "priorities.yaml"

        if not priorities_file.exists():
            # Return default registry
            return cls.create_default()

        with open(priorities_file) as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def save(self, root: Optional[Path] = None) -> None:
        """Save priorities registry to file.

        Args:
            root: IdlerGear root directory. If None, auto-detect.
        """
        if root is None:
            root = find_idlergear_root()
            if not root:
                raise ValueError("Not in an IdlerGear project")

        priorities_file = root / ".idlergear" / "priorities.yaml"
        priorities_file.parent.mkdir(parents=True, exist_ok=True)

        # Update timestamp
        self.last_updated = datetime.now().isoformat()

        # Convert to dict and save as YAML
        # Use mode='python' to get proper dict serialization
        data = self.model_dump(mode='python', exclude_none=True)

        # Convert enum keys to strings for clean YAML
        def clean_dict(obj):
            if isinstance(obj, dict):
                return {
                    (k.value if hasattr(k, 'value') else k): clean_dict(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [clean_dict(item) for item in obj]
            elif hasattr(obj, 'value'):  # Enum
                return obj.value
            return obj

        data = clean_dict(data)

        with open(priorities_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    @classmethod
    def create_default(cls) -> PrioritiesRegistry:
        """Create default priorities registry for a new project.

        Returns:
            Default PrioritiesRegistry instance
        """
        return cls(
            feature_areas={
                PriorityTier.TIER_1: [],
                PriorityTier.TIER_2: [],
                PriorityTier.TIER_3: [],
            },
            backends={
                PriorityTier.CRITICAL: [
                    Backend(
                        name="local",
                        status=Status.COMPLETE,
                        priority_level=PriorityTier.CRITICAL,
                        features={
                            "tasks": "complete",
                            "notes": "complete",
                            "references": "complete",
                            "plans": "complete",
                        },
                    )
                ],
                PriorityTier.HIGH: [],
                PriorityTier.MEDIUM: [],
            },
            ai_assistants={
                PriorityTier.TIER_1: [],
                PriorityTier.TIER_2: [],
            },
        )
