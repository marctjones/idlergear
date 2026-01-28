"""Tests for plan management."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from idlergear.plans import (
    Plan,
    add_file_to_plan,
    archive_plan,
    complete_plan,
    create_plan,
    delete_plan,
    deprecate_file_in_plan,
    deprecate_plan,
    get_plan_files,
    list_plans,
    load_plan,
    plan_exists,
    remove_file_from_plan,
    restore_plan,
    save_plan,
    update_file_annotations_for_plan,
    update_plan,
)


@pytest.fixture
def plans_dir(tmp_path):
    """Create a temporary plans directory."""
    plans_path = tmp_path / ".idlergear" / "plans"
    plans_path.mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_plan_creation(plans_dir):
    """Test creating a plan."""
    plan = create_plan(
        name="test-feature",
        description="Test feature implementation",
        root=plans_dir,
        type="feature",
        milestone="v1.0",
    )

    assert plan.name == "test-feature"
    assert plan.description == "Test feature implementation"
    assert plan.status == "active"
    assert plan.type == "feature"
    assert plan.milestone == "v1.0"
    assert plan.created is not None
    assert plan.files == []
    assert plan.tasks == []


def test_plan_persistence(plans_dir):
    """Test that plans persist to disk."""
    plan = Plan(
        name="persist-test",
        description="Persistence test",
        type="feature",
    )
    save_plan(plan, plans_dir)

    # Check file exists
    plan_file = plans_dir / ".idlergear" / "plans" / "persist-test.json"
    assert plan_file.exists()

    # Check content
    with open(plan_file) as f:
        data = json.load(f)
    assert data["name"] == "persist-test"
    assert data["description"] == "Persistence test"


def test_load_plan(plans_dir):
    """Test loading a plan from disk."""
    # Create and save a plan
    original = create_plan(
        name="load-test",
        description="Load test plan",
        root=plans_dir,
    )

    # Load it back
    loaded = load_plan("load-test", plans_dir)

    assert loaded.name == original.name
    assert loaded.description == original.description
    assert loaded.status == original.status
    assert loaded.type == original.type


def test_load_nonexistent_plan(plans_dir):
    """Test loading a plan that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_plan("nonexistent", plans_dir)


def test_list_plans(plans_dir):
    """Test listing plans."""
    # Create multiple plans
    create_plan("plan-1", "First plan", plans_dir, type="feature")
    create_plan("plan-2", "Second plan", plans_dir, type="roadmap")
    create_plan("plan-3", "Third plan", plans_dir, type="feature")

    # List all plans
    plans = list_plans(plans_dir)
    assert len(plans) == 3

    # Filter by type
    feature_plans = list_plans(plans_dir, type_filter="feature")
    assert len(feature_plans) == 2
    assert all(p.type == "feature" for p in feature_plans)

    roadmap_plans = list_plans(plans_dir, type_filter="roadmap")
    assert len(roadmap_plans) == 1
    assert roadmap_plans[0].name == "plan-2"


def test_list_plans_by_status(plans_dir):
    """Test filtering plans by status."""
    # Create plans with different statuses
    plan1 = create_plan("active-plan", "Active", plans_dir)
    plan2 = create_plan("completed-plan", "Completed", plans_dir)
    update_plan("completed-plan", plans_dir, status="completed")

    # Filter by status
    active_plans = list_plans(plans_dir, status="active")
    assert len(active_plans) == 1
    assert active_plans[0].name == "active-plan"

    completed_plans = list_plans(plans_dir, status="completed")
    assert len(completed_plans) == 1
    assert completed_plans[0].name == "completed-plan"


def test_update_plan(plans_dir):
    """Test updating a plan."""
    create_plan("update-test", "Original description", plans_dir)

    # Update description
    plan = update_plan(
        "update-test",
        plans_dir,
        description="Updated description",
        milestone="v2.0",
    )

    assert plan.description == "Updated description"
    assert plan.milestone == "v2.0"

    # Verify persistence
    loaded = load_plan("update-test", plans_dir)
    assert loaded.description == "Updated description"
    assert loaded.milestone == "v2.0"


