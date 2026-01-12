"""Test framework detection and result tracking for IdlerGear."""

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.storage import now_iso


class TestFramework(str, Enum):
    """Supported test frameworks."""

    PYTEST = "pytest"
    CARGO = "cargo"
    DOTNET = "dotnet"
    JEST = "jest"
    VITEST = "vitest"
    GO = "go"
    RSPEC = "rspec"
    UNKNOWN = "unknown"


@dataclass
class TestResult:
    """Result of a test run."""

    framework: str
    timestamp: str
    duration_seconds: float
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    failed_tests: list[str] = field(default_factory=list)
    command: str = ""
    exit_code: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "framework": self.framework,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "failed_tests": self.failed_tests,
            "command": self.command,
            "exit_code": self.exit_code,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestResult":
        """Create from dictionary."""
        return cls(
            framework=data.get("framework", "unknown"),
            timestamp=data.get("timestamp", ""),
            duration_seconds=data.get("duration_seconds", 0),
            total=data.get("total", 0),
            passed=data.get("passed", 0),
            failed=data.get("failed", 0),
            skipped=data.get("skipped", 0),
            errors=data.get("errors", 0),
            failed_tests=data.get("failed_tests", []),
            command=data.get("command", ""),
            exit_code=data.get("exit_code", 0),
        )


@dataclass
class TestConfig:
    """Test configuration for a project."""

    framework: str
    command: str
    test_dir: str = ""
    test_pattern: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "framework": self.framework,
            "command": self.command,
            "test_dir": self.test_dir,
            "test_pattern": self.test_pattern,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestConfig":
        """Create from dictionary."""
        return cls(
            framework=data.get("framework", "unknown"),
            command=data.get("command", ""),
            test_dir=data.get("test_dir", ""),
            test_pattern=data.get("test_pattern", ""),
        )


def get_tests_dir(project_path: Path | None = None) -> Path | None:
    """Get the .idlergear/tests directory."""
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None
    return project_path / ".idlergear" / "tests"


