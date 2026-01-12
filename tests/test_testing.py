"""Tests for the testing module."""

import json
from unittest.mock import patch


from idlergear.testing import (
    TestFramework,
    TestResult,
    TestConfig,
    detect_framework,
    get_last_result,
    save_result,
    get_history,
    run_tests,
    format_status,
    _parse_pytest_output,
    _parse_cargo_output,
    _parse_dotnet_output,
    _parse_jest_output,
    _parse_go_output,
    _parse_generic_output,
)


class TestTestFramework:
    """Test TestFramework enum."""

    def test_framework_values(self):
        """Framework values are strings."""
        assert TestFramework.PYTEST.value == "pytest"
        assert TestFramework.CARGO.value == "cargo"
        assert TestFramework.DOTNET.value == "dotnet"
        assert TestFramework.JEST.value == "jest"
        assert TestFramework.VITEST.value == "vitest"
        assert TestFramework.GO.value == "go"
        assert TestFramework.RSPEC.value == "rspec"
        assert TestFramework.UNKNOWN.value == "unknown"


class TestTestResult:
    """Test TestResult dataclass."""

    def test_to_dict(self):
        """Convert TestResult to dictionary."""
        result = TestResult(
            framework="pytest",
            timestamp="2026-01-11T10:00:00Z",
            duration_seconds=5.5,
            total=10,
            passed=8,
            failed=1,
            skipped=1,
            errors=0,
            failed_tests=["test_foo::test_bar"],
            command="pytest",
            exit_code=1,
        )
        d = result.to_dict()
        assert d["framework"] == "pytest"
        assert d["total"] == 10
        assert d["passed"] == 8
        assert d["failed"] == 1
        assert d["failed_tests"] == ["test_foo::test_bar"]

    def test_from_dict(self):
        """Create TestResult from dictionary."""
        d = {
            "framework": "cargo",
            "timestamp": "2026-01-11T10:00:00Z",
            "duration_seconds": 3.2,
            "total": 5,
            "passed": 5,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "failed_tests": [],
            "command": "cargo test",
            "exit_code": 0,
        }
        result = TestResult.from_dict(d)
        assert result.framework == "cargo"
        assert result.passed == 5
        assert result.exit_code == 0

    def test_from_dict_defaults(self):
        """Handle missing keys with defaults."""
        result = TestResult.from_dict({})
        assert result.framework == "unknown"
        assert result.total == 0
        assert result.failed_tests == []


class TestTestConfig:
    """Test TestConfig dataclass."""

    def test_to_dict(self):
        """Convert TestConfig to dictionary."""
        config = TestConfig(
            framework="pytest",
            command="python -m pytest",
            test_dir="tests",
            test_pattern="test_*.py",
        )
        d = config.to_dict()
        assert d["framework"] == "pytest"
        assert d["command"] == "python -m pytest"
        assert d["test_dir"] == "tests"

    def test_from_dict(self):
        """Create TestConfig from dictionary."""
        d = {
            "framework": "jest",
            "command": "npm test",
            "test_dir": "__tests__",
            "test_pattern": "*.test.js",
        }
        config = TestConfig.from_dict(d)
        assert config.framework == "jest"
        assert config.command == "npm test"


