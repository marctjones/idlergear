"""Logging configuration for TUI."""

import logging
import os
from pathlib import Path
from datetime import datetime


class ProjectContextFilter(logging.Filter):
    """Add project and agent context to log records."""

    def __init__(self, project_name: str, agent_id: str | None = None):
        """Initialize filter with project context.

        Args:
            project_name: Name of the project being worked on
            agent_id: ID of the AI assistant (if any)
        """
        super().__init__()
        self.project_name = project_name
        self.agent_id = agent_id or "unknown"

    def filter(self, record: logging.LogRecord) -> bool:
        """Add project and agent to record."""
        record.project = self.project_name
        record.agent = self.agent_id
        return True


def setup_tui_logging(
    project_name: str | None = None, log_dir: Path | None = None
) -> logging.Logger:
    """Set up logging for the TUI.

    Args:
        project_name: Name of the project (defaults to current directory name)
        log_dir: Directory for log files (defaults to ~/.idlergear/logs/)

    Returns:
        Configured logger instance
    """
    if log_dir is None:
        log_dir = Path.home() / ".idlergear" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # Get project name from current directory if not provided
    if project_name is None:
        project_name = Path.cwd().name

    # Get agent ID from environment (set by MCP server or AI assistant)
    agent_id = os.environ.get("IDLERGEAR_AGENT_ID")
    if agent_id is None:
        # Try to detect from other environment variables
        if os.environ.get("CLAUDE_CODE_SESSION"):
            agent_id = "claude-code"
        elif os.environ.get("GEMINI_SESSION"):
            agent_id = "gemini"
        elif os.environ.get("GOOSE_SESSION"):
            agent_id = "goose"
        else:
            agent_id = "manual"  # User ran directly

    # Create log file with project name and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize project name for filename
    safe_project = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)
    log_file = log_dir / f"tui_{safe_project}_{timestamp}.log"

    # Keep only last 10 log files
    log_files = sorted(log_dir.glob("tui_*.log"), key=lambda p: p.stat().st_mtime)
    for old_log in log_files[:-10]:
        old_log.unlink()

    # Configure logger
    logger = logging.getLogger("idlergear.tui")
    logger.setLevel(logging.DEBUG)

    # Add project context filter
    context_filter = ProjectContextFilter(project_name=project_name, agent_id=agent_id)
    logger.addFilter(context_filter)

    # File handler - detailed logs with project and agent context
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - [%(project)s/%(agent)s] - %(name)s - %(levelname)s - "
        "%(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Also log to stderr for critical errors (with project/agent context)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter(
        "[%(project)s/%(agent)s] %(levelname)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info(f"TUI logging initialized - log file: {log_file}")
    logger.info(f"Project: {project_name}, Agent: {agent_id}")
    logger.info(f"View logs: tail -f {log_file}")

    return logger


def get_logger() -> logging.Logger:
    """Get the TUI logger instance."""
    return logging.getLogger("idlergear.tui")