def detect_framework(project_path: Path | None = None) -> TestConfig | None:
    """Detect the test framework used in a project.

    Returns TestConfig with framework and suggested command, or None if not detected.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    # Check for Python (pytest)
    if _has_pytest(project_path):
        test_dir = _find_test_dir(project_path, ["tests", "test"])
        return TestConfig(
            framework=TestFramework.PYTEST.value,
            command="python -m pytest",
            test_dir=test_dir,
            test_pattern="test_*.py",
        )

    # Check for Rust (cargo)
    if (project_path / "Cargo.toml").exists():
        return TestConfig(
            framework=TestFramework.CARGO.value,
            command="cargo test",
            test_dir="src",
            test_pattern="*_test.rs",
        )

    # Check for .NET (dotnet test)
    if _has_dotnet_tests(project_path):
        return TestConfig(
            framework=TestFramework.DOTNET.value,
            command="dotnet test",
            test_dir="",
            test_pattern="*Tests.cs",
        )

    # Check for JavaScript (jest/vitest)
    js_config = _detect_js_framework(project_path)
    if js_config:
        return js_config

    # Check for Go
    if _has_go_tests(project_path):
        return TestConfig(
            framework=TestFramework.GO.value,
            command="go test ./...",
            test_dir="",
            test_pattern="*_test.go",
        )

    # Check for Ruby (rspec)
    if (project_path / "spec").is_dir() or (project_path / ".rspec").exists():
        return TestConfig(
            framework=TestFramework.RSPEC.value,
            command="rspec",
            test_dir="spec",
            test_pattern="*_spec.rb",
        )

    return None


def _has_pytest(project_path: Path) -> bool:
    """Check if project uses pytest."""
    # Check pyproject.toml
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        if "pytest" in content:
            return True

    # Check for pytest.ini or conftest.py
    if (project_path / "pytest.ini").exists():
        return True
    if (project_path / "conftest.py").exists():
        return True
    if (project_path / "tests" / "conftest.py").exists():
        return True

    # Check requirements
    for req_file in [
        "requirements.txt",
        "requirements-dev.txt",
        "dev-requirements.txt",
    ]:
        req_path = project_path / req_file
        if req_path.exists() and "pytest" in req_path.read_text():
            return True

    return False


def _has_dotnet_tests(project_path: Path) -> bool:
    """Check if project has .NET test projects."""
    # Look for *.Tests.csproj or *.Test.csproj
    for pattern in ["*.Tests.csproj", "*.Test.csproj", "*Tests.csproj"]:
        if list(project_path.rglob(pattern)):
            return True

    # Check for test in solution
    sln_files = list(project_path.glob("*.sln"))
    if sln_files:
        for sln in sln_files:
            content = sln.read_text()
            if "Test" in content:
                return True

    return False


def _detect_js_framework(project_path: Path) -> TestConfig | None:
    """Detect JavaScript test framework."""
    package_json = project_path / "package.json"
    if not package_json.exists():
        return None

    try:
        pkg = json.loads(package_json.read_text())
    except json.JSONDecodeError:
        return None

    deps = {
        **pkg.get("dependencies", {}),
        **pkg.get("devDependencies", {}),
    }

    # Check for vitest first (modern)
    if "vitest" in deps:
        return TestConfig(
            framework=TestFramework.VITEST.value,
            command="npx vitest run",
            test_dir="",
            test_pattern="*.test.{js,ts}",
        )

    # Check for jest
    if "jest" in deps:
        return TestConfig(
            framework=TestFramework.JEST.value,
            command="npx jest",
            test_dir="",
            test_pattern="*.test.{js,ts}",
        )

    # Check scripts for test command
    scripts = pkg.get("scripts", {})
    if "test" in scripts:
        test_script = scripts["test"]
        if "vitest" in test_script:
            return TestConfig(
                framework=TestFramework.VITEST.value,
                command="npm test",
                test_dir="",
                test_pattern="*.test.{js,ts}",
            )
        if "jest" in test_script:
            return TestConfig(
                framework=TestFramework.JEST.value,
                command="npm test",
                test_dir="",
                test_pattern="*.test.{js,ts}",
            )

    return None


def _has_go_tests(project_path: Path) -> bool:
    """Check if project has Go tests."""
    if not (project_path / "go.mod").exists():
        return False

    # Look for *_test.go files
    return bool(list(project_path.rglob("*_test.go")))


def _find_test_dir(project_path: Path, candidates: list[str]) -> str:
    """Find the test directory from candidates."""
    for candidate in candidates:
        if (project_path / candidate).is_dir():
            return candidate
    return ""


def get_test_config(project_path: Path | None = None) -> TestConfig | None:
    """Get cached test config or detect it."""
    tests_dir = get_tests_dir(project_path)
    if tests_dir is None:
        return detect_framework(project_path)

    config_file = tests_dir / "config.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text())
            return TestConfig.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    # Detect and cache
    config = detect_framework(project_path)
    if config:
        save_test_config(config, project_path)
    return config


def save_test_config(config: TestConfig, project_path: Path | None = None) -> None:
    """Save test configuration."""
    tests_dir = get_tests_dir(project_path)
    if tests_dir is None:
        return

    tests_dir.mkdir(parents=True, exist_ok=True)
    config_file = tests_dir / "config.json"
    config_file.write_text(json.dumps(config.to_dict(), indent=2) + "\n")


def get_last_result(project_path: Path | None = None) -> TestResult | None:
    """Get the last test run result."""
    tests_dir = get_tests_dir(project_path)
    if tests_dir is None:
        return None

    result_file = tests_dir / "last-run.json"
    if not result_file.exists():
        return None

    try:
        data = json.loads(result_file.read_text())
        return TestResult.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None


def save_result(result: TestResult, project_path: Path | None = None) -> None:
    """Save test run result."""
    tests_dir = get_tests_dir(project_path)
    if tests_dir is None:
        return

    tests_dir.mkdir(parents=True, exist_ok=True)

    # Save as last run
    result_file = tests_dir / "last-run.json"
    result_file.write_text(json.dumps(result.to_dict(), indent=2) + "\n")

    # Also save to history
    history_dir = tests_dir / "history"
    history_dir.mkdir(exist_ok=True)

    # Use timestamp for history filename
    timestamp = result.timestamp.replace(":", "-").replace(".", "-")
    history_file = history_dir / f"{timestamp}.json"
    history_file.write_text(json.dumps(result.to_dict(), indent=2) + "\n")

    # Keep only last 10 history entries
    history_files = sorted(history_dir.glob("*.json"), reverse=True)
    for old_file in history_files[10:]:
        old_file.unlink()


def get_history(project_path: Path | None = None, limit: int = 10) -> list[TestResult]:
    """Get test run history.

    Args:
        project_path: Project root path
        limit: Maximum number of results to return

    Returns:
        List of TestResult objects, newest first
    """
    tests_dir = get_tests_dir(project_path)
    if tests_dir is None:
        return []

    history_dir = tests_dir / "history"
    if not history_dir.exists():
        return []

    results = []
    history_files = sorted(history_dir.glob("*.json"), reverse=True)

    for history_file in history_files[:limit]:
        try:
            data = json.loads(history_file.read_text())
            results.append(TestResult.from_dict(data))
        except (json.JSONDecodeError, KeyError):
            continue

    return results


def run_tests(
    project_path: Path | None = None,
    config: TestConfig | None = None,
    extra_args: str | None = None,
) -> tuple[TestResult, str]:
    """Run tests and return parsed results.

    Args:
        project_path: Project root path
        config: Test configuration (uses detected if None)
        extra_args: Additional arguments to pass to test command as string

    Returns:
        Tuple of (TestResult, output string)
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    if config is None:
        config = get_test_config(project_path)
    if config is None:
        result = TestResult(
            framework="unknown",
            timestamp=now_iso(),
            duration_seconds=0,
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            failed_tests=["No test framework detected"],
            command="",
            exit_code=1,
        )
        return result, ""

    test_command = config.command
    if extra_args:
        test_command = f"{test_command} {extra_args}"

    framework = config.framework

    # Run the tests
    start_time = time.time()
    try:
        proc = subprocess.run(
            test_command,
            shell=True,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
        output = proc.stdout + proc.stderr
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        result = TestResult(
            framework=framework,
            timestamp=now_iso(),
            duration_seconds=600,
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            failed_tests=["Test run timed out after 10 minutes"],
            command=test_command,
            exit_code=124,
        )
        return result, "Test run timed out after 10 minutes"
    except Exception as e:
        result = TestResult(
            framework=framework,
            timestamp=now_iso(),
            duration_seconds=0,
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            failed_tests=[str(e)],
            command=test_command,
            exit_code=1,
        )
        return result, str(e)

    duration = time.time() - start_time

    # Parse output based on framework
    result = _parse_test_output(framework, output, test_command, duration, exit_code)

    # Save result
    save_result(result, project_path)

    return result, output


def _parse_test_output(
    framework: str,
    output: str,
    command: str,
    duration: float,
    exit_code: int,
) -> TestResult:
    """Parse test output based on framework."""
    if framework == TestFramework.PYTEST.value:
        return _parse_pytest_output(output, command, duration, exit_code)
    elif framework == TestFramework.CARGO.value:
        return _parse_cargo_output(output, command, duration, exit_code)
    elif framework == TestFramework.DOTNET.value:
        return _parse_dotnet_output(output, command, duration, exit_code)
    elif framework == TestFramework.JEST.value:
        return _parse_jest_output(output, command, duration, exit_code)
    elif framework == TestFramework.GO.value:
        return _parse_go_output(output, command, duration, exit_code)
    else:
        # Generic parsing - try to find common patterns
        return _parse_generic_output(framework, output, command, duration, exit_code)


def _parse_pytest_output(
    output: str, command: str, duration: float, exit_code: int
) -> TestResult:
    """Parse pytest output."""
    # Look for summary line like "759 passed in 245.11s"
    # or "10 passed, 2 failed, 1 skipped in 5.23s"
    passed = 0
    failed = 0
    skipped = 0
    errors = 0
    failed_tests = []

    # Parse summary line
    summary_pattern = r"=+ (.*?) =+"
    for match in re.finditer(summary_pattern, output):
        summary = match.group(1)

        # Extract counts
        passed_match = re.search(r"(\d+) passed", summary)
        if passed_match:
            passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+) failed", summary)
        if failed_match:
            failed = int(failed_match.group(1))

        skipped_match = re.search(r"(\d+) skipped", summary)
        if skipped_match:
            skipped = int(skipped_match.group(1))

        error_match = re.search(r"(\d+) error", summary)
        if error_match:
            errors = int(error_match.group(1))

    # Extract failed test names
    # Look for "FAILED tests/test_foo.py::test_bar"
    for match in re.finditer(r"FAILED\s+(\S+)", output):
        failed_tests.append(match.group(1))

    total = passed + failed + skipped + errors

    return TestResult(
        framework=TestFramework.PYTEST.value,
        timestamp=now_iso(),
        duration_seconds=round(duration, 2),
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        failed_tests=failed_tests,
        command=command,
        exit_code=exit_code,
    )


