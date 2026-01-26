"""IdlerGear Terminal User Interface (TUI).

Interactive dashboard for examining project knowledge state across all IdlerGear
knowledge types: tasks, notes, vision, plans, references, file registry, graph,
sessions, and daemon state.
"""

from .app import IdlerGearApp

__all__ = ["IdlerGearApp"]