class TestDetectFramework:
    """Test framework detection."""

    def test_detect_pytest_from_pyproject(self, tmp_path):
        """Detect pytest from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.pytest]\ntestpaths = ["tests"]')

        config = detect_framework(tmp_path)
        assert config.framework == "pytest"
        assert "pytest" in config.command

    def test_detect_pytest_from_conftest(self, tmp_path):
        """Detect pytest from conftest.py."""
        (tmp_path / "conftest.py").write_text("# pytest config")

        config = detect_framework(tmp_path)
        assert config.framework == "pytest"

    def test_detect_pytest_from_tests_dir(self, tmp_path):
        """Detect pytest from tests/conftest.py."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "conftest.py").write_text("# pytest config")

        config = detect_framework(tmp_path)
        assert config.framework == "pytest"
        assert config.test_dir == "tests"

    def test_detect_cargo(self, tmp_path):
        """Detect cargo test from Cargo.toml."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')

        config = detect_framework(tmp_path)
        assert config.framework == "cargo"
        assert config.command == "cargo test"

    def test_detect_dotnet(self, tmp_path):
        """Detect dotnet test from .csproj files."""
        (tmp_path / "MyApp.Tests.csproj").write_text("<Project />")

        config = detect_framework(tmp_path)
        assert config.framework == "dotnet"
        assert config.command == "dotnet test"

    def test_detect_jest(self, tmp_path):
        """Detect jest from package.json."""
        package = tmp_path / "package.json"
        package.write_text('{"devDependencies": {"jest": "^29.0.0"}}')

        config = detect_framework(tmp_path)
        assert config.framework == "jest"
        assert "jest" in config.command

    def test_detect_vitest(self, tmp_path):
        """Detect vitest from package.json (preferred over jest)."""
        package = tmp_path / "package.json"
        package.write_text(
            '{"devDependencies": {"vitest": "^1.0.0", "jest": "^29.0.0"}}'
        )

        config = detect_framework(tmp_path)
        assert config.framework == "vitest"

    def test_detect_go(self, tmp_path):
        """Detect go test from go.mod and test files."""
        (tmp_path / "go.mod").write_text("module example.com/test")
        (tmp_path / "main_test.go").write_text("package main")

        config = detect_framework(tmp_path)
        assert config.framework == "go"
        assert "go test" in config.command

    def test_detect_rspec(self, tmp_path):
        """Detect rspec from spec directory."""
        (tmp_path / "spec").mkdir()

        config = detect_framework(tmp_path)
        assert config.framework == "rspec"

    def test_detect_unknown(self, tmp_path):
        """Return None for unknown projects."""
        config = detect_framework(tmp_path)
        assert config is None


class TestResultPersistence:
    """Test result saving and loading."""

    def test_save_and_get_result(self, tmp_path):
        """Save and retrieve test result."""
        # Create .idlergear directory structure
        ig_dir = tmp_path / ".idlergear"
        ig_dir.mkdir()

        result = TestResult(
            framework="pytest",
            timestamp="2026-01-11T10:00:00Z",
            duration_seconds=5.5,
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            errors=0,
            command="pytest",
            exit_code=0,
        )

        with patch("idlergear.testing.get_tests_dir") as mock_dir:
            mock_dir.return_value = tmp_path / ".idlergear" / "tests"
            save_result(result, tmp_path)

            loaded = get_last_result(tmp_path)
            assert loaded is not None
            assert loaded.framework == "pytest"
            assert loaded.passed == 10

    def test_get_history(self, tmp_path):
        """Get test run history."""
        ig_dir = tmp_path / ".idlergear" / "tests" / "history"
        ig_dir.mkdir(parents=True)

        # Create some history files
        for i in range(5):
            result = TestResult(
                framework="pytest",
                timestamp=f"2026-01-1{i}T10:00:00Z",
                duration_seconds=i + 1.0,
                total=10,
                passed=10 - i,
                failed=i,
                skipped=0,
                errors=0,
                command="pytest",
                exit_code=0 if i == 0 else 1,
            )
            file = ig_dir / f"2026-01-1{i}T10-00-00Z.json"
            file.write_text(json.dumps(result.to_dict()))

        with patch("idlergear.testing.get_tests_dir") as mock_dir:
            mock_dir.return_value = tmp_path / ".idlergear" / "tests"
            history = get_history(tmp_path, limit=3)

            assert len(history) == 3
            # Should be newest first
            assert history[0].timestamp > history[1].timestamp


class TestOutputParsing:
    """Test test output parsing."""

    def test_parse_pytest_passed(self):
        """Parse pytest output with all passing."""
        output = """
============================= test session starts ==============================
collected 42 items

tests/test_foo.py ...........                                       [ 26%]
tests/test_bar.py ...............................                   [100%]

============================== 42 passed in 5.23s ==============================
"""
        result = _parse_pytest_output(output, "pytest", 5.23, 0)
        assert result.passed == 42
        assert result.failed == 0
        assert result.total == 42

    def test_parse_pytest_mixed(self):
        """Parse pytest output with mixed results."""
        output = """
============================= test session starts ==============================
collected 10 items

