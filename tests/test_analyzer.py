from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

GIT_EXECUTABLE = shutil.which("git")
if GIT_EXECUTABLE is None and os.name == "nt":
    for candidate in (
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
    ):
        if Path(candidate).is_file():
            GIT_EXECUTABLE = candidate
            break
if GIT_EXECUTABLE is not None:
    os.environ.setdefault("GIT_PYTHON_GIT_EXECUTABLE", GIT_EXECUTABLE)

from git import InvalidGitRepositoryError

from commitscope.analyzer import analyze_repository


def _git(repo_path: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        [GIT_EXECUTABLE or "git", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def _commit(
    repo_path: Path,
    message: str,
    date: str,
    *,
    author_name: str = "Test Author",
) -> None:
    _git(repo_path, "add", "-A")
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_DATE": date,
            "GIT_COMMITTER_DATE": date,
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    _git(repo_path, "commit", "-m", message, env=env)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _git(repo_path, "init", "-q")
    _git(repo_path, "config", "user.name", "Test Author")
    _git(repo_path, "config", "user.email", "test@example.com")
    return repo_path


def test_analyzes_single_commit_and_counts_author_file_and_insertions(
    git_repo: Path,
) -> None:
    (git_repo / "notes.txt").write_text("first line\nsecond line\n", encoding="utf-8")
    _commit(git_repo, "add notes", "2024-01-15T12:00:00+00:00")

    report = analyze_repository(str(git_repo))

    assert report["repository"] == str(git_repo.resolve())
    assert report["commits_analyzed"] == 1
    assert report["authors"] == {"Test Author": 1}
    assert report["most_changed_files"] == {"notes.txt": 1}
    assert report["insertions"] == 2
    assert report["deletions"] == 0
    assert report["monthly_activity"] == {"2024-01": 1}


def test_counts_deletions_and_modifications(git_repo: Path) -> None:
    (git_repo / "tracked.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    _commit(git_repo, "add tracked file", "2024-01-15T12:00:00+00:00")

    (git_repo / "tracked.txt").write_text("alpha\ngamma\n", encoding="utf-8")
    _commit(git_repo, "modify tracked file", "2024-02-15T12:00:00+00:00")

    (git_repo / "tracked.txt").unlink()
    _commit(git_repo, "delete tracked file", "2024-03-15T12:00:00+00:00")

    report = analyze_repository(str(git_repo))

    assert report["commits_analyzed"] == 3
    assert report["most_changed_files"] == {"tracked.txt": 3}
    assert report["insertions"] == 3
    assert report["deletions"] == 3
    assert report["monthly_activity"] == {
        "2024-01": 1,
        "2024-02": 1,
        "2024-03": 1,
    }


def test_counts_authors_separately(git_repo: Path) -> None:
    (git_repo / "one.txt").write_text("one\n", encoding="utf-8")
    _commit(git_repo, "first author", "2024-01-15T12:00:00+00:00")

    (git_repo / "two.txt").write_text("two\n", encoding="utf-8")
    _commit(
        git_repo,
        "second author",
        "2024-01-16T12:00:00+00:00",
        author_name="Another Author",
    )

    report = analyze_repository(str(git_repo))

    assert report["authors"] == {"Test Author": 1, "Another Author": 1}


def test_limits_the_recent_commit_window(git_repo: Path) -> None:
    for day in range(1, 4):
        (git_repo / f"file-{day}.txt").write_text(f"{day}\n", encoding="utf-8")
        _commit(git_repo, f"commit {day}", f"2024-01-0{day}T12:00:00+00:00")

    report = analyze_repository(str(git_repo), max_commits=2)

    assert report["commits_analyzed"] == 2
    assert report["authors"] == {"Test Author": 2}
    assert set(report["most_changed_files"]) == {"file-2.txt", "file-3.txt"}
    assert report["monthly_activity"] == {"2024-01": 2}


def test_rejects_nonexistent_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        analyze_repository(str(tmp_path / "missing"))


def test_rejects_file_instead_of_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("text", encoding="utf-8")

    with pytest.raises(NotADirectoryError, match="not a directory"):
        analyze_repository(str(file_path))


def test_rejects_directory_that_is_not_a_repository(tmp_path: Path) -> None:
    with pytest.raises(InvalidGitRepositoryError):
        analyze_repository(str(tmp_path))


@pytest.mark.parametrize("value", [0, -1])
def test_rejects_nonpositive_max_commits(git_repo: Path, value: int) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        analyze_repository(str(git_repo), max_commits=value)


@pytest.mark.parametrize("value", [True, 1.5, "2"])
def test_rejects_noninteger_max_commits(git_repo: Path, value: object) -> None:
    with pytest.raises(TypeError, match="must be an integer"):
        analyze_repository(str(git_repo), max_commits=value)  # type: ignore[arg-type]


def test_discovers_repository_from_nested_directory(git_repo: Path) -> None:
    (git_repo / "nested").mkdir()
    (git_repo / "tracked.txt").write_text("content\n", encoding="utf-8")
    _commit(git_repo, "add file", "2024-01-15T12:00:00+00:00")

    report = analyze_repository(str(git_repo / "nested"))

    assert report["repository"] == str(git_repo.resolve())
    assert report["commits_analyzed"] == 1


def test_repository_with_no_commits_returns_empty_report(git_repo: Path) -> None:
    report = analyze_repository(str(git_repo))

    assert report["commits_analyzed"] == 0
    assert report["authors"] == {}
    assert report["most_changed_files"] == {}
    assert report["monthly_activity"] == {}
    assert report["insertions"] == 0
    assert report["deletions"] == 0


def test_analysis_does_not_change_repository(git_repo: Path) -> None:
    (git_repo / "tracked.txt").write_text("content\n", encoding="utf-8")
    _commit(git_repo, "add file", "2024-01-15T12:00:00+00:00")
    before_head = _git(git_repo, "rev-parse", "HEAD")
    before_status = _git(git_repo, "status", "--porcelain")

    analyze_repository(str(git_repo))

    assert _git(git_repo, "rev-parse", "HEAD") == before_head
    assert _git(git_repo, "status", "--porcelain") == before_status
