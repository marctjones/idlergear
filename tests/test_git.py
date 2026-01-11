"""Tests for git operations."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from idlergear.git import GitServer


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repo\n")
        subprocess.run(
            ["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        yield repo_path


def test_git_status_clean(temp_repo):
    """Test git status on clean repo."""
    git = GitServer(allowed_repos=[str(temp_repo)])
    status = git.status(repo_path=str(temp_repo))

    assert status.branch == "master" or status.branch == "main"
    assert status.staged == []
    assert status.modified == []
    assert status.untracked == []
    assert status.conflicts == []
    assert status.last_commit is not None


def test_git_status_with_changes(temp_repo):
    """Test git status with staged and unstaged changes."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Create new file and stage it
    (temp_repo / "new.txt").write_text("new content")
    subprocess.run(
        ["git", "add", "new.txt"], cwd=temp_repo, check=True, capture_output=True
    )

    # Modify existing file (unstaged)
    (temp_repo / "README.md").write_text("# Modified\n")

    # Create untracked file
    (temp_repo / "untracked.txt").write_text("untracked")

    status = git.status(repo_path=str(temp_repo))

    assert "new.txt" in status.staged
    assert "README.md" in status.modified
    assert "untracked.txt" in status.untracked


def test_git_add_and_commit(temp_repo):
    """Test adding files and committing."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Create and add file
    (temp_repo / "test.txt").write_text("test content")
    result = git.add(["test.txt"], repo_path=str(temp_repo))
    assert "Staged" in result

    # Commit
    commit_hash = git.commit("Add test file", repo_path=str(temp_repo))
    assert len(commit_hash) == 40  # SHA-1 hash

    # Verify file is in last commit
    status = git.status(repo_path=str(temp_repo))
    assert status.last_commit["message"] == "Add test file"


def test_git_commit_with_task_id(temp_repo):
    """Test committing with task ID linkage."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    (temp_repo / "task_file.txt").write_text("task work")
    git.add(["task_file.txt"], repo_path=str(temp_repo))

    commit_hash = git.commit("Fix bug", repo_path=str(temp_repo), task_id=42)

    # Verify task ID is in commit message
    log = git.log(repo_path=str(temp_repo), max_count=1)
    assert len(log) == 1
    assert "Task: #42" in log[0].message


def test_git_log(temp_repo):
    """Test git log."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Create multiple commits
    for i in range(3):
        (temp_repo / f"file{i}.txt").write_text(f"content {i}")
        git.add([f"file{i}.txt"], repo_path=str(temp_repo))
        git.commit(f"Commit {i}", repo_path=str(temp_repo))

    # Get log
    log = git.log(repo_path=str(temp_repo), max_count=5)
    assert len(log) >= 3
    assert log[0].message == "Commit 2"  # Most recent first


def test_git_diff(temp_repo):
    """Test git diff."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Modify file
    (temp_repo / "README.md").write_text("# Modified README\nNew line\n")

    # Get unstaged diff
    diff = git.diff(repo_path=str(temp_repo))
    assert "Modified README" in diff
    assert "-# Test Repo" in diff

    # Stage and get staged diff
    git.add(["README.md"], repo_path=str(temp_repo))
    staged_diff = git.diff(repo_path=str(temp_repo), staged=True)
    assert "Modified README" in staged_diff


