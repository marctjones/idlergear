"""Built-in generators for IdlerGear.

These generators wrap the existing documentation generation modules
(docs.py, docs_rust.py, docs_dotnet.py) to integrate with the
generator configuration system.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from idlergear.generators.base import (
    BuiltinGenerator,
    GeneratorConfig,
    GeneratorResult,
    GeneratorType,
    ShellGenerator,
)


class PdocGenerator(BuiltinGenerator):
    """Python documentation generator using pdoc."""

    name = "pdoc"
    description = "Generate API docs from Python source code using pdoc"
    generator_type = GeneratorType.BUILTIN
    python_deps = ["pdoc"]

    def generate(
        self,
        input_path: Path,
        output_path: Path | None = None,
    ) -> GeneratorResult:
        """Generate Python documentation."""
        try:
            from idlergear.docs import generate_api_summary

            result = generate_api_summary(str(input_path), mode="standard")

            references = []
            if result:
                # Convert to reference format
                references.append({
                    "title": f"API: {input_path.name}",
                    "body": result,
                    "source": "generated",
                    "generator": self.name,
                })

            return GeneratorResult(
                success=True,
                references=references,
            )

        except ImportError:
            return GeneratorResult(
                success=False,
                errors=["pdoc package not installed. Install with: pip install pdoc"],
            )
        except Exception as e:
            return GeneratorResult(
                success=False,
                errors=[str(e)],
            )


class RustGenerator(BuiltinGenerator):
    """Rust documentation generator.

    Uses source parsing for documentation generation.
    Does not require external tools beyond Python.
    """

    name = "rust"
    description = "Generate API docs from Rust source code"
    generator_type = GeneratorType.BUILTIN
    requires = []  # No shell deps - uses Python parsing
    python_deps = []

    def generate(
        self,
        input_path: Path,
        output_path: Path | None = None,
    ) -> GeneratorResult:
        """Generate Rust documentation."""
        try:
            from idlergear.docs_rust import generate_rust_summary

            result = generate_rust_summary(input_path, mode="standard")

            references = []
            if result:
                # Result is a dict with summary info
                body = result.get("markdown", "") if isinstance(result, dict) else str(result)
                if body:
                    references.append({
                        "title": f"Rust API: {input_path.name}",
                        "body": body,
                        "source": "generated",
                        "generator": self.name,
                    })

            return GeneratorResult(
                success=True,
                references=references,
            )

        except Exception as e:
            return GeneratorResult(
                success=False,
                errors=[str(e)],
            )


class DotNetGenerator(BuiltinGenerator):
    """Documentation generator for .NET projects.

    Parses XML documentation comments from .NET projects.
    """

    name = "dotnet"
    description = "Generate API docs from .NET XML documentation"
    generator_type = GeneratorType.BUILTIN
    requires = []  # Uses XML parsing, no external deps
    python_deps = []

    def generate(
        self,
        input_path: Path,
        output_path: Path | None = None,
    ) -> GeneratorResult:
        """Generate .NET documentation."""
        try:
            from idlergear.docs_dotnet import generate_dotnet_summary

            result = generate_dotnet_summary(input_path, mode="standard")

            references = []
            if result:
                # Result is a dict with summary info
                body = result.get("markdown", "") if isinstance(result, dict) else str(result)
                if body:
                    references.append({
                        "title": f".NET API: {input_path.name}",
                        "body": body,
                        "source": "generated",
                        "generator": self.name,
                    })

            return GeneratorResult(
                success=True,
                references=references,
            )

        except Exception as e:
            return GeneratorResult(
                success=False,
                errors=[str(e)],
            )


class RustdocGenerator(ShellGenerator):
    """Rust documentation generator using cargo doc.

    Requires Rust toolchain with nightly for JSON output.
    """

    name = "rustdoc"
    description = "Generate API docs using cargo doc (requires Rust nightly)"
    generator_type = GeneratorType.SHELL
    requires = ["cargo"]

    def __init__(self, config: GeneratorConfig | None = None):
        """Initialize with default rustdoc config."""
        if config is None:
            config = GeneratorConfig(
                name=self.name,
                generator_type=self.generator_type,
                command="cargo +nightly doc --no-deps",
                env={"RUSTDOCFLAGS": "-Z unstable-options --output-format json"},
                output="target/doc/{crate}.json",
                requires=self.requires,
            )
        super().__init__(config)

    def detect(self) -> bool:
        """Check if rustdoc is available."""
        import shutil
        import subprocess

        # Check for cargo
        if not shutil.which("cargo"):
            return False

        # Check for nightly toolchain
        try:
            result = subprocess.run(
                ["rustup", "run", "nightly", "rustc", "--version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False
