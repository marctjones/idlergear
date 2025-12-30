"""Storage utilities for markdown + YAML frontmatter files."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Returns (frontmatter_dict, body_content).
    """
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)

    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
            body = match.group(2)
            return frontmatter, body
        except yaml.YAMLError:
            return {}, content

    return {}, content


def render_frontmatter(frontmatter: dict[str, Any], body: str) -> str:
    """Render frontmatter dict and body to markdown with YAML frontmatter."""
    if frontmatter:
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_str}---\n{body}"
    return body


def get_next_id(directory: Path, prefix: str = "") -> int:
    """Get the next available ID for items in a directory."""
    if not directory.exists():
        return 1

    max_id = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)")

    for item in directory.iterdir():
        if item.is_file() and item.suffix == ".md":
            match = pattern.match(item.stem)
            if match:
                item_id = int(match.group(1))
                max_id = max(max_id, item_id)

    return max_id + 1


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a URL-friendly slug."""
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    slug = slug.strip("-")

    if len(slug) > max_length:
        # Truncate at word boundary
        slug = slug[:max_length].rsplit("-", 1)[0]

    return slug


def now_iso() -> str:
    """Return current UTC time in ISO format."""
    from datetime import timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