tests/test_foo.py ....F..                                           [ 70%]
tests/test_bar.py ..s                                               [100%]

FAILED tests/test_foo.py::test_bad - AssertionError
=========================== 7 passed, 1 failed, 1 skipped in 2.11s ===========================
"""
        result = _parse_pytest_output(output, "pytest", 2.11, 1)
        assert result.passed == 7
        assert result.failed == 1
        assert result.skipped == 1
        assert "tests/test_foo.py::test_bad" in result.failed_tests

    def test_parse_cargo_passed(self):
        """Parse cargo test output with all passing."""
        output = """
   Compiling myapp v0.1.0
    Finished test target(s) in 2.34s
     Running unittests src/lib.rs

running 5 tests
test tests::test_one ... ok
test tests::test_two ... ok
test tests::test_three ... ok
test tests::test_four ... ok
test tests::test_five ... ok

test result: ok. 5 passed; 0 failed; 0 ignored
"""
        result = _parse_cargo_output(output, "cargo test", 2.34, 0)
        assert result.passed == 5
        assert result.failed == 0

    def test_parse_cargo_failed(self):
        """Parse cargo test output with failures."""
        output = """
running 3 tests
test tests::test_one ... ok
test tests::test_bad ... FAILED
test tests::test_two ... ok

---- tests::test_bad stdout ----
thread 'tests::test_bad' panicked at 'assertion failed'

test result: FAILED. 2 passed; 1 failed; 0 ignored
"""
        result = _parse_cargo_output(output, "cargo test", 1.5, 1)
        assert result.passed == 2
        assert result.failed == 1
        assert "tests::test_bad" in result.failed_tests

    def test_parse_dotnet_passed(self):
        """Parse dotnet test output."""
        output = """
  Determining projects to restore...
  All projects are up-to-date for restore.
  MyApp.Tests -> /app/bin/Debug/net8.0/MyApp.Tests.dll

Test Run Successful.
Total tests: 15
     Passed: 15
     Failed: 0
    Skipped: 0
"""
        result = _parse_dotnet_output(output, "dotnet test", 3.5, 0)
        assert result.passed == 15
        assert result.failed == 0

    def test_parse_jest_passed(self):
        """Parse jest output."""
        output = """
 PASS  src/components/Button.test.js
 PASS  src/utils/helpers.test.js

Test Suites: 2 passed, 2 total
Tests:       8 passed, 8 total
Snapshots:   0 total
Time:        1.234 s
"""
        result = _parse_jest_output(output, "npm test", 1.234, 0)
        assert result.passed == 8
        assert result.failed == 0

    def test_parse_go_passed(self):
        """Parse go test output."""
        output = """
=== RUN   TestAdd
--- PASS: TestAdd (0.00s)
=== RUN   TestSubtract
--- PASS: TestSubtract (0.00s)
=== RUN   TestMultiply
--- PASS: TestMultiply (0.00s)
PASS
ok      example.com/math    0.005s
"""
        result = _parse_go_output(output, "go test ./...", 0.005, 0)
        assert result.passed == 3
        assert result.failed == 0

    def test_parse_go_failed(self):
        """Parse go test output with failures."""
        output = """
=== RUN   TestAdd
--- PASS: TestAdd (0.00s)
=== RUN   TestBad
--- FAIL: TestBad (0.00s)
    main_test.go:15: expected 5, got 4
FAIL
exit status 1
"""
        result = _parse_go_output(output, "go test ./...", 0.01, 1)
        assert result.passed == 1
        assert result.failed == 1
        assert "TestBad" in result.failed_tests

    def test_parse_generic_passed(self):
        """Parse generic output with common patterns."""
        # Generic parser looks for patterns like "10 passed" not "10 tests passed"
        output = """