def _parse_cargo_output(
    output: str, command: str, duration: float, exit_code: int
) -> TestResult:
    """Parse cargo test output."""
    passed = 0
    failed = 0
    skipped = 0
    failed_tests = []

    # Look for "test result: ok. X passed; Y failed; Z ignored"
    result_pattern = r"test result: \w+\. (\d+) passed; (\d+) failed; (\d+) ignored"
    match = re.search(result_pattern, output)
    if match:
        passed = int(match.group(1))
        failed = int(match.group(2))
        skipped = int(match.group(3))

    # Extract failed test names
    for match in re.finditer(r"---- (\S+) stdout ----", output):
        if "FAILED" in output[match.end() : match.end() + 500]:
            failed_tests.append(match.group(1))

    # Also check for "test ... FAILED" lines
    for match in re.finditer(r"test (\S+) \.\.\. FAILED", output):
        test_name = match.group(1)
        if test_name not in failed_tests:
            failed_tests.append(test_name)

    total = passed + failed + skipped

    return TestResult(
        framework=TestFramework.CARGO.value,
        timestamp=now_iso(),
        duration_seconds=round(duration, 2),
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=0,
        failed_tests=failed_tests,
        command=command,
        exit_code=exit_code,
    )


def _parse_dotnet_output(
    output: str, command: str, duration: float, exit_code: int
) -> TestResult:
    """Parse dotnet test output."""
    passed = 0
    failed = 0
    skipped = 0
    failed_tests = []

    # Look for "Passed: X, Failed: Y, Skipped: Z"
    # or "Total tests: X. Passed: Y. Failed: Z. Skipped: W."
    passed_match = re.search(r"Passed[:\s]+(\d+)", output)
    if passed_match:
        passed = int(passed_match.group(1))

    failed_match = re.search(r"Failed[:\s]+(\d+)", output)
    if failed_match:
        failed = int(failed_match.group(1))

    skipped_match = re.search(r"Skipped[:\s]+(\d+)", output)
    if skipped_match:
        skipped = int(skipped_match.group(1))

    # Extract failed test names
    for match in re.finditer(r"Failed\s+(\S+)", output):
        test_name = match.group(1)
        if test_name not in [":", "tests", "tests."]:
            failed_tests.append(test_name)

    total = passed + failed + skipped

    return TestResult(
        framework=TestFramework.DOTNET.value,
        timestamp=now_iso(),
        duration_seconds=round(duration, 2),
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=0,
        failed_tests=failed_tests,
        command=command,
        exit_code=exit_code,
    )


def _parse_jest_output(
    output: str, command: str, duration: float, exit_code: int
) -> TestResult:
    """Parse jest/vitest output."""
    passed = 0
    failed = 0
    skipped = 0
    failed_tests = []

    # Look for "Tests: X passed, Y failed, Z skipped, W total"
    # or "X passed, Y failed, Z total"
    tests_pattern = r"Tests?:\s*(.*)"
    match = re.search(tests_pattern, output)
    if match:
        summary = match.group(1)

        passed_match = re.search(r"(\d+) passed", summary)
        if passed_match:
            passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+) failed", summary)
        if failed_match:
            failed = int(failed_match.group(1))

        skipped_match = re.search(r"(\d+) skipped", summary)
        if skipped_match:
            skipped = int(skipped_match.group(1))

    # Extract failed test names (jest shows them with ✕)
    for match in re.finditer(r"✕\s+(.+?)(?:\s+\(\d+|\n)", output):
        failed_tests.append(match.group(1).strip())

    total = passed + failed + skipped

    return TestResult(
        framework=TestFramework.JEST.value,
        timestamp=now_iso(),
        duration_seconds=round(duration, 2),
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=0,
        failed_tests=failed_tests,
        command=command,
        exit_code=exit_code,
    )


def _parse_go_output(
    output: str, command: str, duration: float, exit_code: int
) -> TestResult:
    """Parse go test output."""
    passed = 0
    failed = 0
    skipped = 0
    failed_tests = []

    # Count "--- PASS:" and "--- FAIL:" lines
    passed = len(re.findall(r"--- PASS:", output))
    failed = len(re.findall(r"--- FAIL:", output))
    skipped = len(re.findall(r"--- SKIP:", output))

    # Extract failed test names
    for match in re.finditer(r"--- FAIL: (\S+)", output):
        failed_tests.append(match.group(1))

    # Also check for "FAIL" at package level
    if exit_code != 0 and failed == 0:
        # Tests failed but we didn't find individual failures
        # This usually means compilation error or package-level failure
        failed = 1

    total = passed + failed + skipped

    return TestResult(
        framework=TestFramework.GO.value,
        timestamp=now_iso(),
        duration_seconds=round(duration, 2),
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=0,
        failed_tests=failed_tests,
        command=command,
        exit_code=exit_code,
    )


def _parse_generic_output(
    framework: str, output: str, command: str, duration: float, exit_code: int
) -> TestResult:
    """Generic test output parser - tries common patterns."""
    passed = 0
    failed = 0
    skipped = 0

    # Try common patterns
    passed_match = re.search(r"(\d+)\s+(?:passed|pass|ok|success)", output, re.I)
    if passed_match:
        passed = int(passed_match.group(1))

    failed_match = re.search(r"(\d+)\s+(?:failed|fail|error|failure)", output, re.I)
    if failed_match:
        failed = int(failed_match.group(1))

    skipped_match = re.search(r"(\d+)\s+(?:skipped|skip|pending|ignored)", output, re.I)
    if skipped_match:
        skipped = int(skipped_match.group(1))

    total = passed + failed + skipped

    # If we couldn't parse anything, infer from exit code
    if total == 0:
        if exit_code == 0:
            passed = 1
            total = 1
        else:
            failed = 1
            total = 1

    return TestResult(
        framework=framework,
        timestamp=now_iso(),
        duration_seconds=round(duration, 2),
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=0,
        failed_tests=[],
        command=command,
        exit_code=exit_code,
    )