def test_delete_plan_archives_by_default(plans_dir):
    """Test that delete archives by default."""
    create_plan("delete-test", "Test deletion", plans_dir)

    # Delete (should archive)
    delete_plan("delete-test", plans_dir, permanent=False)

    # Plan should still exist but be archived
    plan = load_plan("delete-test", plans_dir)
    assert plan.status == "archived"
    assert plan.archived_at is not None


def test_delete_plan_permanent(plans_dir):
    """Test permanent deletion."""
    create_plan("permanent-delete", "Test permanent deletion", plans_dir)

    # Permanently delete
    delete_plan("permanent-delete", plans_dir, permanent=True)

    # Plan should not exist
    assert not plan_exists("permanent-delete", plans_dir)

    with pytest.raises(FileNotFoundError):
        load_plan("permanent-delete", plans_dir)


def test_plan_exists(plans_dir):
    """Test checking if a plan exists."""
    assert not plan_exists("test-plan", plans_dir)

    create_plan("test-plan", "Test", plans_dir)
    assert plan_exists("test-plan", plans_dir)


def test_ephemeral_plan_auto_archive(plans_dir):
    """Test that ephemeral plans have auto_archive=True by default."""
    plan = create_plan(
        "ephemeral-test",
        "Ephemeral plan",
        plans_dir,
        type="ephemeral",
    )

    assert plan.auto_archive is True


def test_hierarchical_plans(plans_dir):
    """Test parent-child plan relationships."""
    # Create parent
    parent = create_plan(
        "parent-plan",
        "Parent plan",
        plans_dir,
        type="initiative",
    )

    # Create child
    child = create_plan(
        "child-plan",
        "Child plan",
        plans_dir,
        type="feature",
        parent_plan="parent-plan",
    )

    # Check child has parent reference
    assert child.parent_plan == "parent-plan"

    # Check parent has child in sub_plans
    parent = load_plan("parent-plan", plans_dir)
    assert "child-plan" in parent.sub_plans


def test_cannot_create_duplicate_plan(plans_dir):
    """Test that duplicate plan names are rejected."""
    create_plan("duplicate-test", "First", plans_dir)

    with pytest.raises(ValueError, match="Plan already exists"):
        create_plan("duplicate-test", "Second", plans_dir)


def test_parent_plan_must_exist(plans_dir):
    """Test that parent plan must exist."""
    with pytest.raises(ValueError, match="Parent plan not found"):
        create_plan(
            "orphan-plan",
            "Orphan",
            plans_dir,
            parent_plan="nonexistent",
        )


def test_plan_to_dict(plans_dir):
    """Test converting plan to dictionary."""
    plan = Plan(
        name="dict-test",
        description="Test dict conversion",
        type="feature",
        files=["file1.py", "file2.py"],
        tasks=[1, 2, 3],
    )

    data = plan.to_dict()

    assert data["name"] == "dict-test"
    assert data["description"] == "Test dict conversion"
    assert data["type"] == "feature"
    assert data["files"] == ["file1.py", "file2.py"]
    assert data["tasks"] == [1, 2, 3]


def test_plan_from_dict():
    """Test creating plan from dictionary."""
    data = {
        "name": "from-dict",
        "description": "Created from dict",
        "type": "roadmap",
        "status": "active",
        "files": ["test.py"],
        "tasks": [42],
    }

    plan = Plan.from_dict(data)

    assert plan.name == "from-dict"
    assert plan.description == "Created from dict"
    assert plan.type == "roadmap"
    assert plan.files == ["test.py"]
    assert plan.tasks == [42]


def test_complete_plan(plans_dir):
    """Test completing a plan."""
    create_plan("complete-test", "Test completion", plans_dir)

    # Complete the plan
    plan = update_plan(
        "complete-test",
        plans_dir,
        status="completed",
        completed_at=datetime.now().isoformat(),
    )

    assert plan.status == "completed"
    assert plan.completed_at is not None

    # Verify persistence
    loaded = load_plan("complete-test", plans_dir)
    assert loaded.status == "completed"
    assert loaded.completed_at is not None


