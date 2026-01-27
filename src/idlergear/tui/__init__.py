"""IdlerGear Terminal User Interface (TUI).

Interactive dashboard with multi-view architecture and real-time AI observability.

Features:
- 6 organizational views (By Type, By Project, By Time, Gaps, Activity, AI Monitor)
- Right-hand detail pane (60/40 split) with automatic updates
- Real-time AI activity monitoring (View 6 - THE KILLER FEATURE!)
- Multi-agent coordination via daemon
- Tree navigation with arrow keys or vi-style (hjkl)
- Rich text formatting with colors and markdown

Navigation:
- Press 1-6 to switch between views
- Use arrow keys or hjkl to navigate trees
- Select items to see full details in right pane
- Press ? for help
- Press r to refresh
- Press q to quit

Views:
1. By Type - Tasks, notes, references, files organized by type
2. By Project - Grouped by milestone/project
3. By Time - Recent activity (today, week, month)
4. Gaps - Knowledge gaps by severity with fix suggestions
5. Activity - Recent events feed with proactive suggestions
6. AI Monitor - Real-time AI assistant activity (phase, action, plan, uncertainties)
"""

from .app import IdlerGearApp

__all__ = ["IdlerGearApp"]