def test_git_branches(temp_repo):
    """Test branch operations."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # List branches
    branches = git.branch_list(repo_path=str(temp_repo))
    assert len(branches) >= 1
    assert any(b["current"] for b in branches)

    # Create new branch
    result = git.branch_create("feature", repo_path=str(temp_repo), checkout=False)
    assert "feature" in result

    # List again
    branches = git.branch_list(repo_path=str(temp_repo))
    assert len(branches) == 2

    # Checkout branch
    result = git.branch_checkout("feature", repo_path=str(temp_repo))
    assert "feature" in result

    # Verify current branch
    branches = git.branch_list(repo_path=str(temp_repo))
    feature_branch = next(b for b in branches if b["name"] == "feature")
    assert feature_branch["current"]

    # Switch back
    git.branch_checkout(
        "master" if branches[0]["name"] == "master" else "main",
        repo_path=str(temp_repo),
    )

    # Delete branch
    result = git.branch_delete("feature", repo_path=str(temp_repo))
    assert "feature" in result


def test_git_reset(temp_repo):
    """Test git reset."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Stage file
    (temp_repo / "test.txt").write_text("test")
    git.add(["test.txt"], repo_path=str(temp_repo))

    # Verify staged
    status = git.status(repo_path=str(temp_repo))
    assert "test.txt" in status.staged

    # Reset
    result = git.reset(files=["test.txt"], repo_path=str(temp_repo))
    assert "Unstaged" in result

    # Verify unstaged
    status = git.status(repo_path=str(temp_repo))
    assert "test.txt" not in status.staged
    assert "test.txt" in status.untracked


def test_git_show(temp_repo):
    """Test git show."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Create commit
    (temp_repo / "show_test.txt").write_text("content")
    git.add(["show_test.txt"], repo_path=str(temp_repo))
    commit_hash = git.commit("Test show", repo_path=str(temp_repo))

    # Show commit
    result = git.show(commit_hash, repo_path=str(temp_repo))
    assert result["hash"] == commit_hash
    assert result["message"] == "Test show"
    assert "show_test.txt" in result["files"]
    assert "diff" in result


def test_git_commit_task_integration(temp_repo):
    """Test commit_task helper."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Create file
    (temp_repo / "task_work.txt").write_text("work")

    # Commit with task (auto-adds)
    commit_hash = git.commit_task(
        task_id=99,
        message="Complete task work",
        repo_path=str(temp_repo),
        auto_add=True,
    )

    assert len(commit_hash) == 40

    # Verify commit message includes task
    log = git.log(repo_path=str(temp_repo), max_count=1)
    assert "Task: #99" in log[0].message
    assert "Complete task work" in log[0].message


def test_git_task_commits(temp_repo):
    """Test finding commits by task ID."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Create commits with task references
    for idx, i in enumerate([10, 20, 10]):  # Task 10 appears twice
        (temp_repo / f"task_{i}_{idx}.txt").write_text(f"work for task {i}")
        git.add([f"task_{i}_{idx}.txt"], repo_path=str(temp_repo))
        git.commit(f"Work on feature {idx}", repo_path=str(temp_repo), task_id=i)

    # Find task 10 commits
    commits = git.task_commits(task_id=10, repo_path=str(temp_repo))
    assert len(commits) == 2
    assert all("Task: #10" in c.message for c in commits)


def test_git_sync_tasks(temp_repo):
    """Test syncing tasks from commits."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Create commits with various task IDs
    for idx, task_id in enumerate([1, 2, 3, 2]):
        (temp_repo / f"file_{task_id}_{idx}.txt").write_text("work")
        git.add([f"file_{task_id}_{idx}.txt"], repo_path=str(temp_repo))
        git.commit(f"Work {idx}", repo_path=str(temp_repo), task_id=task_id)

    # Sync
    result = git.sync_tasks_from_commits(repo_path=str(temp_repo))

    assert result["total_commits"] >= 4
    assert result["task_commits"] == 4
    assert set(result["tasks_found"]) == {1, 2, 3}


def test_security_disallowed_repo():
    """Test that accessing disallowed repos fails."""
    git = GitServer(allowed_repos=["/allowed/path"])

    with pytest.raises(ValueError, match="not allowed"):
        git.status(repo_path="/tmp/evil")


def test_git_add_all(temp_repo):
    """Test git add --all."""
    git = GitServer(allowed_repos=[str(temp_repo)])

    # Create multiple files
    for i in range(3):
        (temp_repo / f"file{i}.txt").write_text(f"content {i}")

    # Add all
    result = git.add([], repo_path=str(temp_repo), all=True)
    assert "all" in result.lower()

    # Verify all staged
    status = git.status(repo_path=str(temp_repo))
    assert len(status.staged) == 3