def test_plan_sorting_by_created_date(plans_dir):
    """Test that plans are sorted by created date (newest first)."""
    import time

    # Create plans with slight delays to ensure different timestamps
    create_plan("old-plan", "Old", plans_dir)
    time.sleep(0.01)
    create_plan("middle-plan", "Middle", plans_dir)
    time.sleep(0.01)
    create_plan("new-plan", "New", plans_dir)

    plans = list_plans(plans_dir)

    # Should be sorted newest first
    assert plans[0].name == "new-plan"
    assert plans[1].name == "middle-plan"
    assert plans[2].name == "old-plan"


# Phase 2: Lifecycle Management Tests


def test_deprecate_plan(plans_dir):
    """Test deprecating a plan."""
    from idlergear.plans import deprecate_plan

    create_plan("old-plan", "Old plan", plans_dir)

    # Deprecate without successor
    plan = deprecate_plan("old-plan", plans_dir)

    assert plan.status == "deprecated"
    assert plan.deprecated_at is not None
    assert plan.successor_plan is None


def test_deprecate_plan_with_successor(plans_dir):
    """Test deprecating a plan with a successor."""
    from idlergear.plans import deprecate_plan

    create_plan("v1-plan", "V1", plans_dir)
    create_plan("v2-plan", "V2", plans_dir)

    # Deprecate with successor
    plan = deprecate_plan("v1-plan", plans_dir, successor_name="v2-plan")

    assert plan.status == "deprecated"
    assert plan.successor_plan == "v2-plan"

    # Check successor has supersedes reference
    successor = load_plan("v2-plan", plans_dir)
    assert successor.supersedes_plan == "v1-plan"


def test_deprecate_plan_with_nonexistent_successor(plans_dir):
    """Test that deprecate fails with nonexistent successor."""
    from idlergear.plans import deprecate_plan

    create_plan("old-plan", "Old", plans_dir)

    with pytest.raises(ValueError, match="Successor plan not found"):
        deprecate_plan("old-plan", plans_dir, successor_name="nonexistent")


def test_archive_plan(plans_dir):
    """Test archiving a plan."""
    from idlergear.plans import archive_plan

    create_plan("archive-test", "Test archiving", plans_dir)

    plan = archive_plan("archive-test", plans_dir)

    assert plan.status == "archived"
    assert plan.archived_at is not None


def test_restore_plan(plans_dir):
    """Test restoring an archived plan."""
    from idlergear.plans import archive_plan, restore_plan

    create_plan("restore-test", "Test restore", plans_dir)
    archive_plan("restore-test", plans_dir)

    # Restore to active
    plan = restore_plan("restore-test", plans_dir)

    assert plan.status == "active"
    assert plan.archived_at is None


def test_restore_plan_to_custom_status(plans_dir):
    """Test restoring a plan to a custom status."""
    from idlergear.plans import archive_plan, restore_plan

    create_plan("restore-test", "Test restore", plans_dir)
    archive_plan("restore-test", plans_dir)

    # Restore to completed
    plan = restore_plan("restore-test", plans_dir, new_status="completed")

    assert plan.status == "completed"
    assert plan.archived_at is None


def test_restore_non_archived_plan_fails(plans_dir):
    """Test that restore fails for non-archived plans."""
    from idlergear.plans import restore_plan

    create_plan("active-plan", "Active", plans_dir)

    with pytest.raises(ValueError, match="not archived"):
        restore_plan("active-plan", plans_dir)


# Phase 3: File-Plan Integration Tests


def test_add_file_to_plan(plans_dir):
    """Test adding a file to a plan."""
    from idlergear.plans import add_file_to_plan

    create_plan("feature-plan", "Feature", plans_dir)

    plan = add_file_to_plan("feature-plan", "src/auth.py", plans_dir)

    assert "src/auth.py" in plan.files
    assert len(plan.files) == 1