def format_status(result: TestResult | None, verbose: bool = False) -> str:
    """Format test status for display."""
    if result is None:
        return "No test runs recorded. Run `idlergear test run` to execute tests."

    # Calculate time ago
    try:
        run_time = datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))
        now = datetime.now(run_time.tzinfo)
        delta = now - run_time
        if delta.days > 0:
            time_ago = f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.seconds >= 60:
            mins = delta.seconds // 60
            time_ago = f"{mins} minute{'s' if mins != 1 else ''} ago"
        else:
            time_ago = "just now"
    except (ValueError, TypeError):
        time_ago = result.timestamp

    # Format duration
    duration = result.duration_seconds
    if duration >= 60:
        mins = int(duration // 60)
        secs = int(duration % 60)
        duration_str = f"{mins}m {secs}s"
    else:
        duration_str = f"{duration:.1f}s"

    # Build status line
    if result.failed > 0 or result.errors > 0:
        status_icon = "❌"
        status_word = "FAILED"
    elif result.passed == 0:
        status_icon = "⚠️"
        status_word = "NO TESTS"
    else:
        status_icon = "✅"
        status_word = "PASSED"

    lines = [
        f"{status_icon} {status_word} ({result.framework})",
        f"   Last run: {time_ago}",
        f"   Results: {result.passed} passed, {result.failed} failed, {result.skipped} skipped",
        f"   Duration: {duration_str}",
    ]

    if result.failed_tests and verbose:
        lines.append("   Failed tests:")
        for test in result.failed_tests[:10]:  # Limit to first 10
            lines.append(f"     - {test}")
        if len(result.failed_tests) > 10:
            lines.append(f"     ... and {len(result.failed_tests) - 10} more")

    return "\n".join(lines)


# =============================================================================
# Test Enumeration (#133)
# =============================================================================


@dataclass
class TestItem:
    """A single test item (file or function)."""

    name: str
    file: str
    line: int = 0
    kind: str = "function"  # "function", "class", "file"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "file": self.file,
            "line": self.line,
            "kind": self.kind,
        }


@dataclass
class TestEnumeration:
    """Enumeration of tests in a project."""

    framework: str
    timestamp: str
    test_files: list[str]
    test_items: list[TestItem]
    total_files: int = 0
    total_tests: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "framework": self.framework,
            "timestamp": self.timestamp,
            "test_files": self.test_files,
            "test_items": [t.to_dict() for t in self.test_items],
            "total_files": self.total_files,
            "total_tests": self.total_tests,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestEnumeration":
        """Create from dictionary."""
        return cls(
            framework=data.get("framework", "unknown"),
            timestamp=data.get("timestamp", ""),
            test_files=data.get("test_files", []),
            test_items=[
                TestItem(
                    name=t.get("name", ""),
                    file=t.get("file", ""),
                    line=t.get("line", 0),
                    kind=t.get("kind", "function"),
                )
                for t in data.get("test_items", [])
            ],
            total_files=data.get("total_files", 0),
            total_tests=data.get("total_tests", 0),
        )


