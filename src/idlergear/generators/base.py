"""Base classes for documentation generators.

Generators transform source code, API specs, or other documentation sources
into structured reference documents for IdlerGear.
"""

from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class GeneratorType(str, Enum):
    """Types of generators."""

    BUILTIN = "built-in"  # Pure Python, no external deps
    SHELL = "shell"  # Invokes external command
    CUSTOM = "custom"  # User-defined via config


@dataclass
class GeneratorConfig:
    """Configuration for a generator.

    Attributes:
        name: Generator name (e.g., "rustdoc", "pdoc")
        enabled: Whether the generator is enabled
        generator_type: Type of generator (built-in, shell, custom)
        command: Shell command to run (for shell/custom generators)
        env: Environment variables to set
        output: Output path pattern (may contain placeholders)
        requires: List of shell commands required (e.g., ["cargo", "rustdoc"])
        python_deps: List of Python packages required (e.g., ["pdoc"])
        input_patterns: Glob patterns for input files
        options: Additional generator-specific options
    """

    name: str
    enabled: bool = True
    generator_type: GeneratorType = GeneratorType.BUILTIN
    command: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    output: str | None = None
    requires: list[str] = field(default_factory=list)
    python_deps: list[str] = field(default_factory=list)
    input_patterns: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "name": self.name,
            "enabled": self.enabled,
            "type": self.generator_type.value,
        }
        if self.command:
            result["command"] = self.command
        if self.env:
            result["env"] = self.env
        if self.output:
            result["output"] = self.output
        if self.requires:
            result["requires"] = self.requires
        if self.python_deps:
            result["python_deps"] = self.python_deps
        if self.input_patterns:
            result["input_patterns"] = self.input_patterns
        if self.options:
            result["options"] = self.options
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeneratorConfig:
        """Create from dictionary."""
        generator_type = data.get("type", "built-in")
        if isinstance(generator_type, str):
            generator_type = GeneratorType(generator_type)

        return cls(
            name=data["name"],
            enabled=data.get("enabled", True),
            generator_type=generator_type,
            command=data.get("command"),
            env=data.get("env", {}),
            output=data.get("output"),
            requires=data.get("requires", []),
            python_deps=data.get("python_deps", []),
            input_patterns=data.get("input_patterns", []),
            options=data.get("options", {}),
        )


@dataclass
class GeneratorResult:
    """Result of running a generator.

    Attributes:
        success: Whether generation succeeded
        references: List of generated reference documents
        errors: List of error messages
        warnings: List of warning messages
        output_path: Path where output was written (if applicable)
    """

    success: bool
    references: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    output_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "success": self.success,
            "references": self.references,
        }
        if self.errors:
            result["errors"] = self.errors
        if self.warnings:
            result["warnings"] = self.warnings
        if self.output_path:
            result["output_path"] = str(self.output_path)
        return result


class Generator(ABC):
    """Abstract base class for documentation generators.

    Generators take source code or specification files and produce
    structured reference documents.
    """

    name: str
    description: str = ""
    generator_type: GeneratorType = GeneratorType.BUILTIN
    requires: list[str] = []  # Shell commands required
    python_deps: list[str] = []  # Python packages required

    def __init__(self, config: GeneratorConfig | None = None):
        """Initialize generator with optional config."""
        self.config = config or GeneratorConfig(
            name=self.name,
            generator_type=self.generator_type,
            requires=self.requires,
            python_deps=self.python_deps,
        )

    def detect(self) -> bool:
        """Check if this generator can run on the current system.

        Returns True if all dependencies are available.
        """
        # Check shell dependencies
        for cmd in self.requires:
            if not self._check_command(cmd):
                return False

        # Check Python dependencies
        for pkg in self.python_deps:
            if not self._check_python_package(pkg):
                return False

        return True

    def get_missing_deps(self) -> dict[str, list[str]]:
        """Get missing dependencies.

        Returns:
            Dict with "shell" and "python" keys, each containing
            list of missing dependencies.
        """
        missing: dict[str, list[str]] = {"shell": [], "python": []}

        for cmd in self.requires:
            if not self._check_command(cmd):
                missing["shell"].append(cmd)

        for pkg in self.python_deps:
            if not self._check_python_package(pkg):
                missing["python"].append(pkg)

        return missing

    def _check_command(self, cmd: str) -> bool:
        """Check if a shell command is available."""
        # Handle commands with arguments like "cargo +nightly"
        base_cmd = cmd.split()[0]
        return shutil.which(base_cmd) is not None

    def _check_python_package(self, package: str) -> bool:
        """Check if a Python package is available."""
        try:
            __import__(package)
            return True
        except ImportError:
            return False

    @abstractmethod
    def generate(
        self,
        input_path: Path,
        output_path: Path | None = None,
    ) -> GeneratorResult:
        """Generate documentation from the input.

        Args:
            input_path: Path to input file or directory
            output_path: Optional path for output

        Returns:
            GeneratorResult with generated references
        """
        ...

    def get_status(self) -> dict[str, Any]:
        """Get generator status information."""
        available = self.detect()
        missing = self.get_missing_deps() if not available else {"shell": [], "python": []}

        return {
            "name": self.name,
            "type": self.generator_type.value,
            "description": self.description,
            "enabled": self.config.enabled if self.config else True,
            "available": available,
            "missing_deps": missing,
        }


class ShellGenerator(Generator):
    """Generator that runs an external shell command.

    Shell generators invoke external tools like rustdoc, protoc, etc.
    """

    generator_type = GeneratorType.SHELL

    def generate(
        self,
        input_path: Path,
        output_path: Path | None = None,
    ) -> GeneratorResult:
        """Run the shell command to generate documentation."""
        if not self.config or not self.config.command:
            return GeneratorResult(
                success=False,
                errors=["No command configured for shell generator"],
            )

        # Check dependencies first
        if not self.detect():
            missing = self.get_missing_deps()
            return GeneratorResult(
                success=False,
                errors=[f"Missing dependencies: {missing}"],
            )

        # Build command
        command = self.config.command
        # Substitute placeholders
        command = command.replace("{input}", str(input_path))
        if output_path:
            command = command.replace("{output}", str(output_path))

        # Run command
        try:
            env = dict(self.config.env) if self.config.env else {}
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **env},
                cwd=input_path if input_path.is_dir() else input_path.parent,
            )

            if result.returncode != 0:
                return GeneratorResult(
                    success=False,
                    errors=[result.stderr or f"Command failed with code {result.returncode}"],
                )

            return GeneratorResult(
                success=True,
                output_path=output_path,
            )

        except Exception as e:
            return GeneratorResult(
                success=False,
                errors=[str(e)],
            )


class BuiltinGenerator(Generator):
    """Generator implemented in pure Python.

    Built-in generators use Python libraries to parse and generate docs.
    """

    generator_type = GeneratorType.BUILTIN
