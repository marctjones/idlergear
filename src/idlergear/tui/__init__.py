"""IdlerGear Terminal User Interface (TUI).

Interactive dashboard for examining project knowledge state across all IdlerGear
knowledge types: tasks, notes, vision, plans, references, file registry, graph,
sessions, and daemon state.

Features:
- Full CRUD operations for tasks, references, notes
- Multi-agent coordination and messaging
- Priority management and bulk operations
- Interactive command palette
- Real-time daemon monitoring
"""

from .app import IdlerGearApp
from .modals import (
    TaskEditModal,
    ReferenceEditModal,
    NotePromoteModal,
    MessageModal,
    CommandPalette,
    NoteViewModal,
    ConfirmDeleteModal,
    BulkActionModal,
    QuickSelectModal,
)

__all__ = [
    "IdlerGearApp",
    "TaskEditModal",
    "ReferenceEditModal",
    "NotePromoteModal",
    "MessageModal",
    "CommandPalette",
    "NoteViewModal",
    "ConfirmDeleteModal",
    "BulkActionModal",
    "QuickSelectModal",
]