def enumerate_tests(project_path: Path | None = None) -> TestEnumeration | None:
    """Enumerate all tests in the project.

    Returns TestEnumeration with list of test files and test items.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    config = detect_framework(project_path)
    if config is None:
        return None

    framework = config.framework

    if framework == TestFramework.PYTEST.value:
        return _enumerate_pytest(project_path)
    elif framework == TestFramework.CARGO.value:
        return _enumerate_cargo(project_path)
    elif framework == TestFramework.GO.value:
        return _enumerate_go(project_path)
    elif framework in (TestFramework.JEST.value, TestFramework.VITEST.value):
        return _enumerate_js(project_path, framework)
    elif framework == TestFramework.DOTNET.value:
        return _enumerate_dotnet(project_path)
    elif framework == TestFramework.RSPEC.value:
        return _enumerate_rspec(project_path)
    else:
        return None


def _enumerate_pytest(project_path: Path) -> TestEnumeration:
    """Enumerate pytest tests using --collect-only."""
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = proc.stdout
    except (subprocess.TimeoutExpired, Exception):
        # Fallback to file-based enumeration
        return _enumerate_pytest_files(project_path)

    test_files: set[str] = set()
    test_items: list[TestItem] = []

    # Parse output like: tests/test_foo.py::test_bar
    for line in output.splitlines():
        line = line.strip()
        if "::" in line and not line.startswith(("=", "-", " ")):
            parts = line.split("::")
            file_path = parts[0]
            test_name = "::".join(parts[1:]) if len(parts) > 1 else ""

            test_files.add(file_path)
            if test_name:
                test_items.append(
                    TestItem(
                        name=test_name,
                        file=file_path,
                        kind="function" if "::" not in test_name else "method",
                    )
                )

    return TestEnumeration(
        framework=TestFramework.PYTEST.value,
        timestamp=now_iso(),
        test_files=sorted(test_files),
        test_items=test_items,
        total_files=len(test_files),
        total_tests=len(test_items),
    )


def _enumerate_pytest_files(project_path: Path) -> TestEnumeration:
    """Fallback: enumerate pytest test files without running pytest."""
    test_files: list[str] = []

    # Look for test_*.py and *_test.py files
    for pattern in ["**/test_*.py", "**/*_test.py"]:
        for path in project_path.glob(pattern):
            if ".venv" not in str(path) and "venv" not in str(path):
                rel_path = str(path.relative_to(project_path))
                if rel_path not in test_files:
                    test_files.append(rel_path)

    return TestEnumeration(
        framework=TestFramework.PYTEST.value,
        timestamp=now_iso(),
        test_files=sorted(test_files),
        test_items=[TestItem(name=f, file=f, kind="file") for f in sorted(test_files)],
        total_files=len(test_files),
        total_tests=len(test_files),  # Approximate - one per file
    )


def _enumerate_cargo(project_path: Path) -> TestEnumeration:
    """Enumerate cargo tests using --list."""
    try:
        proc = subprocess.run(
            ["cargo", "test", "--", "--list"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = proc.stdout
    except (subprocess.TimeoutExpired, Exception):
        return _enumerate_cargo_files(project_path)

    test_items: list[TestItem] = []

    # Parse output like: tests::test_name: test
    for line in output.splitlines():
        line = line.strip()
        if line.endswith(": test"):
            test_name = line[:-6]  # Remove ": test"
            test_items.append(TestItem(name=test_name, file="", kind="function"))

    # Find test files
    test_files = [
        str(p.relative_to(project_path)) for p in project_path.rglob("*_test.rs")
    ]
    test_files.extend(
        str(p.relative_to(project_path)) for p in project_path.rglob("tests/*.rs")
    )

    return TestEnumeration(
        framework=TestFramework.CARGO.value,
        timestamp=now_iso(),
        test_files=sorted(set(test_files)),
        test_items=test_items,
        total_files=len(set(test_files)),
        total_tests=len(test_items),
    )


def _enumerate_cargo_files(project_path: Path) -> TestEnumeration:
    """Fallback: enumerate cargo test files."""
    test_files: list[str] = []

    for pattern in ["**/tests/*.rs", "**/*_test.rs"]:
        for path in project_path.glob(pattern):
            rel_path = str(path.relative_to(project_path))
            if rel_path not in test_files:
                test_files.append(rel_path)

    return TestEnumeration(
        framework=TestFramework.CARGO.value,
        timestamp=now_iso(),
        test_files=sorted(test_files),
        test_items=[TestItem(name=f, file=f, kind="file") for f in sorted(test_files)],
        total_files=len(test_files),
        total_tests=len(test_files),
    )


def _enumerate_go(project_path: Path) -> TestEnumeration:
    """Enumerate Go tests."""
    try:
        proc = subprocess.run(
            ["go", "test", "./...", "-list", ".*"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = proc.stdout
    except (subprocess.TimeoutExpired, Exception):
        return _enumerate_go_files(project_path)

    test_items: list[TestItem] = []

    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Test") or line.startswith("Benchmark"):
            test_items.append(TestItem(name=line, file="", kind="function"))

    test_files = [
        str(p.relative_to(project_path)) for p in project_path.rglob("*_test.go")
    ]

    return TestEnumeration(
        framework=TestFramework.GO.value,
        timestamp=now_iso(),
        test_files=sorted(test_files),
        test_items=test_items,
        total_files=len(test_files),
        total_tests=len(test_items),
    )


def _enumerate_go_files(project_path: Path) -> TestEnumeration:
    """Fallback: enumerate Go test files."""
    test_files = [
        str(p.relative_to(project_path)) for p in project_path.rglob("*_test.go")
    ]

    return TestEnumeration(
        framework=TestFramework.GO.value,
        timestamp=now_iso(),
        test_files=sorted(test_files),
        test_items=[TestItem(name=f, file=f, kind="file") for f in sorted(test_files)],
        total_files=len(test_files),
        total_tests=len(test_files),
    )


def _enumerate_js(project_path: Path, framework: str) -> TestEnumeration:
    """Enumerate JavaScript tests (jest/vitest)."""
    test_files: list[str] = []

    # Common test file patterns
    patterns = [
        "**/*.test.js",
        "**/*.test.ts",
        "**/*.test.jsx",
        "**/*.test.tsx",
        "**/*.spec.js",
        "**/*.spec.ts",
        "**/__tests__/*.js",
        "**/__tests__/*.ts",
    ]

    for pattern in patterns:
        for path in project_path.glob(pattern):
            if "node_modules" not in str(path):
                rel_path = str(path.relative_to(project_path))
                if rel_path not in test_files:
                    test_files.append(rel_path)

    return TestEnumeration(
        framework=framework,
        timestamp=now_iso(),
        test_files=sorted(test_files),
        test_items=[TestItem(name=f, file=f, kind="file") for f in sorted(test_files)],
        total_files=len(test_files),
        total_tests=len(test_files),
    )


def _enumerate_dotnet(project_path: Path) -> TestEnumeration:
    """Enumerate .NET tests."""
    try:
        proc = subprocess.run(
            ["dotnet", "test", "--list-tests"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = proc.stdout
    except (subprocess.TimeoutExpired, Exception):
        return _enumerate_dotnet_files(project_path)

    test_items: list[TestItem] = []
    in_test_list = False

    for line in output.splitlines():
        line = line.strip()
        if "The following Tests are available:" in line:
            in_test_list = True
            continue
        if in_test_list and line:
            test_items.append(TestItem(name=line, file="", kind="function"))

    test_files = [
        str(p.relative_to(project_path)) for p in project_path.rglob("*Tests.cs")
    ]
    test_files.extend(
        str(p.relative_to(project_path)) for p in project_path.rglob("*Test.cs")
    )

    return TestEnumeration(
        framework=TestFramework.DOTNET.value,
        timestamp=now_iso(),
        test_files=sorted(set(test_files)),
        test_items=test_items,
        total_files=len(set(test_files)),
        total_tests=len(test_items),
    )


def _enumerate_dotnet_files(project_path: Path) -> TestEnumeration:
    """Fallback: enumerate .NET test files."""
    test_files: list[str] = []

    for pattern in ["**/*Tests.cs", "**/*Test.cs"]:
        for path in project_path.glob(pattern):
            rel_path = str(path.relative_to(project_path))
            if rel_path not in test_files:
                test_files.append(rel_path)

    return TestEnumeration(
        framework=TestFramework.DOTNET.value,
        timestamp=now_iso(),
        test_files=sorted(test_files),
        test_items=[TestItem(name=f, file=f, kind="file") for f in sorted(test_files)],
        total_files=len(test_files),
        total_tests=len(test_files),
    )


def _enumerate_rspec(project_path: Path) -> TestEnumeration:
    """Enumerate RSpec tests."""
    test_files: list[str] = []

    for path in project_path.glob("spec/**/*_spec.rb"):
        rel_path = str(path.relative_to(project_path))
        test_files.append(rel_path)

    return TestEnumeration(
        framework=TestFramework.RSPEC.value,
        timestamp=now_iso(),
        test_files=sorted(test_files),
        test_items=[TestItem(name=f, file=f, kind="file") for f in sorted(test_files)],
        total_files=len(test_files),
        total_tests=len(test_files),
    )


def save_enumeration(enum: TestEnumeration, project_path: Path | None = None) -> None:
    """Save test enumeration to cache."""
    tests_dir = get_tests_dir(project_path)
    if tests_dir is None:
        return

    tests_dir.mkdir(parents=True, exist_ok=True)
    enum_file = tests_dir / "enumeration.json"
    enum_file.write_text(json.dumps(enum.to_dict(), indent=2) + "\n")


def get_enumeration(project_path: Path | None = None) -> TestEnumeration | None:
    """Get cached test enumeration."""
    tests_dir = get_tests_dir(project_path)
    if tests_dir is None:
        return None

    enum_file = tests_dir / "enumeration.json"
    if not enum_file.exists():
        return None

    try:
        data = json.loads(enum_file.read_text())
        return TestEnumeration.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None


# =============================================================================
# Coverage Mapping (#134)
# =============================================================================


@dataclass
class CoverageMap:
    """Mapping of source files to test files."""

    framework: str
    timestamp: str
    mappings: dict[str, list[str]]  # source_file -> [test_files]
    reverse_mappings: dict[str, list[str]]  # test_file -> [source_files]
    uncovered: list[str]  # source files without tests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "framework": self.framework,
            "timestamp": self.timestamp,
            "mappings": self.mappings,
            "reverse_mappings": self.reverse_mappings,
            "uncovered": self.uncovered,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoverageMap":
        """Create from dictionary."""
        return cls(
            framework=data.get("framework", "unknown"),
            timestamp=data.get("timestamp", ""),
            mappings=data.get("mappings", {}),
            reverse_mappings=data.get("reverse_mappings", {}),
            uncovered=data.get("uncovered", []),
        )


def build_coverage_map(project_path: Path | None = None) -> CoverageMap | None:
    """Build a coverage map linking source files to test files.

    Uses convention-based mapping:
    - src/foo.py -> tests/test_foo.py
    - src/bar/baz.py -> tests/bar/test_baz.py
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    config = detect_framework(project_path)
    if config is None:
        return None

    framework = config.framework

    # Get all source files
    source_files = _get_source_files(project_path, framework)

    # Get all test files
    enum = enumerate_tests(project_path)
    if enum is None:
        return None

    test_files = set(enum.test_files)

    # Build mappings
    mappings: dict[str, list[str]] = {}
    reverse_mappings: dict[str, list[str]] = {}
    uncovered: list[str] = []

    for source_file in source_files:
        # Find likely test files for this source
        likely_tests = _find_tests_for_source(source_file, test_files, framework)

        if likely_tests:
            mappings[source_file] = likely_tests
            for test in likely_tests:
                if test not in reverse_mappings:
                    reverse_mappings[test] = []
                reverse_mappings[test].append(source_file)
        else:
            uncovered.append(source_file)

    coverage_map = CoverageMap(
        framework=framework,
        timestamp=now_iso(),
        mappings=mappings,
        reverse_mappings=reverse_mappings,
        uncovered=uncovered,
    )

    # Save to cache
    save_coverage_map(coverage_map, project_path)

    return coverage_map


