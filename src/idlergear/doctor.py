"""Health check and diagnostics for IdlerGear installations.

The `idlergear doctor` command checks for:
1. Configuration health - Is IdlerGear properly initialized?
2. File installation status - Are all managed files up to date?
3. Lingering/legacy files - Are there files that should be cleaned up?
4. Unmanaged knowledge files - Are there files that should be migrated?
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from idlergear import __version__
from idlergear.config import find_idlergear_root
from idlergear.upgrade import parse_version, get_project_version


class CheckStatus(str, Enum):
    """Status of a health check."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


@dataclass
class CheckResult:
    """Result of a single health check."""

    name: str
    status: CheckStatus
    message: str
    fix: str | None = None  # Suggested fix command or action
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "fix": self.fix,
            "details": self.details,
        }


@dataclass
class DoctorReport:
    """Complete health report from running doctor."""

    checks: list[CheckResult]
    project_path: Path | None
    installed_version: str
    project_version: str | None

    @property
    def has_errors(self) -> bool:
        return any(c.status == CheckStatus.ERROR for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.status == CheckStatus.WARNING for c in self.checks)

    @property
    def is_healthy(self) -> bool:
        return not self.has_errors and not self.has_warnings

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_path": str(self.project_path) if self.project_path else None,
            "installed_version": self.installed_version,
            "project_version": self.project_version,
            "is_healthy": self.is_healthy,
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
            "checks": [c.to_dict() for c in self.checks],
        }


# ============================================================================
# Configuration Checks
# ============================================================================


def check_initialization(project_path: Path) -> CheckResult:
    """Check if IdlerGear is properly initialized."""
    idlergear_dir = project_path / ".idlergear"

    if not idlergear_dir.exists():
        return CheckResult(
            name="initialization",
            status=CheckStatus.ERROR,
            message="IdlerGear not initialized - .idlergear/ directory missing",
            fix="idlergear init",
        )

    config_file = idlergear_dir / "config.json"
    if not config_file.exists():
        return CheckResult(
            name="initialization",
            status=CheckStatus.WARNING,
            message="Config file missing - .idlergear/config.json",
            fix="idlergear init",
        )

    return CheckResult(
        name="initialization",
        status=CheckStatus.OK,
        message="IdlerGear properly initialized",
    )


def check_version(project_path: Path) -> CheckResult:
    """Check if project version is current with installed version."""
    project_version = get_project_version(project_path)

    if project_version is None:
        return CheckResult(
            name="version",
            status=CheckStatus.WARNING,
            message=f"No version stored in project (installed: {__version__})",
            fix="idlergear install --upgrade",
            details={"installed_version": __version__},
        )

    installed = parse_version(__version__)
    project = parse_version(project_version)

    if installed > project:
        return CheckResult(
            name="version",
            status=CheckStatus.WARNING,
            message=f"Project version ({project_version}) is older than installed ({__version__})",
            fix="idlergear install --upgrade",
            details={
                "installed_version": __version__,
                "project_version": project_version,
            },
        )

    return CheckResult(
        name="version",
        status=CheckStatus.OK,
        message=f"Project version is current ({project_version})",
    )


# ============================================================================
# File Installation Checks
# ============================================================================


def check_mcp_config(project_path: Path) -> CheckResult:
    """Check if .mcp.json has IdlerGear configured."""
    mcp_file = project_path / ".mcp.json"

    if not mcp_file.exists():
        return CheckResult(
            name="mcp_config",
            status=CheckStatus.ERROR,
            message="MCP config missing - .mcp.json not found",
            fix="idlergear install",
        )

    try:
        config = json.loads(mcp_file.read_text())
        servers = config.get("mcpServers", {})

        if "idlergear" not in servers:
            return CheckResult(
                name="mcp_config",
                status=CheckStatus.ERROR,
                message="IdlerGear MCP server not configured in .mcp.json",
                fix="idlergear install",
            )

        # Check if command is correct
        ig_config = servers["idlergear"]
        if ig_config.get("command") != "idlergear-mcp":
            return CheckResult(
                name="mcp_config",
                status=CheckStatus.WARNING,
                message="IdlerGear MCP command may be outdated",
                fix="idlergear install --upgrade",
                details={"current_command": ig_config.get("command")},
            )

    except (json.JSONDecodeError, KeyError) as e:
        return CheckResult(
            name="mcp_config",
            status=CheckStatus.ERROR,
            message=f"Invalid .mcp.json: {e}",
        )

    return CheckResult(
        name="mcp_config",
        status=CheckStatus.OK,
        message="MCP server properly configured",
    )


