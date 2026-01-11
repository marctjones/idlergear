"""Tests for the doctor module (health check functionality)."""

import json
from pathlib import Path


class TestCheckStatus:
    """Tests for CheckStatus enum."""

    def test_status_values(self):
        from idlergear.doctor import CheckStatus

        assert CheckStatus.OK == "ok"
        assert CheckStatus.WARNING == "warning"
        assert CheckStatus.ERROR == "error"
        assert CheckStatus.INFO == "info"


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_create_simple_result(self):
        from idlergear.doctor import CheckResult, CheckStatus

        result = CheckResult(
            name="test",
            status=CheckStatus.OK,
            message="All good",
        )

        assert result.name == "test"
        assert result.status == CheckStatus.OK
        assert result.message == "All good"
        assert result.fix is None
        assert result.details == {}

    def test_create_result_with_fix(self):
        from idlergear.doctor import CheckResult, CheckStatus

        result = CheckResult(
            name="version",
            status=CheckStatus.WARNING,
            message="Version outdated",
            fix="idlergear install --upgrade",
        )

        assert result.fix == "idlergear install --upgrade"

    def test_to_dict(self):
        from idlergear.doctor import CheckResult, CheckStatus

        result = CheckResult(
            name="test",
            status=CheckStatus.WARNING,
            message="Warning message",
            fix="run fix command",
            details={"key": "value"},
        )

        d = result.to_dict()

        assert d["name"] == "test"
        assert d["status"] == "warning"
        assert d["message"] == "Warning message"
        assert d["fix"] == "run fix command"
        assert d["details"] == {"key": "value"}


class TestDoctorReport:
    """Tests for DoctorReport dataclass."""

    def test_healthy_report(self):
        from idlergear.doctor import DoctorReport, CheckResult, CheckStatus

        report = DoctorReport(
            checks=[
                CheckResult("check1", CheckStatus.OK, "OK"),
                CheckResult("check2", CheckStatus.OK, "OK"),
            ],
            project_path=Path("/test"),
            installed_version="0.3.17",
            project_version="0.3.17",
        )

        assert report.is_healthy is True
        assert report.has_errors is False
        assert report.has_warnings is False

    def test_report_with_warnings(self):
        from idlergear.doctor import DoctorReport, CheckResult, CheckStatus

        report = DoctorReport(
            checks=[
                CheckResult("check1", CheckStatus.OK, "OK"),
                CheckResult("check2", CheckStatus.WARNING, "Warning"),
            ],
            project_path=Path("/test"),
            installed_version="0.3.17",
            project_version="0.3.16",
        )

        assert report.is_healthy is False
        assert report.has_errors is False
        assert report.has_warnings is True

    def test_report_with_errors(self):
        from idlergear.doctor import DoctorReport, CheckResult, CheckStatus

        report = DoctorReport(
            checks=[
                CheckResult("check1", CheckStatus.ERROR, "Error"),
                CheckResult("check2", CheckStatus.OK, "OK"),
            ],
            project_path=Path("/test"),
            installed_version="0.3.17",
            project_version=None,
        )

        assert report.is_healthy is False
        assert report.has_errors is True

    def test_to_dict(self):
        from idlergear.doctor import DoctorReport, CheckResult, CheckStatus

        report = DoctorReport(
            checks=[
                CheckResult("check1", CheckStatus.OK, "OK"),
            ],
            project_path=Path("/test"),
            installed_version="0.3.17",
            project_version="0.3.17",
        )

        d = report.to_dict()

        assert d["project_path"] == "/test"
        assert d["installed_version"] == "0.3.17"
        assert d["project_version"] == "0.3.17"
        assert d["is_healthy"] is True
        assert len(d["checks"]) == 1


class TestCheckInitialization:
    """Tests for check_initialization function."""

    def test_initialized_project(self, tmp_path):
        from idlergear.doctor import check_initialization, CheckStatus

        # Create a properly initialized project
        idlergear_dir = tmp_path / ".idlergear"
        idlergear_dir.mkdir()
        (idlergear_dir / "config.json").write_text("{}")

        result = check_initialization(tmp_path)

        assert result.status == CheckStatus.OK
        assert "initialized" in result.message.lower()

    def test_missing_idlergear_dir(self, tmp_path):
        from idlergear.doctor import check_initialization, CheckStatus

        result = check_initialization(tmp_path)

        assert result.status == CheckStatus.ERROR
        assert result.fix == "idlergear init"

    def test_missing_config_file(self, tmp_path):
        from idlergear.doctor import check_initialization, CheckStatus

        # Create .idlergear dir but no config
        (tmp_path / ".idlergear").mkdir()

        result = check_initialization(tmp_path)

        assert result.status == CheckStatus.WARNING
        assert "config" in result.message.lower()