def _get_source_files(project_path: Path, framework: str) -> list[str]:
    """Get all source files for a project."""
    source_files: list[str] = []

    if framework == TestFramework.PYTEST.value:
        # Python source files
        for pattern in ["src/**/*.py", "**/*.py"]:
            for path in project_path.glob(pattern):
                rel = str(path.relative_to(project_path))
                # Skip test files, venv, etc.
                if (
                    "test" not in rel.lower()
                    and "venv" not in rel
                    and ".venv" not in rel
                    and "__pycache__" not in rel
                    and "conftest" not in rel
                ):
                    source_files.append(rel)

    elif framework == TestFramework.CARGO.value:
        for path in project_path.glob("src/**/*.rs"):
            rel = str(path.relative_to(project_path))
            if "_test" not in rel and "tests/" not in rel:
                source_files.append(rel)

    elif framework == TestFramework.GO.value:
        for path in project_path.glob("**/*.go"):
            rel = str(path.relative_to(project_path))
            if "_test.go" not in rel and "vendor/" not in rel:
                source_files.append(rel)

    elif framework in (TestFramework.JEST.value, TestFramework.VITEST.value):
        for pattern in ["src/**/*.js", "src/**/*.ts", "src/**/*.jsx", "src/**/*.tsx"]:
            for path in project_path.glob(pattern):
                rel = str(path.relative_to(project_path))
                if (
                    ".test." not in rel
                    and ".spec." not in rel
                    and "node_modules" not in rel
                ):
                    source_files.append(rel)

    elif framework == TestFramework.DOTNET.value:
        for path in project_path.glob("**/*.cs"):
            rel = str(path.relative_to(project_path))
            if "Test" not in rel and "bin/" not in rel and "obj/" not in rel:
                source_files.append(rel)

    elif framework == TestFramework.RSPEC.value:
        for pattern in ["lib/**/*.rb", "app/**/*.rb"]:
            for path in project_path.glob(pattern):
                rel = str(path.relative_to(project_path))
                if "_spec" not in rel:
                    source_files.append(rel)

    return sorted(set(source_files))


def _find_tests_for_source(
    source_file: str, test_files: set[str], framework: str
) -> list[str]:
    """Find test files that likely test a source file."""
    matches: list[str] = []
    source_path = Path(source_file)
    source_name = source_path.stem

    for test_file in test_files:
        test_path = Path(test_file)
        test_name = test_path.stem

        # Convention: test_foo.py tests foo.py
        if framework == TestFramework.PYTEST.value:
            if test_name == f"test_{source_name}" or test_name == f"{source_name}_test":
                matches.append(test_file)
            # Also match if directory structure is similar
            elif source_name in test_name:
                matches.append(test_file)

        elif framework == TestFramework.CARGO.value:
            if test_name == f"{source_name}_test" or source_name in test_name:
                matches.append(test_file)

        elif framework == TestFramework.GO.value:
            if test_name == f"{source_name}_test":
                matches.append(test_file)

        elif framework in (TestFramework.JEST.value, TestFramework.VITEST.value):
            base_name = (
                source_name.replace(".tsx", "")
                .replace(".jsx", "")
                .replace(".ts", "")
                .replace(".js", "")
            )
            if base_name in test_name:
                matches.append(test_file)

        elif framework == TestFramework.DOTNET.value:
            if f"{source_name}Tests" in test_name or f"{source_name}Test" in test_name:
                matches.append(test_file)

        elif framework == TestFramework.RSPEC.value:
            if test_name == f"{source_name}_spec":
                matches.append(test_file)

    return matches


def save_coverage_map(
    coverage_map: CoverageMap, project_path: Path | None = None
) -> None:
    """Save coverage map to cache."""
    tests_dir = get_tests_dir(project_path)
    if tests_dir is None:
        return

    tests_dir.mkdir(parents=True, exist_ok=True)
    map_file = tests_dir / "coverage-map.json"
    map_file.write_text(json.dumps(coverage_map.to_dict(), indent=2) + "\n")


def get_coverage_map(project_path: Path | None = None) -> CoverageMap | None:
    """Get cached coverage map."""
    tests_dir = get_tests_dir(project_path)
    if tests_dir is None:
        return None

    map_file = tests_dir / "coverage-map.json"
    if not map_file.exists():
        return None

    try:
        data = json.loads(map_file.read_text())
        return CoverageMap.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None


def get_tests_for_file(source_file: str, project_path: Path | None = None) -> list[str]:
    """Get test files for a source file."""
    coverage_map = get_coverage_map(project_path)
    if coverage_map is None:
        coverage_map = build_coverage_map(project_path)
    if coverage_map is None:
        return []

    return coverage_map.mappings.get(source_file, [])


def get_uncovered_files(project_path: Path | None = None) -> list[str]:
    """Get source files without tests."""
    coverage_map = get_coverage_map(project_path)
    if coverage_map is None:
        coverage_map = build_coverage_map(project_path)
    if coverage_map is None:
        return []

    return coverage_map.uncovered


# =============================================================================
# Smart Test Selection (#135)
# =============================================================================


