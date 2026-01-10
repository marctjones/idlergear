"""Tests for self-update functionality."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from idlergear.selfupdate import (
    InstallMethod,
    InstallInfo,
    VersionInfo,
    parse_version,
    compare_versions,
    get_latest_version,
    detect_install_method,
    do_self_update,
)


class TestParseVersion:
    """Tests for version parsing."""

    def test_simple_version(self):
        assert parse_version("0.3.17") == (0, 3, 17)

    def test_version_with_v_prefix(self):
        assert parse_version("v0.3.17") == (0, 3, 17)

    def test_version_with_suffix(self):
        assert parse_version("0.3.17-beta") == (0, 3, 17)

    def test_short_version(self):
        assert parse_version("1.0") == (1, 0, 0)

    def test_invalid_version(self):
        assert parse_version("invalid") == (0, 0, 0)


class TestCompareVersions:
    """Tests for version comparison."""

    def test_newer_version(self):
        assert compare_versions("0.3.17", "0.3.18") is True

    def test_older_version(self):
        assert compare_versions("0.3.18", "0.3.17") is False

    def test_same_version(self):
        assert compare_versions("0.3.17", "0.3.17") is False

    def test_major_version_bump(self):
        assert compare_versions("0.3.17", "1.0.0") is True

    def test_minor_version_bump(self):
        assert compare_versions("0.3.17", "0.4.0") is True


class TestGetLatestVersion:
    """Tests for getting latest version from GitHub."""

    @patch("idlergear.selfupdate.urllib.request.urlopen")
    def test_get_latest_version_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"tag_name": "v0.4.0"}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_latest_version(use_cache=False)

        assert result.latest == "0.4.0"
        assert result.error is None

    @patch("idlergear.selfupdate.urllib.request.urlopen")
    def test_get_latest_version_network_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        result = get_latest_version(use_cache=False)

        assert result.latest is None
        assert result.error is not None
        assert "Network error" in result.error

    @patch("idlergear.selfupdate.urllib.request.urlopen")
    def test_get_latest_version_rate_limited(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            None, 403, "Rate limited", {}, None
        )

        result = get_latest_version(use_cache=False)

        assert result.latest is None
        assert "rate limited" in result.error.lower()


class TestDetectInstallMethod:
    """Tests for install method detection."""

    def test_detect_returns_install_info(self):
        result = detect_install_method()

        assert isinstance(result, InstallInfo)
        assert isinstance(result.method, InstallMethod)
        assert isinstance(result.can_upgrade, bool)
        assert isinstance(result.upgrade_command, str)

    @patch("idlergear.selfupdate._is_editable_install")
    def test_detect_editable_install(self, mock_editable):
        mock_editable.return_value = True

        result = detect_install_method()

        assert result.method == InstallMethod.EDITABLE
        assert result.can_upgrade is False
        assert "git" in result.upgrade_command.lower()

    def test_install_info_has_required_fields(self):
        result = detect_install_method()

        assert result.method is not None
        assert result.path is not None or result.method == InstallMethod.UNKNOWN
        assert result.upgrade_command is not None


class TestDoSelfUpdate:
    """Tests for performing self-update."""

    @patch("idlergear.selfupdate.detect_install_method")
    @patch("idlergear.selfupdate.get_latest_version")
    def test_dry_run_returns_info(self, mock_version, mock_install):
        mock_version.return_value = VersionInfo(
            current="0.3.17",
            latest="0.4.0",
            update_available=True,
        )
        mock_install.return_value = InstallInfo(
            method=InstallMethod.PIPX,
            path=Path("/test"),
            can_upgrade=True,
            upgrade_command="pipx upgrade idlergear",
        )

        result = do_self_update(dry_run=True)

        assert result["dry_run"] is True
        assert result["success"] is True
        assert "pipx" in result["upgrade_command"]

    @patch("idlergear.selfupdate.detect_install_method")
    @patch("idlergear.selfupdate.get_latest_version")
    def test_cannot_upgrade_returns_error(self, mock_version, mock_install):
        mock_version.return_value = VersionInfo(
            current="0.3.17",
            latest="0.4.0",
            update_available=True,
        )
        mock_install.return_value = InstallInfo(
            method=InstallMethod.EDITABLE,
            path=Path("/test"),
            can_upgrade=False,
            upgrade_command="git pull",
            message="Editable install - use git",
        )

        result = do_self_update()

        assert result["success"] is False
        assert result["can_upgrade"] is False

    @patch("idlergear.selfupdate.detect_install_method")
    @patch("idlergear.selfupdate.get_latest_version")
    def test_already_latest_succeeds(self, mock_version, mock_install):
        mock_version.return_value = VersionInfo(
            current="0.4.0",
            latest="0.4.0",
            update_available=False,
        )
        mock_install.return_value = InstallInfo(
            method=InstallMethod.PIPX,
            path=Path("/test"),
            can_upgrade=True,
            upgrade_command="pipx upgrade idlergear",
        )

        result = do_self_update()

        assert result["success"] is True
        assert "latest" in result["message"].lower()