def check_hooks_config(project_path: Path) -> CheckResult:
    """Check if Claude hooks are configured."""
    hooks_file = project_path / ".claude" / "hooks.json"

    if not hooks_file.exists():
        return CheckResult(
            name="hooks_config",
            status=CheckStatus.WARNING,
            message="Claude hooks not configured - .claude/hooks.json missing",
            fix="idlergear install",
        )

    try:
        config = json.loads(hooks_file.read_text())
        hooks = config.get("hooks", {})

        # Check for IdlerGear hooks
        has_idlergear_hooks = False
        for hook_type, hook_list in hooks.items():
            for hook in hook_list:
                cmd = hook.get("command", "")
                if "idlergear" in cmd or "ig_" in cmd:
                    has_idlergear_hooks = True
                    break

        if not has_idlergear_hooks:
            return CheckResult(
                name="hooks_config",
                status=CheckStatus.WARNING,
                message="No IdlerGear hooks found in .claude/hooks.json",
                fix="idlergear install",
            )

    except (json.JSONDecodeError, KeyError) as e:
        return CheckResult(
            name="hooks_config",
            status=CheckStatus.ERROR,
            message=f"Invalid .claude/hooks.json: {e}",
        )

    return CheckResult(
        name="hooks_config",
        status=CheckStatus.OK,
        message="Claude hooks properly configured",
    )


