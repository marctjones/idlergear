"""IdlerGear - Knowledge management API for AI-assisted development."""

try:
    from importlib.metadata import version as get_version

    __version__ = get_version("idlergear")
except Exception:
    # Fallback for development/editable installs
    __version__ = "0.3.1"
