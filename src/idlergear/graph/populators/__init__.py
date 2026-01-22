"""Graph populators for indexing code and git data."""

from .git_populator import GitPopulator
from .code_populator import CodePopulator
from .task_populator import TaskPopulator
from .commit_task_linker import CommitTaskLinker
from .reference_populator import ReferencePopulator
from .wiki_populator import WikiPopulator

__all__ = [
    "GitPopulator",
    "CodePopulator",
    "TaskPopulator",
    "CommitTaskLinker",
    "ReferencePopulator",
    "WikiPopulator",
]