class TestCheckVersion:
    """Tests for check_version function."""

    def test_current_version(self, temp_project, monkeypatch):
        from idlergear.doctor import check_version, CheckStatus
        from idlergear.upgrade import set_project_version

        monkeypatch.setattr("idlergear.doctor.__version__", "0.3.17")
        set_project_version("0.3.17")

        result = check_version(temp_project)

        assert result.status == CheckStatus.OK

    def test_outdated_version(self, temp_project, monkeypatch):
        from idlergear.doctor import check_version, CheckStatus
        from idlergear.upgrade import set_project_version

        monkeypatch.setattr("idlergear.doctor.__version__", "0.3.17")
        set_project_version("0.2.0")

        result = check_version(temp_project)

        assert result.status == CheckStatus.WARNING
        assert "older" in result.message.lower()
        assert result.fix == "idlergear install --upgrade"

    def test_no_version_stored(self, temp_project, monkeypatch):
        from idlergear.doctor import check_version, CheckStatus

        monkeypatch.setattr("idlergear.doctor.__version__", "0.3.17")
        # Don't set any version

        result = check_version(temp_project)

        assert result.status == CheckStatus.WARNING
        assert "no version" in result.message.lower()


class TestCheckMcpConfig:
    """Tests for check_mcp_config function."""

    def test_valid_mcp_config(self, temp_project):
        from idlergear.doctor import check_mcp_config, CheckStatus

        # Create valid .mcp.json
        mcp_path = temp_project / ".mcp.json"
        mcp_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "idlergear": {
                            "command": "idlergear-mcp",
                            "args": [],
                        }
                    }
                }
            )
        )

        result = check_mcp_config(temp_project)

        assert result.status == CheckStatus.OK

    def test_missing_mcp_config(self, temp_project):
        from idlergear.doctor import check_mcp_config, CheckStatus

        result = check_mcp_config(temp_project)

        assert result.status == CheckStatus.ERROR
        assert result.fix == "idlergear install"

    def test_mcp_config_without_idlergear(self, temp_project):
        from idlergear.doctor import check_mcp_config, CheckStatus

        mcp_path = temp_project / ".mcp.json"
        mcp_path.write_text(
            json.dumps({"mcpServers": {"other": {"command": "other-mcp"}}})
        )

        result = check_mcp_config(temp_project)

        assert result.status == CheckStatus.ERROR


class TestCheckHooksConfig:
    """Tests for check_hooks_config function."""

    def test_valid_hooks_config(self, temp_project):
        from idlergear.doctor import check_hooks_config, CheckStatus

        hooks_dir = temp_project / ".claude"
        hooks_dir.mkdir()
        hooks_file = hooks_dir / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {"hooks": {"PostToolUse": [{"command": "idlergear check --file"}]}}
            )
        )

        result = check_hooks_config(temp_project)

        assert result.status == CheckStatus.OK

    def test_missing_hooks_config(self, temp_project):
        from idlergear.doctor import check_hooks_config, CheckStatus

        result = check_hooks_config(temp_project)

        assert result.status == CheckStatus.WARNING
        assert result.fix == "idlergear install"


class TestCheckLegacyFiles:
    """Tests for check_legacy_files function."""

    def test_no_legacy_files(self, tmp_path):
        from idlergear.doctor import check_legacy_files, CheckStatus

        # Create clean project with no legacy files
        idlergear_dir = tmp_path / ".idlergear"
        idlergear_dir.mkdir()
        (idlergear_dir / "config.json").write_text("{}")

        results = check_legacy_files(tmp_path)

        assert len(results) == 1
        assert results[0].status == CheckStatus.OK

    def test_legacy_explorations_file(self, tmp_path):
        from idlergear.doctor import check_legacy_files, CheckStatus

        # Create project with legacy explorations.json
        idlergear_dir = tmp_path / ".idlergear"
        idlergear_dir.mkdir()
        legacy_file = idlergear_dir / "explorations.json"
        legacy_file.write_text("[]")

        results = check_legacy_files(tmp_path)

        assert len(results) == 1
        assert results[0].status == CheckStatus.WARNING
        assert "legacy" in results[0].message.lower()