def get_changed_files(
    project_path: Path | None = None,
    since: str | None = None,
    staged_only: bool = False,
) -> list[str]:
    """Get files changed since last commit or since a specific commit.

    Args:
        project_path: Project root
        since: Commit hash or ref to compare against (default: HEAD)
        staged_only: Only return staged files
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    try:
        if staged_only:
            # Get staged files
            proc = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
        elif since:
            # Get files changed since a commit
            proc = subprocess.run(
                ["git", "diff", "--name-only", since],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
        else:
            # Get all uncommitted changes (staged + unstaged)
            proc = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            # Also include untracked files
            proc2 = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            return sorted(set(proc.stdout.splitlines() + proc2.stdout.splitlines()))

        return proc.stdout.splitlines()
    except Exception:
        return []


def get_tests_for_changes(
    project_path: Path | None = None,
    since: str | None = None,
) -> list[str]:
    """Get test files that should run based on changed files.

    Returns list of test file paths.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    changed = get_changed_files(project_path, since=since)
    if not changed:
        return []

    # Build coverage map if needed
    coverage_map = get_coverage_map(project_path)
    if coverage_map is None:
        coverage_map = build_coverage_map(project_path)
    if coverage_map is None:
        return []

    tests_to_run: set[str] = set()

    for file in changed:
        # If it's a test file itself, include it
        if file in coverage_map.reverse_mappings:
            tests_to_run.add(file)

        # If it's a source file, include its tests
        if file in coverage_map.mappings:
            tests_to_run.update(coverage_map.mappings[file])

    return sorted(tests_to_run)


def run_changed_tests(
    project_path: Path | None = None,
    since: str | None = None,
    extra_args: str | None = None,
) -> tuple[TestResult, str]:
    """Run only tests for changed files.

    Returns (TestResult, output) tuple.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    config = detect_framework(project_path)
    if config is None:
        result = TestResult(
            framework="unknown",
            timestamp=now_iso(),
            duration_seconds=0,
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            failed_tests=["No test framework detected"],
            command="",
            exit_code=1,
        )
        return result, ""

    tests_to_run = get_tests_for_changes(project_path, since=since)

    if not tests_to_run:
        result = TestResult(
            framework=config.framework,
            timestamp=now_iso(),
            duration_seconds=0,
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=0,
            failed_tests=[],
            command="",
            exit_code=0,
        )
        return result, "No tests to run - no changed files affect tests."

    # Build command with specific test files
    framework = config.framework
    if framework == TestFramework.PYTEST.value:
        test_args = " ".join(tests_to_run)
        if extra_args:
            test_args = f"{test_args} {extra_args}"
    elif framework == TestFramework.CARGO.value:
        # Cargo doesn't easily support running specific files
        test_args = extra_args or ""
    elif framework == TestFramework.GO.value:
        # For Go, we need to specify packages
        packages = set()
        for test in tests_to_run:
            pkg = str(Path(test).parent)
            if pkg:
                packages.add(f"./{pkg}/...")
        test_args = " ".join(packages) if packages else "./..."
        if extra_args:
            test_args = f"{test_args} {extra_args}"
    else:
        test_args = " ".join(tests_to_run)
        if extra_args:
            test_args = f"{test_args} {extra_args}"

    # Create modified config with specific files
    modified_config = TestConfig(
        framework=config.framework,
        command=config.command,
        test_dir=config.test_dir,
        test_pattern=config.test_pattern,
    )

    return run_tests(project_path, modified_config, extra_args=test_args)


# =============================================================================
# External Test Detection (#136)
# =============================================================================


@dataclass
class ExternalTestRun:
    """Information about a test run detected outside IdlerGear."""

    framework: str
    timestamp: str
    cache_path: str
    estimated_tests: int = 0
    success: bool | None = None  # None if we can't determine

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "framework": self.framework,
            "timestamp": self.timestamp,
            "cache_path": self.cache_path,
            "estimated_tests": self.estimated_tests,
            "success": self.success,
        }


def get_cache_paths(project_path: Path, framework: str) -> list[Path]:
    """Get framework-specific cache/result paths to monitor."""
    paths = []

    if framework == TestFramework.PYTEST.value:
        # pytest creates .pytest_cache and possibly coverage files
        paths.append(project_path / ".pytest_cache")
        paths.append(project_path / ".coverage")
        paths.append(project_path / "htmlcov")
        # Also check for junit xml output
        paths.append(project_path / "junit.xml")
        paths.append(project_path / "test-results.xml")

    elif framework == TestFramework.CARGO.value:
        # Cargo test uses target/debug for test binaries
        paths.append(project_path / "target" / "debug" / ".fingerprint")

    elif framework == TestFramework.GO.value:
        # Go test cache
        paths.append(project_path / ".go-test-cache")
        # Go also writes to GOCACHE, but that's global

    elif framework in (TestFramework.JEST.value, TestFramework.VITEST.value):
        # Jest/vitest cache
        paths.append(project_path / "node_modules" / ".cache" / "jest")
        paths.append(project_path / "node_modules" / ".cache" / "vitest")
        paths.append(project_path / ".vitest")
        paths.append(project_path / "coverage")

    elif framework == TestFramework.DOTNET.value:
        # .NET test results
        paths.append(project_path / "TestResults")

    elif framework == TestFramework.RSPEC.value:
        # RSpec output
        paths.append(project_path / ".rspec_status")
        paths.append(project_path / "coverage")

    return [p for p in paths if p.exists()]


def get_cache_mtime(cache_path: Path) -> float | None:
    """Get the most recent modification time in a cache directory."""
    try:
        if cache_path.is_file():
            return cache_path.stat().st_mtime

        if cache_path.is_dir():
            latest = 0.0
            for item in cache_path.rglob("*"):
                try:
                    mtime = item.stat().st_mtime
                    if mtime > latest:
                        latest = mtime
                except (OSError, PermissionError):
                    continue
            return latest if latest > 0 else None

        return None
    except (OSError, PermissionError):
        return None


def check_external_test_runs(
    project_path: Path | None = None,
) -> list[ExternalTestRun]:
    """Check for test runs that happened outside IdlerGear.

    Compares cache modification times against our last recorded run.
    Returns list of detected external runs (usually 0 or 1).
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    config = detect_framework(project_path)
    if config is None:
        return []

    framework = config.framework

    # Get our last recorded run time
    last_result = get_last_result(project_path)
    last_run_time: float = 0
    if last_result:
        try:
            dt = datetime.fromisoformat(last_result.timestamp.replace("Z", "+00:00"))
            last_run_time = dt.timestamp()
        except (ValueError, TypeError):
            pass

    # Check cache paths
    external_runs: list[ExternalTestRun] = []
    cache_paths = get_cache_paths(project_path, framework)

    for cache_path in cache_paths:
        cache_mtime = get_cache_mtime(cache_path)
        if cache_mtime is None:
            continue

        # If cache was modified after our last run, tests ran externally
        if cache_mtime > last_run_time + 1:  # 1 second buffer
            # Try to extract more info from the cache
            estimated_tests = 0
            success = None

            if framework == TestFramework.PYTEST.value:
                estimated_tests, success = _parse_pytest_cache(cache_path)
            elif framework in (TestFramework.JEST.value, TestFramework.VITEST.value):
                estimated_tests, success = _parse_jest_cache(cache_path)

            external_runs.append(
                ExternalTestRun(
                    framework=framework,
                    timestamp=datetime.fromtimestamp(cache_mtime).isoformat(),
                    cache_path=str(cache_path.relative_to(project_path)),
                    estimated_tests=estimated_tests,
                    success=success,
                )
            )

    return external_runs


