"""Output formatting utilities for IdlerGear commands."""

import json
from enum import Enum
from typing import Any, Dict, List


class OutputFormat(str, Enum):
    """Supported output formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"
    GOOSE = "goose"  # Goose GUI optimized format


def format_output(data: Any, format: OutputFormat = OutputFormat.TEXT) -> str:
    """
    Format data for output.

    Args:
        data: Data to format (dict, list, str, etc.)
        format: Output format

    Returns:
        Formatted string
    """
    if format == OutputFormat.JSON:
        return format_json(data)
    elif format == OutputFormat.MARKDOWN:
        return format_markdown(data)
    elif format == OutputFormat.HTML:
        return format_html(data)
    elif format == OutputFormat.GOOSE:
        return format_goose(data)
    else:  # TEXT
        return format_text(data)


def format_json(data: Any) -> str:
    """Format as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_text(data: Any) -> str:
    """Format as plain text."""
    if isinstance(data, str):
        return data
    elif isinstance(data, dict):
        return "\n".join(f"{k}: {v}" for k, v in data.items())
    elif isinstance(data, list):
        return "\n".join(str(item) for item in data)
    else:
        return str(data)


def format_markdown(data: Any) -> str:
    """Format as Markdown."""
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        # Format dict as markdown
        lines = []
        for key, value in data.items():
            lines.append(f"## {key.replace('_', ' ').title()}\n")
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        lines.append(format_dict_as_list(item))
                    else:
                        lines.append(f"- {item}")
            elif isinstance(value, dict):
                lines.append(format_dict_as_table(value))
            else:
                lines.append(str(value))
            lines.append("")
        return "\n".join(lines)

    elif isinstance(data, list):
        # Format list as markdown
        lines = []
        for item in data:
            if isinstance(item, dict):
                lines.append(format_dict_as_list(item))
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)

    return str(data)


def format_html(data: Any) -> str:
    """Format as HTML."""
    if isinstance(data, str):
        return f"<pre>{data}</pre>"

    if isinstance(data, dict):
        html = ["<div class='idlergear-output'>"]
        for key, value in data.items():
            html.append(f"<h3>{key.replace('_', ' ').title()}</h3>")
            if isinstance(value, list):
                html.append("<ul>")
                for item in value:
                    if isinstance(item, dict):
                        html.append(f"<li>{format_dict_as_html_table(item)}</li>")
                    else:
                        html.append(f"<li>{item}</li>")
                html.append("</ul>")
            elif isinstance(value, dict):
                html.append(format_dict_as_html_table(value))
            else:
                html.append(f"<p>{value}</p>")
        html.append("</div>")
        return "\n".join(html)

    elif isinstance(data, list):
        html = ["<ul>"]
        for item in data:
            if isinstance(item, dict):
                html.append(f"<li>{format_dict_as_html_table(item)}</li>")
            else:
                html.append(f"<li>{item}</li>")
        html.append("</ul>")
        return "\n".join(html)

    return f"<pre>{data}</pre>"


def format_goose(data: Any) -> str:
    """
    Format for Goose GUI (rich markdown with badges, collapsibles).

    Optimized for visual rendering in Goose GUI with:
    - Badges for status/priority
    - Collapsible sections
    - Progress indicators
    - Visual hierarchy
    """
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        lines = []

        # Add summary badges if available
        if "status" in data or "priority" in data:
            badges = []
            if "status" in data:
                status_badge = f"![{data['status']}](https://img.shields.io/badge/status-{data['status']}-blue)"
                badges.append(status_badge)
            if "priority" in data:
                priority_color = {"high": "red", "medium": "orange", "low": "green"}.get(data["priority"], "gray")
                priority_badge = f"![{data['priority']}](https://img.shields.io/badge/priority-{data['priority']}-{priority_color})"
                badges.append(priority_badge)
            lines.append(" ".join(badges))
            lines.append("")

        # Format sections with collapsibles
        for key, value in data.items():
            if key in ["status", "priority"]:  # Already shown as badges
                continue

            section_title = key.replace('_', ' ').title()

            if isinstance(value, list) and len(value) > 5:
                # Collapsible for long lists
                lines.append(f"<details>")
                lines.append(f"<summary><strong>{section_title}</strong> ({len(value)} items)</summary>")
                lines.append("")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(format_dict_as_goose_card(item))
                    else:
                        lines.append(f"- {item}")
                lines.append("</details>")
                lines.append("")
            else:
                # Normal section
                lines.append(f"### {section_title}")
                lines.append("")
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            lines.append(format_dict_as_goose_card(item))
                        else:
                            lines.append(f"- {item}")
                elif isinstance(value, dict):
                    lines.append(format_dict_as_table(value))
                else:
                    lines.append(str(value))
                lines.append("")

        return "\n".join(lines)

    elif isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, dict):
                lines.append(format_dict_as_goose_card(item))
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)

    return str(data)


# Helper functions

def format_dict_as_list(d: Dict) -> str:
    """Format dict as markdown list item."""
    items = [f"**{k}**: {v}" for k, v in d.items()]
    return "- " + ", ".join(items)


def format_dict_as_table(d: Dict) -> str:
    """Format dict as markdown table."""
    lines = ["| Key | Value |", "|-----|-------|"]
    for k, v in d.items():
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


def format_dict_as_html_table(d: Dict) -> str:
    """Format dict as HTML table."""
    lines = ["<table>", "<tr><th>Key</th><th>Value</th></tr>"]
    for k, v in d.items():
        lines.append(f"<tr><td>{k}</td><td>{v}</td></tr>")
    lines.append("</table>")
    return "\n".join(lines)


def format_dict_as_goose_card(d: Dict) -> str:
    """Format dict as Goose GUI card."""
    lines = []

    # Title with badges
    title = d.get("title", d.get("name", "Item"))
    badges = []

    if "status" in d:
        status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "open": "📂", "closed": "✅"}.get(d["status"], "")
        badges.append(f"{status_emoji} `{d['status']}`")

    if "priority" in d:
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(d["priority"], "")
        badges.append(f"{priority_emoji} `{d['priority']}`")

    lines.append(f"**{title}** {' '.join(badges)}")

    # Body
    for k, v in d.items():
        if k in ["title", "name", "status", "priority"]:
            continue
        if isinstance(v, str) and len(v) < 100:
            lines.append(f"  - **{k}**: {v}")

    lines.append("")
    return "\n".join(lines)