class TestCheckUnmanagedKnowledgeFiles:
    """Tests for check_unmanaged_knowledge_files function."""

    def test_no_unmanaged_files(self, temp_project):
        from idlergear.doctor import check_unmanaged_knowledge_files, CheckStatus

        results = check_unmanaged_knowledge_files(temp_project)

        assert len(results) == 1
        assert results[0].status == CheckStatus.OK

    def test_todo_md_detected(self, temp_project):
        from idlergear.doctor import check_unmanaged_knowledge_files, CheckStatus

        # Create TODO.md
        (temp_project / "TODO.md").write_text("# TODOs\n- Task 1")

        results = check_unmanaged_knowledge_files(temp_project)

        assert len(results) == 1
        assert results[0].status == CheckStatus.INFO
        assert "TODO.md" in str(results[0].details)

    def test_multiple_unmanaged_files(self, temp_project):
        from idlergear.doctor import check_unmanaged_knowledge_files, CheckStatus

        # Create multiple unmanaged files
        (temp_project / "TODO.md").write_text("# TODOs")
        (temp_project / "NOTES.md").write_text("# Notes")
        (temp_project / "SCRATCH.md").write_text("# Scratch")

        results = check_unmanaged_knowledge_files(temp_project)

        assert len(results) == 1
        assert results[0].status == CheckStatus.INFO
        assert len(results[0].details["files"]) == 3


class TestRunDoctor:
    """Tests for run_doctor function."""

    def test_run_doctor_initialized_project(self, temp_project, monkeypatch):
        from idlergear.doctor import run_doctor
        from idlergear.upgrade import set_project_version

        monkeypatch.setattr("idlergear.doctor.__version__", "0.3.17")
        set_project_version("0.3.17")

        report = run_doctor(temp_project)

        assert report.project_path == temp_project
        assert report.installed_version == "0.3.17"
        assert len(report.checks) > 0

    def test_run_doctor_outside_project(self, tmp_path, monkeypatch):
        from idlergear.doctor import run_doctor, CheckStatus

        monkeypatch.chdir(tmp_path)

        report = run_doctor()

        assert report.project_path is None
        assert len(report.checks) == 1
        assert report.checks[0].status == CheckStatus.ERROR
        assert "not in" in report.checks[0].message.lower()

    def test_run_doctor_returns_all_checks(self, temp_project, monkeypatch):
        from idlergear.doctor import run_doctor
        from idlergear.upgrade import set_project_version

        monkeypatch.setattr("idlergear.doctor.__version__", "0.3.17")
        set_project_version("0.3.17")

        report = run_doctor(temp_project)

        # Should have multiple checks
        check_names = [c.name for c in report.checks]
        assert "initialization" in check_names
        assert "version" in check_names
        assert "mcp_config" in check_names


class TestFormatReport:
    """Tests for format_report function."""

    def test_format_healthy_report(self):
        from idlergear.doctor import (
            format_report,
            DoctorReport,
            CheckResult,
            CheckStatus,
        )

        report = DoctorReport(
            checks=[
                CheckResult("check1", CheckStatus.OK, "OK"),
            ],
            project_path=Path("/test"),
            installed_version="0.3.17",
            project_version="0.3.17",
        )

        output = format_report(report)

        assert "0.3.17" in output
        assert "All checks passed" in output

    def test_format_report_with_issues(self):
        from idlergear.doctor import (
            format_report,
            DoctorReport,
            CheckResult,
            CheckStatus,
        )

        report = DoctorReport(
            checks=[
                CheckResult("check1", CheckStatus.WARNING, "Warning msg", "fix cmd"),
            ],
            project_path=Path("/test"),
            installed_version="0.3.17",
            project_version="0.3.16",
        )

        output = format_report(report)

        assert "warning" in output.lower()
        assert "Warning msg" in output
        assert "fix cmd" in output

    def test_format_verbose_shows_ok_checks(self):
        from idlergear.doctor import (
            format_report,
            DoctorReport,
            CheckResult,
            CheckStatus,
        )

        report = DoctorReport(
            checks=[
                CheckResult("check1", CheckStatus.OK, "All good"),
            ],
            project_path=Path("/test"),
            installed_version="0.3.17",
            project_version="0.3.17",
        )

        # Non-verbose should not show OK checks in the detailed section
        # (but still shows overall summary)
        _ = format_report(report, verbose=False)  # Just verify no error

        # Verbose should show OK checks
        output_verbose = format_report(report, verbose=True)

        # OK checks shown in verbose mode
        assert "All good" in output_verbose