def check_installed_files(project_path: Path) -> list[CheckResult]:
    """Check if all installed files are current."""
    from importlib.resources import files as pkg_files

    results = []

    # Check rules file
    rules_file = project_path / ".claude" / "rules" / "idlergear.md"
    if not rules_file.exists():
        results.append(
            CheckResult(
                name="rules_file",
                status=CheckStatus.WARNING,
                message="Rules file missing - .claude/rules/idlergear.md",
                fix="idlergear install --upgrade",
            )
        )
    else:
        # Compare with package version
        try:
            pkg_rules = pkg_files("idlergear") / "rules" / "idlergear.md"
            if pkg_rules.is_file():
                if rules_file.read_text() != pkg_rules.read_text():
                    results.append(
                        CheckResult(
                            name="rules_file",
                            status=CheckStatus.WARNING,
                            message="Rules file is outdated",
                            fix="idlergear install --upgrade",
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            name="rules_file",
                            status=CheckStatus.OK,
                            message="Rules file is current",
                        )
                    )
        except Exception:
            pass

    # Check skill directory
    skill_dir = project_path / ".claude" / "skills" / "idlergear"
    if not skill_dir.exists():
        results.append(
            CheckResult(
                name="skill",
                status=CheckStatus.WARNING,
                message="Skill directory missing - .claude/skills/idlergear/",
                fix="idlergear install",
            )
        )
    else:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            results.append(
                CheckResult(
                    name="skill",
                    status=CheckStatus.WARNING,
                    message="Skill file missing - SKILL.md",
                    fix="idlergear install --upgrade",
                )
            )
        else:
            # Compare with package version
            try:
                pkg_skill = pkg_files("idlergear") / "skills" / "idlergear" / "SKILL.md"
                if pkg_skill.is_file():
                    if skill_file.read_text() != pkg_skill.read_text():
                        results.append(
                            CheckResult(
                                name="skill",
                                status=CheckStatus.WARNING,
                                message="Skill file is outdated",
                                fix="idlergear install --upgrade",
                            )
                        )
                    else:
                        results.append(
                            CheckResult(
                                name="skill",
                                status=CheckStatus.OK,
                                message="Skill files are current",
                            )
                        )
            except Exception:
                pass

    # Check hook scripts
    from idlergear.install import HOOK_SCRIPTS

    hooks_dir = project_path / ".claude" / "hooks"
    missing_hooks = []
    outdated_hooks = []

    for script_name in HOOK_SCRIPTS:
        hook_file = hooks_dir / script_name
        if not hook_file.exists():
            missing_hooks.append(script_name)
        else:
            # Compare with package version
            try:
                pkg_hook = pkg_files("idlergear") / "hooks" / script_name
                if pkg_hook.is_file():
                    if hook_file.read_text() != pkg_hook.read_text():
                        outdated_hooks.append(script_name)
            except Exception:
                pass

    if missing_hooks:
        results.append(
            CheckResult(
                name="hook_scripts",
                status=CheckStatus.WARNING,
                message=f"Missing hook scripts: {', '.join(missing_hooks)}",
                fix="idlergear install --upgrade",
                details={"missing": missing_hooks},
            )
        )
    elif outdated_hooks:
        results.append(
            CheckResult(
                name="hook_scripts",
                status=CheckStatus.WARNING,
                message=f"Outdated hook scripts: {', '.join(outdated_hooks)}",
                fix="idlergear install --upgrade",
                details={"outdated": outdated_hooks},
            )
        )
    else:
        results.append(
            CheckResult(
                name="hook_scripts",
                status=CheckStatus.OK,
                message="Hook scripts are current",
            )
        )

    # Check slash commands
    commands_dir = project_path / ".claude" / "commands"
    if not commands_dir.exists():
        results.append(
            CheckResult(
                name="commands",
                status=CheckStatus.WARNING,
                message="Commands directory missing - .claude/commands/",
                fix="idlergear install",
            )
        )
    else:
        # Check for outdated commands
        try:
            pkg_commands = pkg_files("idlergear") / "commands"
            outdated_commands = []
            missing_commands = []

            for item in pkg_commands.iterdir():
                if item.is_file() and item.name.endswith(".md"):
                    local_cmd = commands_dir / item.name
                    if not local_cmd.exists():
                        missing_commands.append(item.name)
                    elif local_cmd.read_text() != item.read_text():
                        outdated_commands.append(item.name)

            if missing_commands or outdated_commands:
                msg_parts = []
                if missing_commands:
                    msg_parts.append(f"missing: {', '.join(missing_commands)}")
                if outdated_commands:
                    msg_parts.append(f"outdated: {', '.join(outdated_commands)}")
                results.append(
                    CheckResult(
                        name="commands",
                        status=CheckStatus.WARNING,
                        message=f"Slash commands need updating ({'; '.join(msg_parts)})",
                        fix="idlergear install --upgrade",
                        details={
                            "missing": missing_commands,
                            "outdated": outdated_commands,
                        },
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="commands",
                        status=CheckStatus.OK,
                        message="Slash commands are current",
                    )
                )
        except Exception:
            pass

    return results


# ============================================================================
# Lingering/Legacy File Checks
# ============================================================================

# Files that older versions of IdlerGear might have created
LEGACY_FILES = [
    ".idlergear/explorations.json",  # Removed in favor of notes with 'explore' tag
    ".idlergear/reference/",  # Moved to wiki/
]

# Files that users commonly create but should use IdlerGear instead
UNMANAGED_KNOWLEDGE_FILES = [
    "TODO.md",
    "TODO.txt",
    "TODOS.md",
    "TASKS.md",
    "NOTES.md",
    "SCRATCH.md",
    "BACKLOG.md",
    "SESSION.md",
    "SESSION_*.md",
    "FEATURE_IDEAS.md",
    "RESEARCH.md",
    "IDEAS.md",
]


