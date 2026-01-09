"""Tests for the upgrade module."""

import pytest
from pathlib import Path


class TestParseVersion:
    """Tests for parse_version function."""

    def test_parse_simple_version(self):
        from idlergear.upgrade import parse_version

        assert parse_version("0.3.17") == (0, 3, 17)

    def test_parse_version_with_v_prefix(self):
        from idlergear.upgrade import parse_version

        assert parse_version("v0.3.17") == (0, 3, 17)

    def test_parse_short_version(self):
        from idlergear.upgrade import parse_version

        assert parse_version("0.3") == (0, 3, 0)
        assert parse_version("1") == (1, 0, 0)

    def test_parse_version_with_suffix(self):
        from idlergear.upgrade import parse_version

        # Handle versions like "0.3.17-dev"
        assert parse_version("0.3.17-dev") == (0, 3, 17)

    def test_parse_invalid_version(self):
        from idlergear.upgrade import parse_version

        assert parse_version("invalid") == (0, 0, 0)
        assert parse_version("") == (0, 0, 0)


class TestVersionComparison:
    """Tests for version comparison logic."""

    def test_newer_version_detected(self, temp_project, monkeypatch):
        from idlergear.upgrade import needs_upgrade, set_project_version

        # Set old version in project
        set_project_version("0.1.0")

        # Mock current version to be newer
        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.17")

        assert needs_upgrade() is True

    def test_same_version_no_upgrade(self, temp_project, monkeypatch):
        from idlergear.upgrade import needs_upgrade, set_project_version

        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.17")
        set_project_version("0.3.17")

        assert needs_upgrade() is False

    def test_older_installed_no_upgrade(self, temp_project, monkeypatch):
        from idlergear.upgrade import needs_upgrade, set_project_version

        # Project has newer version than installed (downgrade scenario)
        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.16")
        set_project_version("0.3.17")

        assert needs_upgrade() is False

    def test_no_version_stored_needs_upgrade(self, temp_project, monkeypatch):
        from idlergear.upgrade import needs_upgrade

        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.17")

        # No version stored yet
        assert needs_upgrade() is True


class TestProjectVersion:
    """Tests for get/set project version."""

    def test_set_and_get_version(self, temp_project):
        from idlergear.upgrade import get_project_version, set_project_version

        set_project_version("1.2.3")
        assert get_project_version() == "1.2.3"

    def test_get_version_not_set(self, temp_project):
        from idlergear.upgrade import get_project_version

        assert get_project_version() is None


class TestGetUpgradeInfo:
    """Tests for get_upgrade_info function."""

    def test_upgrade_info_when_needed(self, temp_project, monkeypatch):
        from idlergear.upgrade import get_upgrade_info, set_project_version

        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.17")
        set_project_version("0.2.0")

        info = get_upgrade_info()

        assert info["needs_upgrade"] is True
        assert info["installed_version"] == "0.3.17"
        assert info["project_version"] == "0.2.0"

    def test_upgrade_info_when_current(self, temp_project, monkeypatch):
        from idlergear.upgrade import get_upgrade_info, set_project_version

        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.17")
        set_project_version("0.3.17")

        info = get_upgrade_info()

        assert info["needs_upgrade"] is False
        assert info["installed_version"] == "0.3.17"
        assert info["project_version"] == "0.3.17"


class TestDoUpgrade:
    """Tests for do_upgrade function."""

    def test_upgrade_updates_version(self, temp_project, monkeypatch):
        from idlergear.upgrade import do_upgrade, get_project_version, set_project_version

        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.17")
        set_project_version("0.2.0")

        results = do_upgrade()

        assert results["upgraded_from"] == "0.2.0"
        assert results["upgraded_to"] == "0.3.17"
        assert get_project_version() == "0.3.17"

    def test_upgrade_returns_file_results(self, temp_project, monkeypatch):
        from idlergear.upgrade import do_upgrade

        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.17")

        results = do_upgrade()

        assert "files" in results
        assert "rules" in results["files"]
        assert "hook_scripts" in results["files"]
        assert "commands" in results["files"]
        assert "skill" in results["files"]


class TestCheckAndPromptUpgrade:
    """Tests for check_and_prompt_upgrade function."""

    def test_no_upgrade_when_current(self, temp_project, monkeypatch, capsys):
        from idlergear.upgrade import check_and_prompt_upgrade, set_project_version

        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.17")
        set_project_version("0.3.17")

        result = check_and_prompt_upgrade()

        assert result is False
        captured = capsys.readouterr()
        assert "Upgrade available" not in captured.out

    def test_upgrade_when_outdated(self, temp_project, monkeypatch, capsys):
        from idlergear.upgrade import check_and_prompt_upgrade, set_project_version

        monkeypatch.setattr("idlergear.upgrade.__version__", "0.3.17")
        set_project_version("0.2.0")

        result = check_and_prompt_upgrade()

        assert result is True
        captured = capsys.readouterr()
        assert "Upgrade available" in captured.out
        assert "0.2.0" in captured.out
        assert "0.3.17" in captured.out

    def test_returns_false_outside_project(self, tmp_path, monkeypatch):
        from idlergear.upgrade import check_and_prompt_upgrade

        # Change to a directory without IdlerGear
        monkeypatch.chdir(tmp_path)

        result = check_and_prompt_upgrade()

        assert result is False