def test_add_multiple_files_to_plan(plans_dir):
    """Test adding multiple files to a plan."""
    from idlergear.plans import add_file_to_plan

    create_plan("feature-plan", "Feature", plans_dir)

    add_file_to_plan("feature-plan", "src/auth.py", plans_dir)
    add_file_to_plan("feature-plan", "src/user.py", plans_dir)
    plan = add_file_to_plan("feature-plan", "tests/test_auth.py", plans_dir)

    assert len(plan.files) == 3
    assert "src/auth.py" in plan.files
    assert "src/user.py" in plan.files
    assert "tests/test_auth.py" in plan.files


def test_add_duplicate_file_is_idempotent(plans_dir):
    """Test that adding a duplicate file is idempotent."""
    from idlergear.plans import add_file_to_plan

    create_plan("feature-plan", "Feature", plans_dir)

    add_file_to_plan("feature-plan", "src/auth.py", plans_dir)
    plan = add_file_to_plan("feature-plan", "src/auth.py", plans_dir)

    # Should only appear once
    assert len(plan.files) == 1
    assert plan.files.count("src/auth.py") == 1


def test_remove_file_from_plan(plans_dir):
    """Test removing a file from a plan."""
    from idlergear.plans import add_file_to_plan, remove_file_from_plan

    create_plan("feature-plan", "Feature", plans_dir)
    add_file_to_plan("feature-plan", "src/auth.py", plans_dir)

    plan = remove_file_from_plan("feature-plan", "src/auth.py", plans_dir)

    assert "src/auth.py" not in plan.files
    assert len(plan.files) == 0


def test_deprecate_file_in_plan(plans_dir):
    """Test deprecating a file in a plan."""
    from idlergear.plans import add_file_to_plan, deprecate_file_in_plan

    create_plan("feature-plan", "Feature", plans_dir)
    add_file_to_plan("feature-plan", "src/legacy.py", plans_dir)

    plan = deprecate_file_in_plan("feature-plan", "src/legacy.py", plans_dir)

    assert "src/legacy.py" not in plan.files
    assert "src/legacy.py" in plan.deprecated_files


def test_get_plan_files(plans_dir):
    """Test getting files from a plan."""
    from idlergear.plans import add_file_to_plan, deprecate_file_in_plan, get_plan_files

    create_plan("feature-plan", "Feature", plans_dir)
    add_file_to_plan("feature-plan", "src/current.py", plans_dir)
    add_file_to_plan("feature-plan", "src/legacy.py", plans_dir)
    deprecate_file_in_plan("feature-plan", "src/legacy.py", plans_dir)

    # Get active files only
    files = get_plan_files("feature-plan", plans_dir, include_deprecated=False)
    assert len(files) == 1
    assert "src/current.py" in files
    assert "src/legacy.py" not in files

    # Get all files including deprecated
    all_files = get_plan_files("feature-plan", plans_dir, include_deprecated=True)
    assert len(all_files) == 2
    assert "src/current.py" in all_files
    assert "src/legacy.py" in all_files


def test_file_path_normalization(plans_dir):
    """Test that absolute paths are normalized to relative."""
    from idlergear.plans import add_file_to_plan

    create_plan("feature-plan", "Feature", plans_dir)

    # Add with absolute path
    abs_path = str(plans_dir / "src" / "auth.py")
    plan = add_file_to_plan("feature-plan", abs_path, plans_dir)

    # Should be stored as relative
    assert "src/auth.py" in plan.files
    assert abs_path not in plan.files


def test_update_file_annotations_for_plan(plans_dir):
    """Test updating file annotations when plan status changes."""
    from idlergear.plans import (
        add_file_to_plan,
        deprecate_plan,
        update_file_annotations_for_plan,
    )

    create_plan("v1-plan", "V1", plans_dir)
    create_plan("v2-plan", "V2", plans_dir)
    add_file_to_plan("v1-plan", "src/auth.py", plans_dir)
    add_file_to_plan("v1-plan", "src/user.py", plans_dir)

    # Deprecate plan
    deprecate_plan("v1-plan", plans_dir, successor_name="v2-plan")

    # Update file annotations
    updated = update_file_annotations_for_plan("v1-plan", plans_dir)

    # Should update 2 files
    assert updated == 2