def check_legacy_files(project_path: Path) -> list[CheckResult]:
    """Check for legacy files from older IdlerGear versions."""
    results = []
    found_legacy = []

    for legacy_path in LEGACY_FILES:
        full_path = project_path / legacy_path
        if legacy_path.endswith("/"):
            # Directory
            if full_path.exists() and full_path.is_dir():
                found_legacy.append(legacy_path)
        else:
            # File
            if full_path.exists():
                found_legacy.append(legacy_path)

    if found_legacy:
        results.append(
            CheckResult(
                name="legacy_files",
                status=CheckStatus.WARNING,
                message=f"Found {len(found_legacy)} legacy file(s) from older IdlerGear version",
                fix="idlergear organize --clean-legacy",
                details={"files": found_legacy},
            )
        )
    else:
        results.append(
            CheckResult(
                name="legacy_files",
                status=CheckStatus.OK,
                message="No legacy files found",
            )
        )

    return results


def check_unmanaged_knowledge_files(project_path: Path) -> list[CheckResult]:
    """Check for knowledge files that should be managed by IdlerGear."""
    results = []
    found_unmanaged = []

    for pattern in UNMANAGED_KNOWLEDGE_FILES:
        if "*" in pattern:
            # Glob pattern
            for match in project_path.glob(pattern):
                if match.is_file():
                    found_unmanaged.append(str(match.relative_to(project_path)))
        else:
            # Exact filename
            full_path = project_path / pattern
            if full_path.exists() and full_path.is_file():
                found_unmanaged.append(pattern)

    if found_unmanaged:
        results.append(
            CheckResult(
                name="unmanaged_files",
                status=CheckStatus.INFO,
                message=f"Found {len(found_unmanaged)} file(s) that could be managed by IdlerGear",
                fix="idlergear import",
                details={"files": found_unmanaged},
            )
        )
    else:
        results.append(
            CheckResult(
                name="unmanaged_files",
                status=CheckStatus.OK,
                message="No unmanaged knowledge files found",
            )
        )

    return results


def check_orphaned_claude_files(project_path: Path) -> list[CheckResult]:
    """Check for orphaned files in .claude/ that IdlerGear doesn't manage."""
    results = []
    orphaned = []

    claude_dir = project_path / ".claude"
    if not claude_dir.exists():
        return results

    # Known IdlerGear-managed files and directories
    known_paths = {
        "hooks.json",
        "hooks/",
        "rules/",
        "skills/idlergear/",
        "commands/",
    }

    # Known IdlerGear hook scripts
    from idlergear.install import HOOK_SCRIPTS

    for item in claude_dir.iterdir():
        item_name = item.name
        if item.is_dir():
            item_name += "/"

        # Check if this is a known IdlerGear item
        is_known = False
        for known in known_paths:
            if item_name == known or item_name.startswith(known.rstrip("/")):
                is_known = True
                break

        if not is_known:
            # Check if it's a hook script subdirectory item we know
            if item.is_dir() and item.name == "hooks":
                for sub in item.iterdir():
                    if sub.name not in HOOK_SCRIPTS and sub.name.startswith("ig_"):
                        # This is an IdlerGear hook we don't recognize
                        orphaned.append(f".claude/hooks/{sub.name}")
            elif not item_name.startswith("ig_"):
                # Not an IdlerGear file, might be from user or other tools
                # Only report if it looks like it might be ours
                pass

    # Check for old IdlerGear command files that no longer exist
    commands_dir = claude_dir / "commands"
    if commands_dir.exists():
        try:
            from importlib.resources import files as pkg_files

            pkg_commands = pkg_files("idlergear") / "commands"
            pkg_command_names = {
                item.name
                for item in pkg_commands.iterdir()
                if item.is_file() and item.name.endswith(".md")
            }

            for cmd_file in commands_dir.glob("ig_*.md"):
                if cmd_file.name not in pkg_command_names:
                    orphaned.append(f".claude/commands/{cmd_file.name}")
        except Exception:
            pass

    if orphaned:
        results.append(
            CheckResult(
                name="orphaned_files",
                status=CheckStatus.WARNING,
                message=f"Found {len(orphaned)} orphaned IdlerGear file(s)",
                fix="Remove manually or run `idlergear organize --clean-orphaned`",
                details={"files": orphaned},
            )
        )

    return results


