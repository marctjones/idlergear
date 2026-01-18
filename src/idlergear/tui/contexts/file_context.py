"""File context provider."""

from pathlib import Path


class FileContext:
    """Provides file metadata context."""

    def get_info(self, file_path: str) -> dict:
        """Get file metadata."""
        path = Path(file_path)

        if not path.exists():
            return {"exists": False, "size": 0, "lines": 0}

        try:
            size = path.stat().st_size
            lines = len(path.read_text().splitlines()) if path.is_file() else 0
        except (OSError, UnicodeDecodeError):
            size = 0
            lines = 0

        return {"exists": True, "size": size, "lines": lines}
