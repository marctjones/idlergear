"""
Note Service - Core note management logic

This service provides note operations used by both CLI and MCP server.
"""

from typing import Optional


class NoteService:
    """Core note management service"""

    def __init__(self, backend=None):
        """
        Initialize note service

        Args:
            backend: Note backend instance (defaults to auto-detected backend)
        """
        if backend is None:
            from idlergear.backends.registry import get_backend

            backend = get_backend("note")
        self.backend = backend

    def list_notes(
        self, tag: Optional[str] = None, limit: Optional[int] = None, preview: bool = False
    ) -> list[dict]:
        """
        List notes with filtering

        Args:
            tag: Filter by tag (e.g., "explore", "idea")
            limit: Maximum number of results
            preview: Strip note content for token efficiency

        Returns:
            List of note dictionaries
        """
        # Get notes from backend
        notes = self.backend.list(tag=tag)

        # Apply limit if specified
        if limit and len(notes) > limit:
            notes = notes[:limit]

        # Strip content if preview mode (token-efficient)
        if preview:
            notes = [
                {
                    "id": n.get("id"),
                    "tags": n.get("tags", []),
                    "created": n.get("created"),
                }
                for n in notes
            ]

        return notes

    def get_note(self, note_id: int) -> Optional[dict]:
        """
        Get a single note by ID

        Args:
            note_id: Note ID

        Returns:
            Note dictionary or None if not found
        """
        return self.backend.get(note_id)

    def create_note(self, content: str, tags: Optional[list[str]] = None) -> dict:
        """
        Create a new note

        Args:
            content: Note content
            tags: Optional tags (e.g., ["explore", "idea"])

        Returns:
            Created note dictionary
        """
        return self.backend.create(content, tags=tags)

    def update_note(
        self,
        note_id: int,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """
        Update a note

        Args:
            note_id: Note ID
            content: New content
            tags: New tags

        Returns:
            Updated note dictionary or None if not found
        """
        return self.backend.update(note_id, content=content, tags=tags)

    def delete_note(self, note_id: int) -> bool:
        """
        Delete a note

        Args:
            note_id: Note ID

        Returns:
            True if deleted, False if not found
        """
        return self.backend.delete(note_id)

    def promote_note(self, note_id: int, to_type: str) -> dict:
        """
        Promote a note to another type (task, reference)

        Args:
            note_id: Note ID
            to_type: Target type ("task" or "reference")

        Returns:
            Result dictionary with promoted item

        Raises:
            ValueError: If note not found or invalid to_type
        """
        from idlergear.notes import promote_note

        return promote_note(note_id, to_type)