# ============================================================================
# Main Doctor Function
# ============================================================================


def run_doctor(project_path: Path | None = None) -> DoctorReport:
    """Run all health checks and return a complete report.

    Args:
        project_path: Path to project root. If None, will auto-detect.

    Returns:
        DoctorReport with all check results.
    """
    if project_path is None:
        project_path = find_idlergear_root()

    checks = []

    if project_path is None:
        # Not in an IdlerGear project
        return DoctorReport(
            checks=[
                CheckResult(
                    name="project",
                    status=CheckStatus.ERROR,
                    message="Not in an IdlerGear project",
                    fix="idlergear init",
                )
            ],
            project_path=None,
            installed_version=__version__,
            project_version=None,
        )

    # Configuration checks
    checks.append(check_initialization(project_path))
    checks.append(check_version(project_path))

    # File installation checks
    checks.append(check_mcp_config(project_path))
    checks.append(check_hooks_config(project_path))
    checks.extend(check_installed_files(project_path))

    # Legacy and unmanaged file checks
    checks.extend(check_legacy_files(project_path))
    checks.extend(check_unmanaged_knowledge_files(project_path))
    checks.extend(check_orphaned_claude_files(project_path))

    return DoctorReport(
        checks=checks,
        project_path=project_path,
        installed_version=__version__,
        project_version=get_project_version(project_path),
    )


def format_report(report: DoctorReport, verbose: bool = False) -> str:
    """Format a doctor report for terminal display.

    Args:
        report: The DoctorReport to format.
        verbose: If True, show all checks including OK ones.

    Returns:
        Formatted string for terminal output.
    """
    lines = []

    # Header
    if report.project_path:
        lines.append(f"IdlerGear Doctor - {report.project_path}")
    else:
        lines.append("IdlerGear Doctor")
    lines.append(f"Installed version: {report.installed_version}")
    if report.project_version:
        lines.append(f"Project version: {report.project_version}")
    lines.append("")

    # Summary
    warn_count = sum(1 for c in report.checks if c.status == CheckStatus.WARNING)
    error_count = sum(1 for c in report.checks if c.status == CheckStatus.ERROR)
    info_count = sum(1 for c in report.checks if c.status == CheckStatus.INFO)

    if report.is_healthy:
        lines.append("✓ All checks passed")
    else:
        parts = []
        if error_count:
            parts.append(f"{error_count} error(s)")
        if warn_count:
            parts.append(f"{warn_count} warning(s)")
        if info_count:
            parts.append(f"{info_count} info")
        lines.append(f"Found issues: {', '.join(parts)}")
    lines.append("")

    # Details
    status_symbols = {
        CheckStatus.OK: "✓",
        CheckStatus.WARNING: "⚠",
        CheckStatus.ERROR: "✗",
        CheckStatus.INFO: "ℹ",
    }

    for check in report.checks:
        # Skip OK checks unless verbose
        if check.status == CheckStatus.OK and not verbose:
            continue

        symbol = status_symbols[check.status]
        lines.append(f"{symbol} [{check.name}] {check.message}")
        if check.fix:
            lines.append(f"  Fix: {check.fix}")
        if check.details and verbose:
            for key, value in check.details.items():
                if isinstance(value, list) and value:
                    lines.append(f"  {key}: {', '.join(str(v) for v in value)}")
                elif value:
                    lines.append(f"  {key}: {value}")

    # Recommendations
    if not report.is_healthy:
        lines.append("")
        lines.append("Quick fixes:")
        seen_fixes = set()
        for check in report.checks:
            if check.fix and check.fix not in seen_fixes:
                if check.status in (CheckStatus.ERROR, CheckStatus.WARNING):
                    lines.append(f"  {check.fix}")
                    seen_fixes.add(check.fix)

    return "\n".join(lines)