class TestCLIDoctor:
    """Tests for the doctor CLI command."""

    def test_doctor_command_exists(self, temp_project):
        """Test that doctor command is available."""
        from typer.testing import CliRunner
        from idlergear.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["doctor", "--help"])

        assert result.exit_code == 0
        assert "health" in result.output.lower()

    def test_doctor_json_output(self, tmp_path, monkeypatch):
        """Test doctor with JSON output."""
        from typer.testing import CliRunner
        from idlergear.cli import app
        import idlergear

        # Create a minimal project with correct version to prevent auto-upgrade
        current_version = idlergear.__version__
        idlergear_dir = tmp_path / ".idlergear"
        idlergear_dir.mkdir()
        (idlergear_dir / "config.json").write_text(
            json.dumps({"idlergear_version": current_version})
        )

        # Create .mcp.json with idlergear configured
        (tmp_path / ".mcp.json").write_text(
            json.dumps({"mcpServers": {"idlergear": {"command": "idlergear-mcp"}}})
        )

        # Create .claude/hooks.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "hooks.json").write_text(
            json.dumps({"hooks": {"PostToolUse": [{"command": "idlergear check"}]}})
        )

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(app, ["--output", "json", "doctor"])

        # Should be valid JSON (even if there are warnings)
        data = json.loads(result.output)
        assert "checks" in data
        assert "installed_version" in data


# =============================================================================
# Tests for Test Health Checks (Issues #156-159)
# =============================================================================


class TestCheckTestStaleness:
    """Tests for check_test_staleness function."""

    def test_no_framework_detected(self, tmp_path):
        from idlergear.doctor import check_test_staleness, CheckStatus

        # Empty project - no test framework
        (tmp_path / ".idlergear").mkdir()

        result = check_test_staleness(tmp_path)

        assert result.status == CheckStatus.INFO
        assert "no test framework" in result.message.lower()

    def test_never_run_tests(self, tmp_path):
        from idlergear.doctor import check_test_staleness, CheckStatus
        from unittest.mock import patch, MagicMock

        # Create pytest project
        (tmp_path / "pyproject.toml").write_text('[tool.pytest]\ntestpaths = ["tests"]')
        (tmp_path / ".idlergear").mkdir()

        # Mock detect_framework to return a valid config
        mock_config = MagicMock()
        mock_config.framework = "pytest"

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch(
                "idlergear.testing.get_test_staleness",
                return_value={"last_run": None, "seconds_ago": None},
            ):
                result = check_test_staleness(tmp_path)

        assert result.status == CheckStatus.WARNING
        assert "never been run" in result.message.lower()
        assert result.fix == "idlergear test run"

    def test_stale_tests_7_days(self, tmp_path):
        from idlergear.doctor import check_test_staleness, CheckStatus
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        # Tests run 10 days ago
        ten_days_seconds = 10 * 24 * 3600

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch(
                "idlergear.testing.get_test_staleness",
                return_value={
                    "last_run": "2026-01-01T10:00:00Z",
                    "seconds_ago": ten_days_seconds,
                },
            ):
                result = check_test_staleness(tmp_path)

        assert result.status == CheckStatus.WARNING
        assert "10 days" in result.message
        assert result.fix == "idlergear test run"

    def test_recent_tests(self, tmp_path):
        from idlergear.doctor import check_test_staleness, CheckStatus
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        # Tests run 1 hour ago
        one_hour_seconds = 3600

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch(
                "idlergear.testing.get_test_staleness",
                return_value={
                    "last_run": "2026-01-11T09:00:00Z",
                    "seconds_ago": one_hour_seconds,
                },
            ):
                result = check_test_staleness(tmp_path)

        assert result.status == CheckStatus.OK
        assert "recently" in result.message.lower()


class TestCheckTestFailures:
    """Tests for check_test_failures function."""

    def test_no_framework_detected(self, tmp_path):
        from idlergear.doctor import check_test_failures, CheckStatus

        (tmp_path / ".idlergear").mkdir()

        result = check_test_failures(tmp_path)

        assert result.status == CheckStatus.OK

    def test_no_results_recorded(self, tmp_path):
        from idlergear.doctor import check_test_failures, CheckStatus
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch("idlergear.testing.get_last_result", return_value=None):
                result = check_test_failures(tmp_path)

        assert result.status == CheckStatus.INFO
        assert "no test results" in result.message.lower()

    def test_failing_tests(self, tmp_path):
        from idlergear.doctor import check_test_failures, CheckStatus
        from idlergear.testing import TestResult
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        failing_result = TestResult(
            framework="pytest",
            timestamp="2026-01-11T10:00:00Z",
            duration_seconds=5.0,
            total=10,
            passed=7,
            failed=3,
            skipped=0,
            errors=0,
            failed_tests=["test_one", "test_two", "test_three"],
            command="pytest",
            exit_code=1,
        )

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch(
                "idlergear.testing.get_last_result", return_value=failing_result
            ):
                result = check_test_failures(tmp_path)

        assert result.status == CheckStatus.ERROR
        assert "3 failure" in result.message
        assert result.fix == "idlergear test run"
        assert "failed_tests" in result.details

    def test_passing_tests(self, tmp_path):
        from idlergear.doctor import check_test_failures, CheckStatus
        from idlergear.testing import TestResult
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        passing_result = TestResult(
            framework="pytest",
            timestamp="2026-01-11T10:00:00Z",
            duration_seconds=5.0,
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            errors=0,
            command="pytest",
            exit_code=0,
        )

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch(
                "idlergear.testing.get_last_result", return_value=passing_result
            ):
                result = check_test_failures(tmp_path)

        assert result.status == CheckStatus.OK
        assert "10 tests passing" in result.message


