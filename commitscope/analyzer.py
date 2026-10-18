"""Read-only analytics for local Git repositories."""

from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
from typing import Any


if os.name == "nt" and shutil.which("git") is None:
    git_locations = (
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Git"
        / "cmd"
        / "git.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Git"
        / "cmd"
        / "git.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Programs"
        / "Git"
        / "cmd"
        / "git.exe",
    )
    for git_location in git_locations:
        if git_location.is_file():
            os.environ.setdefault("GIT_PYTHON_GIT_EXECUTABLE", str(git_location))
            break

from git import GitCommandError, Repo


def analyze_repository(repo_path: str, max_commits: int = 500) -> dict[str, Any]:
    """Summarize recent Git history without changing the repository.

    ``authors``, ``most_changed_files``, and ``monthly_activity`` are mappings
    from names/paths/months to counts. Author and file mappings contain at most
    ten entries; monthly activity includes every month in the analyzed window.
    File counts indicate how often a file appears in available commit stats,
    not whether that file is defective. Unavailable commit stats are omitted.
    """
    if isinstance(max_commits, bool) or not isinstance(max_commits, int):
        raise TypeError("max_commits must be an integer")
    if max_commits < 1:
        raise ValueError("max_commits must be at least 1")

    requested_path = Path(repo_path).expanduser()
    if not requested_path.exists():
        raise FileNotFoundError(f"Path does not exist: {requested_path}")
    if not requested_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {requested_path}")

    absolute_path = requested_path.resolve()
    repo = Repo(str(absolute_path), search_parent_directories=True)
    repository = Path(repo.working_tree_dir or repo.git_dir).resolve()

    authors: Counter[str] = Counter()
    changed_files: Counter[str] = Counter()
    monthly_activity: Counter[str] = Counter()
    insertions = 0
    deletions = 0
    commits_analyzed = 0

    if repo.head.is_valid():
        for commit in repo.iter_commits(max_count=max_commits):
            commits_analyzed += 1
            authors[commit.author.name or "(unknown)"] += 1
            month = datetime.fromtimestamp(commit.committed_date, timezone.utc)
            monthly_activity[month.strftime("%Y-%m")] += 1

            try:
                stats = commit.stats
            except (GitCommandError, OSError, ValueError):
                continue

            insertions += stats.total["insertions"]
            deletions += stats.total["deletions"]
            changed_files.update(stats.files.keys())

    return {
        "repository": str(repository),
        "commits_analyzed": commits_analyzed,
        "authors": dict(authors.most_common(10)),
        "most_changed_files": dict(changed_files.most_common(10)),
        "monthly_activity": dict(sorted(monthly_activity.items())),
        "insertions": insertions,
        "deletions": deletions,
    }
