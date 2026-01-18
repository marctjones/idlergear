"""Tests for priorities registry."""

import json
from pathlib import Path

import pytest

from idlergear.priorities import (
    PrioritiesRegistry,
    PriorityTier,
    Status,
    FeatureArea,
    Backend,
    AIAssistant,
)


@pytest.fixture
def temp_root(tmp_path):
    """Create temporary IdlerGear root."""
    idlergear_dir = tmp_path / ".idlergear"
    idlergear_dir.mkdir()
    return tmp_path


def test_create_default_registry():
    """Test creating default priorities registry."""
    registry = PrioritiesRegistry.create_default()

    assert registry.version == "1.0.0"
    assert registry.last_updated
    assert PriorityTier.TIER_1 in registry.feature_areas
    assert PriorityTier.CRITICAL in registry.backends
    assert len(registry.backends[PriorityTier.CRITICAL]) == 1
    assert registry.backends[PriorityTier.CRITICAL][0].name == "local"


def test_save_and_load_registry(temp_root):
    """Test saving and loading registry from file."""
    registry = PrioritiesRegistry.create_default()
    registry.save(temp_root)

    # Check file was created
    priorities_file = temp_root / ".idlergear" / "priorities.yaml"
    assert priorities_file.exists()

    # Load and verify
    loaded = PrioritiesRegistry.load(temp_root)
    assert loaded.version == registry.version
    assert len(loaded.backends[PriorityTier.CRITICAL]) == 1
    assert loaded.backends[PriorityTier.CRITICAL][0].name == "local"


def test_add_feature_area(temp_root):
    """Test adding a feature area."""
    registry = PrioritiesRegistry.create_default()

    # Add feature
    feature = FeatureArea(
        name="test_integration",
        full_name="Test Framework Integration",
        milestone="v0.4.0",
        status=Status.IN_PROGRESS,
        completion=70,
        epic=144,
        notes="Task-aware testing",
    )
    registry.feature_areas[PriorityTier.TIER_1].append(feature)

    # Save and reload
    registry.save(temp_root)
    loaded = PrioritiesRegistry.load(temp_root)

    # Verify
    tier_1_features = loaded.feature_areas[PriorityTier.TIER_1]
    assert len(tier_1_features) == 1
    assert tier_1_features[0].name == "test_integration"
    assert tier_1_features[0].completion == 70
    assert tier_1_features[0].milestone == "v0.4.0"


def test_add_backend(temp_root):
    """Test adding a backend."""
    registry = PrioritiesRegistry.create_default()

    # Add backend
    backend = Backend(
        name="github",
        status=Status.IN_PROGRESS,
        priority_level=PriorityTier.CRITICAL,
        features={
            "issues": "complete",
            "labels": "complete",
            "milestones": "partial",
            "projects": "not_started",
        },
        notes="Projects v2 in progress",
    )
    registry.backends[PriorityTier.CRITICAL].append(backend)

    # Save and reload
    registry.save(temp_root)
    loaded = PrioritiesRegistry.load(temp_root)

    # Verify
    critical_backends = loaded.backends[PriorityTier.CRITICAL]
    assert len(critical_backends) == 2  # local + github
    github = [b for b in critical_backends if b.name == "github"][0]
    assert github.status == Status.IN_PROGRESS
    assert github.features["issues"] == "complete"
    assert github.features["projects"] == "not_started"


def test_add_ai_assistant(temp_root):
    """Test adding an AI assistant."""
    registry = PrioritiesRegistry.create_default()

    # Add assistant
    assistant = AIAssistant(
        name="claude_code",
        status=Status.EXCELLENT,
        context="CLAUDE.md + MCP + hooks",
        commands="126 MCP tools",
        hooks="Full lifecycle",
    )
    registry.ai_assistants[PriorityTier.TIER_1].append(assistant)

    # Save and reload
    registry.save(temp_root)
    loaded = PrioritiesRegistry.load(temp_root)

    # Verify
    tier_1_assistants = loaded.ai_assistants[PriorityTier.TIER_1]
    assert len(tier_1_assistants) == 1
    assert tier_1_assistants[0].name == "claude_code"
    assert tier_1_assistants[0].status == Status.EXCELLENT
    assert tier_1_assistants[0].commands == "126 MCP tools"


def test_validation_matrix(temp_root):
    """Test validation matrix."""
    registry = PrioritiesRegistry.create_default()

    # Add validation data
    registry.validation_matrix.backend_features = {
        "github": {
            "tasks": "✅ validated",
            "notes": "✅ validated",
            "plans": "⚠️ partial",
            "projects": "❌ not_implemented",
        }
    }
    registry.validation_matrix.assistant_features = {
        "claude_code": {
            "context_injection": "✅ validated",
            "commands": "✅ validated",
            "hooks": "✅ validated",
        }
    }

    # Save and reload
    registry.save(temp_root)
    loaded = PrioritiesRegistry.load(temp_root)

    # Verify
    assert "github" in loaded.validation_matrix.backend_features
    assert loaded.validation_matrix.backend_features["github"]["tasks"] == "✅ validated"
    assert "claude_code" in loaded.validation_matrix.assistant_features
    assert (
        loaded.validation_matrix.assistant_features["claude_code"]["hooks"]
        == "✅ validated"
    )


def test_release_requirements(temp_root):
    """Test release requirements."""
    registry = PrioritiesRegistry.create_default()

    # Add release requirements
    registry.v1_0_requirements.feature_coverage = {
        "minimum_tier_1": 4,
        "required": ["test_integration", "multi_assistant"],
    }
    registry.v1_0_requirements.bugs_blocking_release = [260, 257]
    registry.v1_0_requirements.documentation_required = [
        "User manual",
        "API reference",
    ]

    # Save and reload
    registry.save(temp_root)
    loaded = PrioritiesRegistry.load(temp_root)

    # Verify
    assert loaded.v1_0_requirements.feature_coverage["minimum_tier_1"] == 4
    assert 260 in loaded.v1_0_requirements.bugs_blocking_release
    assert "User manual" in loaded.v1_0_requirements.documentation_required


def test_yaml_format(temp_root):
    """Test that YAML is human-readable."""
    registry = PrioritiesRegistry.create_default()
    registry.save(temp_root)

    priorities_file = temp_root / ".idlergear" / "priorities.yaml"
    content = priorities_file.read_text()

    # Check for clean YAML (no Python object tags)
    assert "!!python" not in content
    assert "tier_1:" in content
    assert "critical:" in content
    assert "local" in content
    assert "complete" in content


def test_timestamp_update(temp_root):
    """Test that timestamp updates on save."""
    registry = PrioritiesRegistry.create_default()
    first_timestamp = registry.last_updated

    # Save
    registry.save(temp_root)

    # Timestamp should update
    assert registry.last_updated != first_timestamp

    # Reload and verify
    loaded = PrioritiesRegistry.load(temp_root)
    assert loaded.last_updated == registry.last_updated
