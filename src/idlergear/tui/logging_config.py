"""Logging configuration for TUI."""

import logging
from pathlib import Path
from datetime import datetime


def setup_tui_logging(log_dir: Path | None = None) -> logging.Logger:
    """Set up logging for the TUI.

    Args:
        log_dir: Directory for log files (defaults to ~/.idlergear/logs/)

    Returns:
        Configured logger instance
    """
    if log_dir is None:
        log_dir = Path.home() / ".idlergear" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"tui_{timestamp}.log"

    # Keep only last 10 log files
    log_files = sorted(log_dir.glob("tui_*.log"), key=lambda p: p.stat().st_mtime)
    for old_log in log_files[:-10]:
        old_log.unlink()

    # Configure logger
    logger = logging.getLogger("idlergear.tui")
    logger.setLevel(logging.DEBUG)

    # File handler - detailed logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Also log to stderr for critical errors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info(f"TUI logging initialized - log file: {log_file}")
    logger.info(f"View logs: tail -f {log_file}")

    return logger


def get_logger() -> logging.Logger:
    """Get the TUI logger instance."""
    return logging.getLogger("idlergear.tui")
