"""Graph populators for indexing code and git data."""

from .git_populator import GitPopulator
from .code_populator import CodePopulator

__all__ = ["GitPopulator", "CodePopulator"]
