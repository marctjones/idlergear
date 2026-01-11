"""Shell-based backend implementation.

This module provides backend implementations that execute shell commands
defined in TOML configuration files. This allows adding new backends
(like GitHub, Jira, Linear) without code changes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from string import Template
from typing import Any


class ShellBackendError(Exception):
    """Error from shell backend execution."""

    pass


def _run_command(
    command: str,
    params: dict[str, Any],
    field_map: dict[str, str] | None = None,
) -> str:
    """Run a shell command with parameter substitution.

    Args:
        command: Command template with $param placeholders
        params: Parameters to substitute
        field_map: Optional mapping from backend field names to IdlerGear names

    Returns:
        Command stdout as string

    Raises:
        ShellBackendError: If command fails
    """
    # Substitute parameters into command
    # Use safe_substitute to leave unmatched $vars alone
    template = Template(command)

    # Convert params for template substitution
    template_params = {}
    for key, value in params.items():
        if value is None:
            template_params[key] = ""
        elif isinstance(value, list):
            template_params[key] = ",".join(str(v) for v in value)
        elif isinstance(value, bool):
            template_params[key] = "true" if value else "false"
        else:
            template_params[key] = str(value)

    cmd = template.safe_substitute(template_params)

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise ShellBackendError(
                f"Command failed (exit {result.returncode}): {result.stderr.strip()}"
            )

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        raise ShellBackendError(f"Command timed out: {cmd}")
    except Exception as e:
        raise ShellBackendError(f"Command error: {e}")


def _parse_json_output(output: str, field_map: dict[str, str] | None = None) -> Any:
    """Parse JSON output and apply field mapping.

    Args:
        output: JSON string from command
        field_map: Mapping from backend field names to IdlerGear names

    Returns:
        Parsed and mapped data
    """
    if not output:
        return None

    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        raise ShellBackendError(f"Invalid JSON output: {e}")

    if field_map:
        data = _apply_field_map(data, field_map)

    return data


def _apply_field_map(data: Any, field_map: dict[str, str]) -> Any:
    """Apply field mapping to data.

    Maps backend-specific field names to IdlerGear's canonical names.
    For example, GitHub's "number" -> IdlerGear's "id".
    """
    if isinstance(data, list):
        return [_apply_field_map(item, field_map) for item in data]

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Map the key if it's in the field_map
            new_key = field_map.get(key, key)
            result[new_key] = value
        return result

    return data


class ShellTaskBackend:
    """Shell-based task backend.

    Executes commands defined in configuration to manage tasks.
    """

    def __init__(
        self,
        config: dict[str, Any],
        project_path: Path | None = None,
    ):
        """Initialize shell task backend.

        Args:
            config: Backend configuration with commands section
            project_path: Optional project path
        """
        self.config = config
        self.project_path = project_path
        self.commands = config.get("commands", {})
        self.field_map = config.get("field_map", {})

    def create(
        self,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        priority: str | None = None,
        due: str | None = None,
    ) -> dict[str, Any]:
        """Create a new task."""
        cmd = self.commands.get("create")
        if not cmd:
            raise ShellBackendError("No 'create' command configured")

        output = _run_command(
            cmd,
            {
                "title": title,
                "body": body or "",
                "labels": labels or [],
                "assignees": assignees or [],
                "priority": priority or "",
                "due": due or "",
            },
        )

        return _parse_json_output(output, self.field_map)

    def list(self, state: str = "open") -> list[dict[str, Any]]:
        """List tasks filtered by state."""
        cmd = self.commands.get("list")
        if not cmd:
            raise ShellBackendError("No 'list' command configured")

        output = _run_command(cmd, {"state": state})
        result = _parse_json_output(output, self.field_map)
        return result if result else []

    def get(self, task_id: int) -> dict[str, Any] | None:
        """Get a task by ID."""
        cmd = self.commands.get("get")
        if not cmd:
            raise ShellBackendError("No 'get' command configured")

        try:
            output = _run_command(cmd, {"id": task_id})
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None

    def update(
        self,
        task_id: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        priority: str | None = None,
        due: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a task."""
        cmd = self.commands.get("update")
        if not cmd:
            raise ShellBackendError("No 'update' command configured")

        try:
            output = _run_command(
                cmd,
                {
                    "id": task_id,
                    "title": title or "",
                    "body": body or "",
                    "state": state or "",
                    "labels": labels or [],
                    "assignees": assignees or [],
                    "priority": priority or "",
                    "due": due or "",
                },
            )
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None

    def close(self, task_id: int) -> dict[str, Any] | None:
        """Close a task."""
        cmd = self.commands.get("close")
        if not cmd:
            # Fall back to update with state=closed
            return self.update(task_id, state="closed")

        try:
            output = _run_command(cmd, {"id": task_id})
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None

    def reopen(self, task_id: int) -> dict[str, Any] | None:
        """Reopen a closed task."""
        cmd = self.commands.get("reopen")
        if not cmd:
            # Fall back to update with state=open
            return self.update(task_id, state="open")

        try:
            output = _run_command(cmd, {"id": task_id})
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None