Running tests...
10 passed, 0 failed
Done.
"""
        result = _parse_generic_output("unknown", output, "run tests", 1.0, 0)
        assert result.passed == 10
        assert result.failed == 0

    def test_parse_generic_infer_from_exit_code(self):
        """Infer result from exit code when output is unparseable."""
        result = _parse_generic_output(
            "unknown", "No recognizable output", "test", 1.0, 0
        )
        assert result.passed == 1
        assert result.total == 1

        result = _parse_generic_output(
            "unknown", "No recognizable output", "test", 1.0, 1
        )
        assert result.failed == 1


class TestFormatStatus:
    """Test status formatting."""

    def test_format_passed(self):
        """Format passing test result."""
        result = TestResult(
            framework="pytest",
            timestamp="2026-01-11T10:00:00Z",
            duration_seconds=5.5,
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            errors=0,
            command="pytest",
            exit_code=0,
        )
        output = format_status(result)
        assert "PASSED" in output
        assert "pytest" in output
        assert "10 passed" in output

    def test_format_failed(self):
        """Format failing test result."""
        result = TestResult(
            framework="pytest",
            timestamp="2026-01-11T10:00:00Z",
            duration_seconds=5.5,
            total=10,
            passed=8,
            failed=2,
            skipped=0,
            errors=0,
            failed_tests=["test_one", "test_two"],
            command="pytest",
            exit_code=1,
        )
        output = format_status(result)
        assert "FAILED" in output
        assert "8 passed" in output
        assert "2 failed" in output

    def test_format_verbose_shows_failed_tests(self):
        """Verbose format shows failed test names."""
        result = TestResult(
            framework="pytest",
            timestamp="2026-01-11T10:00:00Z",
            duration_seconds=5.5,
            total=3,
            passed=1,
            failed=2,
            skipped=0,
            errors=0,
            failed_tests=["test_one", "test_two"],
            command="pytest",
            exit_code=1,
        )
        output = format_status(result, verbose=True)
        assert "Failed tests:" in output
        assert "test_one" in output
        assert "test_two" in output

    def test_format_none(self):
        """Format when no result exists."""
        output = format_status(None)
        assert "No test runs" in output


class TestRunTests:
    """Test running tests."""

    def test_run_tests_success(self, tmp_path):
        """Run tests successfully."""
        # Create pytest project
        (tmp_path / "pyproject.toml").write_text('[tool.pytest]\ntestpaths = ["tests"]')
        (tmp_path / ".idlergear").mkdir()

        config = TestConfig(
            framework="pytest",
            command="echo '1 passed in 0.01s'",
            test_dir="tests",
            test_pattern="test_*.py",
        )

        with patch("idlergear.testing.get_tests_dir") as mock_dir:
            mock_dir.return_value = tmp_path / ".idlergear" / "tests"
            result, output = run_tests(tmp_path, config)

            assert result.exit_code == 0
            assert "passed" in output

    def test_run_tests_with_extra_args(self, tmp_path):
        """Run tests with extra arguments."""
        (tmp_path / ".idlergear").mkdir()

        config = TestConfig(
            framework="pytest",
            command="echo",
            test_dir="tests",
            test_pattern="test_*.py",
        )

        with patch("idlergear.testing.get_tests_dir") as mock_dir:
            mock_dir.return_value = tmp_path / ".idlergear" / "tests"
            result, output = run_tests(tmp_path, config, extra_args="-k foo")

            assert "-k foo" in output

    def test_run_tests_no_framework(self, tmp_path):
        """Handle missing framework gracefully."""
        result, output = run_tests(tmp_path, config=None)
        assert result.errors == 1
        assert "No test framework" in result.failed_tests[0]


# =============================================================================
# External Test Detection Tests (#136)
# =============================================================================


class TestExternalTestRun:
    """Test ExternalTestRun dataclass."""

    def test_to_dict(self):
        """Convert to dictionary."""
        from idlergear.testing import ExternalTestRun

        run = ExternalTestRun(
            framework="pytest",
            timestamp="2024-01-01T12:00:00",
            cache_path=".pytest_cache",
            estimated_tests=10,
            success=True,
        )

        data = run.to_dict()
        assert data["framework"] == "pytest"
        assert data["timestamp"] == "2024-01-01T12:00:00"
        assert data["cache_path"] == ".pytest_cache"
        assert data["estimated_tests"] == 10
        assert data["success"] is True

    def test_success_unknown(self):
        """Handle unknown success status."""
        from idlergear.testing import ExternalTestRun

        run = ExternalTestRun(
            framework="cargo",
            timestamp="2024-01-01T12:00:00",
            cache_path="target",
        )

        data = run.to_dict()
        assert data["success"] is None


class TestGetCachePaths:
    """Test cache path detection."""

    def test_pytest_cache_paths(self, tmp_path):
        """Get pytest cache paths."""
        from idlergear.testing import get_cache_paths, TestFramework

        # Create some cache directories
        (tmp_path / ".pytest_cache").mkdir()
        (tmp_path / ".coverage").touch()

        paths = get_cache_paths(tmp_path, TestFramework.PYTEST.value)
        assert len(paths) >= 2
        assert tmp_path / ".pytest_cache" in paths
        assert tmp_path / ".coverage" in paths

    def test_jest_cache_paths(self, tmp_path):
        """Get jest cache paths."""
        from idlergear.testing import get_cache_paths, TestFramework

        # Create cache directory
        jest_cache = tmp_path / "node_modules" / ".cache" / "jest"
        jest_cache.mkdir(parents=True)

        paths = get_cache_paths(tmp_path, TestFramework.JEST.value)
        assert jest_cache in paths

    def test_no_cache_paths(self, tmp_path):
        """Handle missing cache directories."""
        from idlergear.testing import get_cache_paths, TestFramework

        paths = get_cache_paths(tmp_path, TestFramework.PYTEST.value)
        assert paths == []


class TestGetCacheMtime:
    """Test cache modification time detection."""

    def test_file_mtime(self, tmp_path):
        """Get mtime for a file."""
        from idlergear.testing import get_cache_mtime

        test_file = tmp_path / "test.txt"
        test_file.touch()

        mtime = get_cache_mtime(test_file)
        assert mtime is not None
        assert mtime > 0

    def test_dir_mtime(self, tmp_path):
        """Get latest mtime in a directory."""
        from idlergear.testing import get_cache_mtime
        import time

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Create files with different times
        (cache_dir / "old.txt").touch()
        time.sleep(0.1)
        (cache_dir / "new.txt").touch()

        mtime = get_cache_mtime(cache_dir)
        assert mtime is not None
        # Should be the most recent file
        new_file_mtime = (cache_dir / "new.txt").stat().st_mtime
        assert abs(mtime - new_file_mtime) < 1

    def test_nonexistent_path(self, tmp_path):
        """Handle nonexistent paths."""
        from idlergear.testing import get_cache_mtime

        mtime = get_cache_mtime(tmp_path / "nonexistent")
        assert mtime is None


class TestCheckExternalTestRuns:
    """Test external test run detection."""

    def test_no_framework(self, tmp_path):
        """Handle project without test framework."""
        from idlergear.testing import check_external_test_runs

        runs = check_external_test_runs(tmp_path)
        assert runs == []

    def test_no_cache(self, tmp_path):
        """Handle project without cache files."""
        from idlergear.testing import check_external_test_runs

        (tmp_path / "pyproject.toml").write_text("[tool.pytest]\n")

        runs = check_external_test_runs(tmp_path)
        assert runs == []

    def test_cache_older_than_last_run(self, tmp_path):
        """Cache older than last run is not detected."""
        from idlergear.testing import (
            check_external_test_runs,
            save_result,
            TestResult,
        )
        import time

        # Set up project
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]\n")
        (tmp_path / ".idlergear").mkdir()
        (tmp_path / ".idlergear" / "tests").mkdir()

        # Create old cache
        cache = tmp_path / ".pytest_cache"
        cache.mkdir()
        (cache / "v" / "cache").mkdir(parents=True)
        (cache / "v" / "cache" / "lastfailed").write_text("{}")

        time.sleep(0.1)

        # Save a recent result
        result = TestResult(
            framework="pytest",
            timestamp="2099-01-01T00:00:00Z",  # Far future
            duration_seconds=1,
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            errors=0,
        )
        save_result(result, tmp_path)

        with patch("idlergear.testing.find_idlergear_root") as mock_root:
            mock_root.return_value = tmp_path
            runs = check_external_test_runs(tmp_path)
            # Cache is older, so no external runs detected
            assert runs == []


class TestParsePytestCache:
    """Test pytest cache parsing."""

    def test_parse_success(self, tmp_path):
        """Parse successful test run cache."""
        from idlergear.testing import _parse_pytest_cache

        cache = tmp_path / ".pytest_cache"
        (cache / "v" / "cache").mkdir(parents=True)
        (cache / "v" / "cache" / "lastfailed").write_text("{}")
        (cache / "v" / "cache" / "nodeids").write_text('["test_a", "test_b", "test_c"]')

        count, success = _parse_pytest_cache(cache)
        assert count == 3
        assert success is True

    def test_parse_failure(self, tmp_path):
        """Parse failed test run cache."""
        from idlergear.testing import _parse_pytest_cache

        cache = tmp_path / ".pytest_cache"
        (cache / "v" / "cache").mkdir(parents=True)
        (cache / "v" / "cache" / "lastfailed").write_text(
            '{"test_foo::test_bar": true}'
        )
        (cache / "v" / "cache" / "nodeids").write_text('["test_a", "test_b"]')

        count, success = _parse_pytest_cache(cache)
        assert count == 2  # max of nodeids (2) vs failed (1)
        assert success is False

    def test_parse_empty_cache(self, tmp_path):
        """Parse empty cache directory."""
        from idlergear.testing import _parse_pytest_cache

        cache = tmp_path / ".pytest_cache"
        cache.mkdir()

        count, success = _parse_pytest_cache(cache)
        assert count == 0
        assert success is None


class TestGetTestStaleness:
    """Test staleness detection."""

    def test_no_last_run(self, tmp_path):
        """Handle no previous test runs."""
        from idlergear.testing import get_test_staleness

        with patch("idlergear.testing.find_idlergear_root") as mock_root:
            mock_root.return_value = tmp_path
            staleness = get_test_staleness(tmp_path)

        assert staleness["last_run"] is None
        assert staleness["seconds_ago"] is None
        assert staleness["external_detected"] is False

    def test_with_last_run(self, tmp_path):
        """Include last run info."""
        from idlergear.testing import get_test_staleness, save_result, TestResult
        from datetime import datetime, timezone

        (tmp_path / ".idlergear" / "tests").mkdir(parents=True)

        # Save a result
        now = datetime.now(timezone.utc)
        result = TestResult(
            framework="pytest",
            timestamp=now.isoformat(),
            duration_seconds=1,
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            errors=0,
        )
        save_result(result, tmp_path)

        with patch("idlergear.testing.find_idlergear_root") as mock_root:
            mock_root.return_value = tmp_path
            staleness = get_test_staleness(tmp_path)

        assert staleness["last_run"] == now.isoformat()
        assert staleness["seconds_ago"] is not None
        assert staleness["seconds_ago"] < 10  # Should be very recent


class TestSyncExternalRuns:
    """Test syncing external runs."""

    def test_no_external_runs(self, tmp_path):
        """Handle no external runs."""
        from idlergear.testing import sync_external_runs

        with patch("idlergear.testing.check_external_test_runs") as mock_check:
            mock_check.return_value = []
            imported = sync_external_runs(tmp_path)

        assert imported == []

    def test_import_external_run(self, tmp_path):
        """Import an external run."""
        from idlergear.testing import (
            sync_external_runs,
            ExternalTestRun,
        )

        (tmp_path / ".idlergear" / "tests").mkdir(parents=True)

        # Create cache with test info
        cache = tmp_path / ".pytest_cache"
        (cache / "v" / "cache").mkdir(parents=True)
        (cache / "v" / "cache" / "lastfailed").write_text("{}")
        (cache / "v" / "cache" / "nodeids").write_text('["test_a", "test_b"]')

        external = ExternalTestRun(
            framework="pytest",
            timestamp="2024-01-01T12:00:00",
            cache_path=".pytest_cache",
            estimated_tests=2,
            success=True,
        )

        with patch("idlergear.testing.check_external_test_runs") as mock_check:
            mock_check.return_value = [external]
            with patch("idlergear.testing.find_idlergear_root") as mock_root:
                mock_root.return_value = tmp_path
                imported = sync_external_runs(tmp_path)

        assert len(imported) == 1
        assert imported[0].passed == 2
        assert imported[0].failed == 0
