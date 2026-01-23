"""Graph populators for indexing code and git data."""

from .git_populator import GitPopulator
from .code_populator import CodePopulator
from .task_populator import TaskPopulator
from .commit_task_linker import CommitTaskLinker
from .reference_populator import ReferencePopulator
from .wiki_populator import WikiPopulator
from .person_populator import PersonPopulator
from .dependency_populator import DependencyPopulator
from .test_populator import TestPopulator

__all__ = [
    "GitPopulator",
    "CodePopulator",
    "TaskPopulator",
    "CommitTaskLinker",
    "ReferencePopulator",
    "WikiPopulator",
    "PersonPopulator",
    "DependencyPopulator",
    "TestPopulator",
]
