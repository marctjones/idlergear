"""Template engine for generating assistant configuration files.

Uses Jinja2 to generate configuration files from a single source of truth.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from idlergear.skills import (
    ASSISTANTS,
    SKILLS,
    AssistantProfile,
    Skill,
    get_assistant,
    get_skills_by_category,
)


class TemplateEngine:
    """Renders configuration files for AI assistants from templates."""

    def __init__(self, template_dir: Path | None = None):
        """Initialize template engine.

        Args:
            template_dir: Directory containing Jinja2 templates.
                         If None, uses src/idlergear/templates/
        """
        if template_dir is None:
            # Default to templates/ directory next to this file
            template_dir = Path(__file__).parent / "templates"

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["category_title"] = lambda cat: cat.replace("_", " ").title()

    def render_skills_file(
        self,
        assistant_id: str,
        project_name: str | None = None,
    ) -> str:
        """Render SKILLS reference file for specific assistant.

        Args:
            assistant_id: ID of the assistant (claude-code, gemini, etc.)
            project_name: Optional project name for personalization

        Returns:
            Rendered content as string

        Example:
            >>> engine = TemplateEngine()
            >>> content = engine.render_skills_file("claude-code", "my-project")
        """
        assistant = get_assistant(assistant_id)
        if not assistant:
            raise ValueError(f"Unknown assistant: {assistant_id}")

        skills_by_category = get_skills_by_category()

        # Load template
        template = self.env.get_template(assistant.skill_template)

        # Render
        return template.render(
            assistant=assistant,
            skills=SKILLS,
            skills_by_category=skills_by_category,
            project_name=project_name or "this project",
            high_impact_skills=[s for s in SKILLS if s.token_impact == "high-savings"],
        )

    def render_agents_md(self, project_name: str | None = None) -> str:
        """Render universal AGENTS.md file.

        This file is assistant-agnostic and provides basic instructions.

        Args:
            project_name: Optional project name

        Returns:
            Rendered AGENTS.md content
        """
        template = self.env.get_template("agents/base.md.j2")

        return template.render(
            project_name=project_name or "this project",
            skills_by_category=get_skills_by_category(),
            assistants=ASSISTANTS,
        )

    def render_config_file(
        self,
        assistant_id: str,
        project_name: str | None = None,
        config_data: dict[str, Any] | None = None,
    ) -> str:
        """Render assistant-specific config file.

        Args:
            assistant_id: ID of the assistant
            project_name: Optional project name
            config_data: Optional additional data for template

        Returns:
            Rendered config content

        Example:
            >>> engine.render_config_file("aider", "my-project")
            # Returns .aider.conf.yml content
        """
        assistant = get_assistant(assistant_id)
        if not assistant:
            raise ValueError(f"Unknown assistant: {assistant_id}")

        # Determine template name from config file name
        # .cursorrules -> cursorrules.j2
        # .aider.conf.yml -> aider.conf.yml.j2
        config_base = assistant.config_file_name.lstrip(".")
        template_name = f"configs/{config_base}.j2"

        try:
            template = self.env.get_template(template_name)
        except Exception:
            # Template might not exist for all assistants
            return ""

        data = config_data or {}
        data["project_name"] = project_name or "this project"
        data["assistant"] = assistant

        return template.render(**data)

    def render_mcp_config(
        self,
        assistant_id: str,
        idlergear_mcp_command: str = "idlergear",
    ) -> str:
        """Render MCP server configuration.

        Args:
            assistant_id: ID of the assistant
            idlergear_mcp_command: Command to run MCP server

        Returns:
            Rendered MCP config (JSON, YAML, or TOML depending on assistant)

        Example:
            >>> engine.render_mcp_config("claude-code")
            # Returns .mcp.json content
        """
        assistant = get_assistant(assistant_id)
        if not assistant or not assistant.supports_mcp:
            return ""

        # Most assistants use similar MCP config format
        if assistant.id == "claude-code":
            # .mcp.json format
            return f"""{{
  "mcpServers": {{
    "idlergear": {{
      "command": "{idlergear_mcp_command}",
      "args": ["mcp"],
      "env": {{}}
    }}
  }}
}}
"""
        elif assistant.id == "gemini":
            # ~/.gemini/settings.json format
            return f"""{{
  "mcpServers": {{
    "idlergear": {{
      "command": "{idlergear_mcp_command}",
      "args": ["mcp"],
      "timeout": 30000
    }}
  }}
}}
"""
        elif assistant.id == "cline":
            # .vscode/settings.json format (partial)
            return f"""{{
  "cline.mcpServers": {{
    "idlergear": {{
      "command": "{idlergear_mcp_command}",
      "args": ["mcp"]
    }}
  }}
}}
"""
        elif assistant.id == "goose":
            # ~/.config/goose/config.yaml format
            return f"""extensions:
  idlergear:
    type: mcp
    command: {idlergear_mcp_command}
    args:
      - mcp
"""

        return ""

    def get_output_filename(self, assistant_id: str, file_type: str) -> str:
        """Get output filename for generated file.

        Args:
            assistant_id: ID of the assistant
            file_type: Type of file ("skills", "config", "mcp")

        Returns:
            Filename to write to

        Example:
            >>> engine.get_output_filename("claude-code", "skills")
            "CLAUDE.md"
        """
        assistant = get_assistant(assistant_id)
        if not assistant:
            raise ValueError(f"Unknown assistant: {assistant_id}")

        if file_type == "skills":
            return assistant.config_file_name

        elif file_type == "config":
            return assistant.config_file_name

        elif file_type == "mcp":
            if assistant.mcp_config_location:
                return assistant.mcp_config_location
            return ""

        return ""


def render_all_assistants(
    output_dir: Path,
    project_name: str | None = None,
    assistants: list[str] | None = None,
) -> dict[str, list[Path]]:
    """Render configuration files for all (or specified) assistants.

    Args:
        output_dir: Directory to write files to
        project_name: Optional project name
        assistants: Optional list of assistant IDs (default: all)

    Returns:
        Dict mapping assistant IDs to list of generated file paths

    Example:
        >>> files = render_all_assistants(Path("/project"), "my-app")
        >>> files["claude-code"]
        [Path("/project/CLAUDE.md"), Path("/project/.mcp.json")]
    """
    engine = TemplateEngine()
    generated: dict[str, list[Path]] = {}

    assistant_ids = assistants or [a.id for a in ASSISTANTS]

    for assistant_id in assistant_ids:
        assistant = get_assistant(assistant_id)
        if not assistant:
            continue

        files: list[Path] = []

        # Generate skills file
        skills_content = engine.render_skills_file(assistant_id, project_name)
        if skills_content:
            skills_file = output_dir / assistant.config_file_name
            skills_file.parent.mkdir(parents=True, exist_ok=True)
            skills_file.write_text(skills_content)
            files.append(skills_file)

        # Generate MCP config if supported
        if assistant.supports_mcp and assistant.mcp_config_location:
            mcp_content = engine.render_mcp_config(assistant_id)
            if mcp_content:
                mcp_file = output_dir / assistant.mcp_config_location
                mcp_file.parent.mkdir(parents=True, exist_ok=True)
                mcp_file.write_text(mcp_content)
                files.append(mcp_file)

        generated[assistant_id] = files

    # Generate universal AGENTS.md
    agents_content = engine.render_agents_md(project_name)
    agents_file = output_dir / "AGENTS.md"
    agents_file.write_text(agents_content)

    return generated
