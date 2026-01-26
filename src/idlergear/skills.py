"""Skill registry and assistant profiles for universal template system.

This module defines all IdlerGear skills/capabilities and assistant profiles
for generating configuration files from a single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Skill categories
SkillCategory = Literal[
    "session",
    "task",
    "note",
    "vision",
    "plan",
    "reference",
    "context",
    "daemon",
    "graph",
    "knowledge",
]


@dataclass
class SkillParameter:
    """Parameter for a skill/command."""

    name: str
    type: str  # "string", "integer", "boolean", "array"
    required: bool
    description: str
    default: str | None = None


@dataclass
class Skill:
    """Represents an IdlerGear skill/capability."""

    id: str  # "session-start", "task-create", etc.
    name: str  # "Start Session"
    category: SkillCategory
    command: str  # "idlergear context"
    description: str
    when_to_use: str
    examples: list[str]
    token_impact: Literal["high-savings", "medium-savings", "low-savings", "neutral"]
    parameters: list[SkillParameter] = field(default_factory=list)
    mcp_tool: str | None = None  # MCP tool name if available
    assistant_overrides: dict[str, dict] = field(default_factory=dict)


@dataclass
class AssistantProfile:
    """Profile for an AI assistant."""

    id: str  # "claude-code", "gemini", etc.
    name: str
    supports_mcp: bool
    supports_slash_commands: bool
    supports_hooks: bool
    config_file_format: Literal["markdown", "yaml", "json", "toml", "text"]
    config_file_name: str  # ".cursorrules", "GEMINI.md", etc.
    skill_template: str  # Path to Jinja2 template (relative to templates/)
    mcp_config_location: str | None = None  # Where MCP config goes
    unique_features: list[str] = field(default_factory=list)


# ============================================================================
# Skill Registry
# ============================================================================

SKILLS = [
    # Session Management
    Skill(
        id="session-start",
        name="Start Session",
        category="session",
        command="idlergear context",
        description="Load project context (vision, plan, tasks) at session start",
        when_to_use="ALWAYS at the start of EVERY session - this is MANDATORY",
        examples=[
            "idlergear context",
            "idlergear context --mode minimal",
            "idlergear context --mode detailed",
        ],
        token_impact="high-savings",
        mcp_tool="idlergear_context",
        assistant_overrides={
            "claude-code": {
                "slash_command": "/ig-start",
                "hook": "user-prompt-submit",
                "automated": True,
            },
        },
    ),
    Skill(
        id="session-end",
        name="End Session",
        category="session",
        command="idlergear session-end",
        description="Save session state for next time",
        when_to_use="At the end of a session to persist state",
        examples=["idlergear session-end"],
        token_impact="neutral",
        mcp_tool="idlergear_session_end",
    ),
    # Task Management
    Skill(
        id="task-create",
        name="Create Task",
        category="task",
        command="idlergear task create",
        description="Create a new task for actionable work",
        when_to_use="When you identify work that needs to be done, bugs, features, or technical debt",
        examples=[
            'idlergear task create "Add login feature"',
            'idlergear task create "Bug: Login redirects incorrectly" --label bug',
            'idlergear task create "Refactor auth module" --label tech-debt',
        ],
        token_impact="neutral",
        parameters=[
            SkillParameter("title", "string", True, "Task title/description"),
            SkillParameter("body", "string", False, "Detailed task body"),
            SkillParameter("label", "array", False, "Labels (bug, enhancement, etc.)"),
            SkillParameter("priority", "string", False, "Priority: high, medium, low"),
        ],
        mcp_tool="idlergear_task_create",
    ),
    Skill(
        id="task-list",
        name="List Tasks",
        category="task",
        command="idlergear task list",
        description="View open tasks",
        when_to_use="To see what work is available or check task status",
        examples=[
            "idlergear task list",
            "idlergear task list --preview",  # Titles only
            "idlergear task list --limit 10",
        ],
        token_impact="low-savings",
        mcp_tool="idlergear_task_list",
    ),
    Skill(
        id="task-show",
        name="Show Task",
        category="task",
        command="idlergear task show",
        description="View task details",
        when_to_use="To get full details of a specific task",
        examples=["idlergear task show 123"],
        token_impact="neutral",
        mcp_tool="idlergear_task_show",
    ),
    Skill(
        id="task-close",
        name="Close Task",
        category="task",
        command="idlergear task close",
        description="Mark task as completed",
        when_to_use="When you finish working on a task",
        examples=["idlergear task close 123"],
        token_impact="neutral",
        mcp_tool="idlergear_task_close",
    ),
    # Note Management
    Skill(
        id="note-create",
        name="Create Note",
        category="note",
        command="idlergear note create",
        description="Capture quick thoughts, decisions, or ideas",
        when_to_use="For ephemeral thoughts, research findings, or decisions that aren't tasks",
        examples=[
            'idlergear note create "OAuth2 vs JWT decision: going with JWT for simplicity"',
            'idlergear note create "Performance bottleneck in auth query" --tag explore',
            'idlergear note create "Idea: implement caching layer" --tag idea',
        ],
        token_impact="neutral",
        mcp_tool="idlergear_note_create",
    ),
    Skill(
        id="note-list",
        name="List Notes",
        category="note",
        command="idlergear note list",
        description="View recent notes",
        when_to_use="To review captured thoughts and decisions",
        examples=[
            "idlergear note list",
            "idlergear note list --tag explore",
        ],
        token_impact="neutral",
        mcp_tool="idlergear_note_list",
    ),
    Skill(
        id="note-promote",
        name="Promote Note",
        category="note",
        command="idlergear note promote",
        description="Convert note to task or reference",
        when_to_use="When a note becomes actionable (task) or needs to be permanent (reference)",
        examples=[
            "idlergear note promote 5 --to task",
            "idlergear note promote 3 --to reference",
        ],
        token_impact="neutral",
        mcp_tool="idlergear_note_promote",
    ),
    # Vision Management
    Skill(
        id="vision-show",
        name="Show Vision",
        category="vision",
        command="idlergear vision show",
        description="Display project vision and goals",
        when_to_use="To check project direction or remind yourself of goals",
        examples=["idlergear vision show"],
        token_impact="neutral",
        mcp_tool="idlergear_vision_show",
    ),
    Skill(
        id="vision-edit",
        name="Edit Vision",
        category="vision",
        command="idlergear vision edit",
        description="Update project vision",
        when_to_use="When project goals or direction changes",
        examples=["idlergear vision edit"],
        token_impact="neutral",
        mcp_tool="idlergear_vision_edit",
    ),
    # Reference Management
    Skill(
        id="reference-add",
        name="Add Reference",
        category="reference",
        command="idlergear reference add",
        description="Add permanent reference documentation",
        when_to_use="For technical concepts, acronyms, or important context that should be permanent",
        examples=[
            'idlergear reference add "OAuth2" --body "Authentication protocol..."',
            'idlergear reference add "API Rate Limits" --file docs/rate-limits.md',
        ],
        token_impact="neutral",
        mcp_tool="idlergear_reference_add",
    ),
    Skill(
        id="reference-search",
        name="Search References",
        category="reference",
        command="idlergear reference search",
        description="Search reference documentation",
        when_to_use="To find documented concepts or technical details",
        examples=['idlergear reference search "OAuth"'],
        token_impact="medium-savings",
        mcp_tool="idlergear_reference_search",
    ),
    # Context & Knowledge Graph
    Skill(
        id="graph-query-symbols",
        name="Query Symbols (Knowledge Graph)",
        category="graph",
        command="idlergear graph query-symbols",
        description="Find functions/classes by name (98% token savings vs grep)",
        when_to_use="ALWAYS use this instead of grep when searching for code symbols",
        examples=[
            "idlergear graph query-symbols --pattern calculate_relevance",
            "idlergear graph query-symbols --pattern AuthService --limit 5",
        ],
        token_impact="high-savings",
        mcp_tool="idlergear_graph_query_symbols",
        assistant_overrides={
            "claude-code": {
                "recommendation": "Use this instead of grep for 98% token savings",
            },
        },
    ),
    Skill(
        id="graph-query-task",
        name="Query Task Context (Knowledge Graph)",
        category="graph",
        command="idlergear graph query-task",
        description="Get all context for a task (files, commits, symbols) - 98% token savings",
        when_to_use="To understand what a task involves without reading multiple files",
        examples=["idlergear graph query-task --task-id 278"],
        token_impact="high-savings",
        mcp_tool="idlergear_graph_query_task",
    ),
    Skill(
        id="graph-populate",
        name="Populate Knowledge Graph",
        category="graph",
        command="idlergear graph populate-all",
        description="Index git history and code symbols for fast queries",
        when_to_use="First-time setup or after significant code changes",
        examples=[
            "idlergear graph populate-all",
            "idlergear graph populate-git --max-commits 100",
        ],
        token_impact="high-savings",
        mcp_tool="idlergear_graph_populate_all",
    ),
    # Knowledge Management
    Skill(
        id="knowledge-decay",
        name="Knowledge Decay Stats",
        category="knowledge",
        command="idlergear knowledge decay",
        description="Show relevance scores and decay statistics",
        when_to_use="To understand knowledge health and identify stale items",
        examples=[
            "idlergear knowledge decay",
            "idlergear knowledge decay --recalculate",
        ],
        token_impact="neutral",
    ),
    Skill(
        id="knowledge-stale",
        name="Show Stale Knowledge",
        category="knowledge",
        command="idlergear knowledge stale",
        description="List low-relevance items",
        when_to_use="To identify old, unaccessed knowledge for cleanup",
        examples=["idlergear knowledge stale --threshold 0.2"],
        token_impact="neutral",
    ),
    # Daemon (Multi-Agent Coordination)
    Skill(
        id="daemon-start",
        name="Start Daemon",
        category="daemon",
        command="idlergear daemon start",
        description="Start daemon for multi-agent coordination",
        when_to_use="When working with multiple AI assistants simultaneously",
        examples=["idlergear daemon start"],
        token_impact="neutral",
        mcp_tool="idlergear_daemon_start",
    ),
]


# ============================================================================
# Assistant Profiles
# ============================================================================

ASSISTANTS = [
    AssistantProfile(
        id="claude-code",
        name="Claude Code",
        supports_mcp=True,
        supports_slash_commands=True,
        supports_hooks=True,
        config_file_format="markdown",
        config_file_name="CLAUDE.md",
        skill_template="skills/claude-code.md.j2",
        mcp_config_location=".mcp.json",
        unique_features=[
            "Full MCP integration (60+ tools)",
            "Lifecycle hooks (user-prompt-submit, pre-commit)",
            "Slash commands (/ig-start, /ig-task)",
            "Always-on rules (.claude/rules/)",
            "98% token savings via knowledge graph",
        ],
    ),
    AssistantProfile(
        id="cursor",
        name="Cursor AI",
        supports_mcp=False,  # Planned
        supports_slash_commands=False,
        supports_hooks=False,
        config_file_format="text",
        config_file_name=".cursorrules",
        skill_template="skills/cursor.md.j2",
        mcp_config_location=None,  # Not yet available
        unique_features=[
            "VS Code fork with AI integration",
            "Large user base",
            "MCP support planned",
        ],
    ),
    AssistantProfile(
        id="gemini",
        name="Gemini CLI",
        supports_mcp=False,  # Planned for Q1 2026
        supports_slash_commands=True,
        supports_hooks=False,  # Unknown
        config_file_format="markdown",
        config_file_name="GEMINI.md",
        skill_template="skills/gemini.md.j2",
        mcp_config_location="~/.gemini/settings.json",
        unique_features=[
            "2M token context window - use detailed mode",
            "Multimodal - analyze diagrams/screenshots",
            "MCP support planned Q1 2026",
        ],
    ),
    AssistantProfile(
        id="aider",
        name="Aider",
        supports_mcp=False,
        supports_slash_commands=True,
        supports_hooks=False,
        config_file_format="yaml",
        config_file_name=".aider.conf.yml",
        skill_template="skills/aider.md.j2",
        mcp_config_location=None,
        unique_features=[
            "Automatic git commits",
            "/run command for shell execution",
            "lint-cmd and test-cmd hooks",
        ],
    ),
    AssistantProfile(
        id="copilot",
        name="GitHub Copilot CLI",
        supports_mcp=False,
        supports_slash_commands=False,
        supports_hooks=False,
        config_file_format="markdown",
        config_file_name="COPILOT.md",
        skill_template="skills/copilot.md.j2",
        mcp_config_location=None,
        unique_features=[
            "GitHub ecosystem integration",
            "Large user base",
        ],
    ),
    AssistantProfile(
        id="cline",
        name="Cline (VS Code)",
        supports_mcp=True,
        supports_slash_commands=False,
        supports_hooks=False,
        config_file_format="markdown",
        config_file_name="cline_docs/idlergear-guide.md",
        skill_template="skills/cline.md.j2",
        mcp_config_location=".vscode/settings.json",
        unique_features=[
            "VS Code extension",
            "MCP support available",
        ],
    ),
    AssistantProfile(
        id="goose",
        name="Goose (Block)",
        supports_mcp=True,
        supports_slash_commands=False,
        supports_hooks=False,
        config_file_format="text",
        config_file_name=".goosehints",
        skill_template="skills/goose.md.j2",
        mcp_config_location="~/.config/goose/config.yaml",
        unique_features=[
            "MCP extension support",
            "Multiple context file names",
        ],
    ),
]


# ============================================================================
# Helper Functions
# ============================================================================


def get_skills_by_category() -> dict[SkillCategory, list[Skill]]:
    """Group skills by category."""
    categorized: dict[SkillCategory, list[Skill]] = {}
    for skill in SKILLS:
        if skill.category not in categorized:
            categorized[skill.category] = []
        categorized[skill.category].append(skill)
    return categorized


def get_assistant(assistant_id: str) -> AssistantProfile | None:
    """Get assistant profile by ID."""
    for assistant in ASSISTANTS:
        if assistant.id == assistant_id:
            return assistant
    return None


def get_skill(skill_id: str) -> Skill | None:
    """Get skill by ID."""
    for skill in SKILLS:
        if skill.id == skill_id:
            return skill
    return None


def get_high_impact_skills() -> list[Skill]:
    """Get skills with high token savings."""
    return [s for s in SKILLS if s.token_impact == "high-savings"]