class ShellExploreBackend:
    """Shell-based exploration backend."""

    def __init__(
        self,
        config: dict[str, Any],
        project_path: Path | None = None,
    ):
        self.config = config
        self.project_path = project_path
        self.commands = config.get("commands", {})
        self.field_map = config.get("field_map", {})

    def create(
        self,
        title: str,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Create a new exploration."""
        cmd = self.commands.get("create")
        if not cmd:
            raise ShellBackendError("No 'create' command configured")

        output = _run_command(cmd, {"title": title, "body": body or ""})
        return _parse_json_output(output, self.field_map)

    def list(self, state: str = "open") -> list[dict[str, Any]]:
        """List explorations filtered by state."""
        cmd = self.commands.get("list")
        if not cmd:
            raise ShellBackendError("No 'list' command configured")

        output = _run_command(cmd, {"state": state})
        result = _parse_json_output(output, self.field_map)
        return result if result else []

    def get(self, explore_id: int) -> dict[str, Any] | None:
        """Get an exploration by ID."""
        cmd = self.commands.get("get")
        if not cmd:
            raise ShellBackendError("No 'get' command configured")

        try:
            output = _run_command(cmd, {"id": explore_id})
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None

    def update(
        self,
        explore_id: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an exploration."""
        cmd = self.commands.get("update")
        if not cmd:
            raise ShellBackendError("No 'update' command configured")

        try:
            output = _run_command(
                cmd,
                {
                    "id": explore_id,
                    "title": title or "",
                    "body": body or "",
                    "state": state or "",
                },
            )
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None

    def close(self, explore_id: int) -> dict[str, Any] | None:
        """Close an exploration."""
        cmd = self.commands.get("close")
        if not cmd:
            return self.update(explore_id, state="closed")

        try:
            output = _run_command(cmd, {"id": explore_id})
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None

    def reopen(self, explore_id: int) -> dict[str, Any] | None:
        """Reopen an exploration."""
        cmd = self.commands.get("reopen")
        if not cmd:
            return self.update(explore_id, state="open")

        try:
            output = _run_command(cmd, {"id": explore_id})
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None


class ShellReferenceBackend:
    """Shell-based reference backend."""

    def __init__(
        self,
        config: dict[str, Any],
        project_path: Path | None = None,
    ):
        self.config = config
        self.project_path = project_path
        self.commands = config.get("commands", {})
        self.field_map = config.get("field_map", {})

    def add(
        self,
        title: str,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Add a new reference document."""
        cmd = self.commands.get("add") or self.commands.get("create")
        if not cmd:
            raise ShellBackendError("No 'add' or 'create' command configured")

        output = _run_command(cmd, {"title": title, "body": body or ""})
        return _parse_json_output(output, self.field_map)

    def list(self) -> list[dict[str, Any]]:
        """List all reference documents."""
        cmd = self.commands.get("list")
        if not cmd:
            raise ShellBackendError("No 'list' command configured")

        output = _run_command(cmd, {})
        result = _parse_json_output(output, self.field_map)
        return result if result else []

    def get(self, title: str) -> dict[str, Any] | None:
        """Get a reference by title."""
        cmd = self.commands.get("get")
        if not cmd:
            raise ShellBackendError("No 'get' command configured")

        try:
            output = _run_command(cmd, {"title": title})
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None

    def get_by_id(self, ref_id: int) -> dict[str, Any] | None:
        """Get a reference by ID."""
        cmd = self.commands.get("get_by_id")
        if not cmd:
            # Try listing and filtering
            refs = self.list()
            for ref in refs:
                if ref.get("id") == ref_id:
                    return ref
            return None

        try:
            output = _run_command(cmd, {"id": ref_id})
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None

    def update(
        self,
        title: str,
        new_title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a reference document."""
        cmd = self.commands.get("update")
        if not cmd:
            raise ShellBackendError("No 'update' command configured")

        try:
            output = _run_command(
                cmd,
                {
                    "title": title,
                    "new_title": new_title or "",
                    "body": body or "",
                },
            )
            return _parse_json_output(output, self.field_map)
        except ShellBackendError:
            return None

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search reference documents."""
        cmd = self.commands.get("search")
        if not cmd:
            # Fall back to list and filter
            refs = self.list()
            query_lower = query.lower()
            return [
                r
                for r in refs
                if query_lower in r.get("title", "").lower()
                or query_lower in r.get("body", "").lower()
            ]

        output = _run_command(cmd, {"query": query})
        result = _parse_json_output(output, self.field_map)
        return result if result else []


def load_shell_backend_config(
    backend_name: str,
    backend_type: str,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Load shell backend configuration from TOML file.

    Looks for configuration in:
    1. .idlergear/backends/{backend_name}.toml
    2. ~/.config/idlergear/backends/{backend_name}.toml

    Args:
        backend_name: Name of the backend (e.g., "github")
        backend_type: Type of backend (e.g., "task")
        project_path: Optional project path

    Returns:
        Configuration dict for the backend type, or None if not found
    """
    import sys

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    from idlergear.config import find_idlergear_root

    if project_path is None:
        project_path = find_idlergear_root()

    # Search paths
    search_paths = []
    if project_path:
        search_paths.append(
            project_path / ".idlergear" / "backends" / f"{backend_name}.toml"
        )

    home = Path.home()
    search_paths.append(
        home / ".config" / "idlergear" / "backends" / f"{backend_name}.toml"
    )

    for config_path in search_paths:
        if config_path.exists():
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Return the section for the requested type
            if backend_type in config:
                return config[backend_type]

    return None