def _parse_pytest_cache(cache_path: Path) -> tuple[int, bool | None]:
    """Parse pytest cache for test info."""
    estimated_tests = 0
    success = None

    try:
        # Check lastfailed file
        lastfailed = cache_path / "v" / "cache" / "lastfailed"
        if lastfailed.exists():
            content = lastfailed.read_text()
            if content.strip() == "{}":
                success = True  # No failed tests
            else:
                success = False
                # Count failed tests
                try:
                    failed_data = json.loads(content)
                    estimated_tests = len(failed_data)
                except json.JSONDecodeError:
                    pass

        # Check nodeids for test count
        nodeids = cache_path / "v" / "cache" / "nodeids"
        if nodeids.exists():
            try:
                content = nodeids.read_text()
                ids = json.loads(content)
                if isinstance(ids, list):
                    estimated_tests = max(estimated_tests, len(ids))
            except (json.JSONDecodeError, TypeError):
                pass

    except (OSError, PermissionError):
        pass

    return estimated_tests, success


def _parse_jest_cache(cache_path: Path) -> tuple[int, bool | None]:
    """Parse jest/vitest cache for test info."""
    estimated_tests = 0
    success = None

    try:
        # Jest stores test results in cache directory
        for result_file in cache_path.rglob("*.json"):
            try:
                data = json.loads(result_file.read_text())
                if isinstance(data, dict):
                    if "numPassedTests" in data:
                        estimated_tests += data.get("numPassedTests", 0)
                        estimated_tests += data.get("numFailedTests", 0)
                        if data.get("numFailedTests", 0) > 0:
                            success = False
                        elif success is None:
                            success = True
            except (json.JSONDecodeError, OSError):
                continue
    except (OSError, PermissionError):
        pass

    return estimated_tests, success


def import_external_result(
    external_run: ExternalTestRun,
    project_path: Path | None = None,
) -> TestResult | None:
    """Try to import results from an external test run.

    Attempts to parse cache files to reconstruct a TestResult.
    Returns None if we can't extract enough information.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    framework = external_run.framework
    cache_path = project_path / external_run.cache_path

    if framework == TestFramework.PYTEST.value:
        return _import_pytest_result(cache_path, external_run, project_path)

    # For other frameworks, create a basic result if we have enough info
    if external_run.estimated_tests > 0 or external_run.success is not None:
        result = TestResult(
            framework=framework,
            timestamp=external_run.timestamp,
            duration_seconds=0,  # Unknown
            total=external_run.estimated_tests,
            passed=external_run.estimated_tests if external_run.success else 0,
            failed=0 if external_run.success else external_run.estimated_tests,
            skipped=0,
            errors=0,
            failed_tests=[],
            command="(external)",
            exit_code=0 if external_run.success else 1,
        )
        return result

    return None


def _import_pytest_result(
    cache_path: Path,
    external_run: ExternalTestRun,
    project_path: Path,
) -> TestResult | None:
    """Import pytest results from cache."""
    passed = 0
    failed = 0
    failed_tests: list[str] = []

    try:
        # Get failed tests from lastfailed
        lastfailed = cache_path / "v" / "cache" / "lastfailed"
        if lastfailed.exists():
            content = lastfailed.read_text()
            try:
                failed_data = json.loads(content)
                if isinstance(failed_data, dict):
                    failed_tests = list(failed_data.keys())
                    failed = len(failed_tests)
            except json.JSONDecodeError:
                pass

        # Get total test count from nodeids
        nodeids = cache_path / "v" / "cache" / "nodeids"
        if nodeids.exists():
            try:
                content = nodeids.read_text()
                ids = json.loads(content)
                if isinstance(ids, list):
                    passed = len(ids) - failed
            except (json.JSONDecodeError, TypeError):
                pass

        total = passed + failed
        if total == 0:
            return None

        result = TestResult(
            framework=TestFramework.PYTEST.value,
            timestamp=external_run.timestamp,
            duration_seconds=0,  # Unknown from cache
            total=total,
            passed=passed,
            failed=failed,
            skipped=0,  # Unknown from cache
            errors=0,
            failed_tests=failed_tests,
            command="(external)",
            exit_code=1 if failed > 0 else 0,
        )

        # Save the imported result
        save_result(result, project_path)

        return result

    except (OSError, PermissionError):
        return None


def sync_external_runs(project_path: Path | None = None) -> list[TestResult]:
    """Check for and import any external test runs.

    Returns list of TestResult objects that were imported.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    external_runs = check_external_test_runs(project_path)
    imported: list[TestResult] = []

    for run in external_runs:
        result = import_external_result(run, project_path)
        if result:
            imported.append(result)

    return imported


def get_test_staleness(project_path: Path | None = None) -> dict[str, Any]:
    """Get information about how stale the test results are.

    Returns dict with:
    - last_run: timestamp of last recorded test run
    - seconds_ago: how many seconds ago
    - external_detected: True if tests ran outside IdlerGear
    - external_runs: list of detected external runs
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        project_path = Path.cwd()

    result: dict[str, Any] = {
        "last_run": None,
        "seconds_ago": None,
        "external_detected": False,
        "external_runs": [],
    }

    last_result = get_last_result(project_path)
    if last_result:
        result["last_run"] = last_result.timestamp
        try:
            from datetime import timezone

            dt = datetime.fromisoformat(last_result.timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            result["seconds_ago"] = (now - dt).total_seconds()
        except (ValueError, TypeError):
            pass

    external_runs = check_external_test_runs(project_path)
    if external_runs:
        result["external_detected"] = True
        result["external_runs"] = [r.to_dict() for r in external_runs]

    return result
