"""Tests for plan management."""

import pytest

from idlergear.plans import (
    create_plan,
    get_current_plan,
    get_plan,
    list_plans,
    load_plan_from_file,
    switch_plan,
    update_plan,
)


class TestCreatePlan:
    """Tests for create_plan."""

    def test_create_plan(self, temp_project):
        plan = create_plan("auth-system")

        assert plan["name"] == "auth-system"
        assert plan["title"] == "auth-system"  # Default to name
        assert plan["state"] == "active"
        assert plan["created"] is not None
        assert "path" in plan

    def test_create_plan_with_title(self, temp_project):
        plan = create_plan("auth", title="Authentication System")

        assert plan["name"] == "auth"
        assert plan["title"] == "Authentication System"

    def test_create_plan_with_body(self, temp_project):
        plan = create_plan("auth", body="Implement OAuth2")

        assert plan["body"] == "Implement OAuth2"

    def test_create_duplicate_plan(self, temp_project):
        create_plan("test-plan")

        with pytest.raises(ValueError, match="already exists"):
            create_plan("test-plan")


class TestListPlans:
    """Tests for list_plans."""

    def test_list_empty(self, temp_project):
        plans = list_plans()
        assert plans == []

    def test_list_plans(self, temp_project):
        create_plan("alpha")
        create_plan("zebra")
        create_plan("beta")

        plans = list_plans()
        assert len(plans) == 3

    def test_list_sorted_by_name(self, temp_project):
        create_plan("zebra")
        create_plan("alpha")
        create_plan("beta")

        plans = list_plans()
        names = [p["name"] for p in plans]
        assert names == ["alpha", "beta", "zebra"]


class TestGetPlan:
    """Tests for get_plan."""

    def test_get_plan(self, temp_project):
        create_plan("test-plan", title="Test Plan", body="Description")

        plan = get_plan("test-plan")
        assert plan is not None
        assert plan["name"] == "test-plan"
        assert plan["title"] == "Test Plan"
        assert plan["body"] == "Description"

    def test_get_plan_case_insensitive(self, temp_project):
        create_plan("Test-Plan")

        plan = get_plan("test-plan")
        assert plan is not None

    def test_get_nonexistent_plan(self, temp_project):
        plan = get_plan("nonexistent")
        assert plan is None


class TestGetCurrentPlan:
    """Tests for get_current_plan."""

    def test_no_current_plan(self, temp_project):
        plan = get_current_plan()
        assert plan is None

    def test_get_current_plan(self, temp_project):
        create_plan("my-plan")
        switch_plan("my-plan")

        plan = get_current_plan()
        assert plan is not None
        assert plan["name"] == "my-plan"


class TestSwitchPlan:
    """Tests for switch_plan."""

    def test_switch_plan(self, temp_project):
        create_plan("plan-a")
        create_plan("plan-b")

        switch_plan("plan-a")
        current = get_current_plan()
        assert current["name"] == "plan-a"

        switch_plan("plan-b")
        current = get_current_plan()
        assert current["name"] == "plan-b"

    def test_switch_to_nonexistent(self, temp_project):
        result = switch_plan("nonexistent")
        assert result is None


class TestUpdatePlan:
    """Tests for update_plan."""

    def test_update_title(self, temp_project):
        create_plan("test", title="Original")

        updated = update_plan("test", title="Updated")
        assert updated["title"] == "Updated"

    def test_update_body(self, temp_project):
        create_plan("test", body="Original body")

        updated = update_plan("test", body="Updated body")
        assert updated["body"] == "Updated body"

    def test_update_state(self, temp_project):
        create_plan("test")

        updated = update_plan("test", state="completed")
        assert updated["state"] == "completed"

    def test_update_nonexistent(self, temp_project):
        result = update_plan("nonexistent", title="New")
        assert result is None


class TestLoadPlanFromFile:
    """Tests for load_plan_from_file."""

    def test_load_nonexistent_file(self, temp_project):
        from pathlib import Path

        result = load_plan_from_file(Path("/nonexistent/file.md"))
        assert result is None

    def test_load_plan_file(self, temp_project):
        from pathlib import Path

        plan = create_plan("test", title="Test Plan", body="Body content")

        loaded = load_plan_from_file(Path(plan["path"]))
        assert loaded is not None
        assert loaded["name"] == "test"
        assert loaded["title"] == "Test Plan"
        assert loaded["body"] == "Body content"