class TestCheckTestCoverageGaps:
    """Tests for check_test_coverage_gaps function."""

    def test_no_framework_detected(self, tmp_path):
        from idlergear.doctor import check_test_coverage_gaps, CheckStatus

        (tmp_path / ".idlergear").mkdir()

        result = check_test_coverage_gaps(tmp_path)

        assert result.status == CheckStatus.OK

    def test_all_files_covered(self, tmp_path):
        from idlergear.doctor import check_test_coverage_gaps, CheckStatus
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch("idlergear.testing.get_uncovered_files", return_value=[]):
                result = check_test_coverage_gaps(tmp_path)

        assert result.status == CheckStatus.OK
        assert "all source files have test coverage" in result.message.lower()

    def test_few_uncovered_files(self, tmp_path):
        from idlergear.doctor import check_test_coverage_gaps, CheckStatus
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch(
                "idlergear.testing.get_uncovered_files",
                return_value=["src/utils.py", "src/helpers.py"],
            ):
                result = check_test_coverage_gaps(tmp_path)

        assert result.status == CheckStatus.INFO
        assert "2 source file" in result.message

    def test_many_uncovered_files(self, tmp_path):
        from idlergear.doctor import check_test_coverage_gaps, CheckStatus
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        uncovered = [f"src/file{i}.py" for i in range(15)]

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch("idlergear.testing.get_uncovered_files", return_value=uncovered):
                result = check_test_coverage_gaps(tmp_path)

        assert result.status == CheckStatus.WARNING
        assert "15 source files" in result.message
        assert result.fix == "idlergear test uncovered"


class TestCheckExternalTestRuns:
    """Tests for check_external_test_runs function."""

    def test_no_framework_detected(self, tmp_path):
        from idlergear.doctor import check_external_test_runs, CheckStatus

        (tmp_path / ".idlergear").mkdir()

        result = check_external_test_runs(tmp_path)

        assert result.status == CheckStatus.OK

    def test_no_external_runs(self, tmp_path):
        from idlergear.doctor import check_external_test_runs, CheckStatus
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch("idlergear.testing.check_external_test_runs", return_value=[]):
                result = check_external_test_runs(tmp_path)

        assert result.status == CheckStatus.OK

    def test_external_runs_detected(self, tmp_path):
        from idlergear.doctor import check_external_test_runs, CheckStatus
        from idlergear.testing import ExternalTestRun
        from unittest.mock import patch, MagicMock

        (tmp_path / ".idlergear").mkdir()

        mock_config = MagicMock()
        mock_config.framework = "pytest"

        external_run = ExternalTestRun(
            framework="pytest",
            timestamp="2026-01-11T10:00:00",
            cache_path=".pytest_cache",
            estimated_tests=10,
            success=True,
        )

        with patch("idlergear.testing.detect_framework", return_value=mock_config):
            with patch(
                "idlergear.testing.check_external_test_runs",
                return_value=[external_run],
            ):
                result = check_external_test_runs(tmp_path)

        assert result.status == CheckStatus.INFO
        assert "1 external test run" in result.message
        assert result.fix == "idlergear test sync"


class TestRunDoctorWithTestChecks:
    """Test that run_doctor includes test health checks."""

    def test_doctor_includes_test_checks(self, temp_project, monkeypatch):
        from idlergear.doctor import run_doctor
        from idlergear.upgrade import set_project_version

        monkeypatch.setattr("idlergear.doctor.__version__", "0.3.17")
        set_project_version("0.3.17")

        report = run_doctor(temp_project)

        check_names = [c.name for c in report.checks]

        # Verify test health checks are included
        assert "test_staleness" in check_names
        assert "test_failures" in check_names
        assert "test_coverage" in check_names
        assert "external_tests" in check_names
