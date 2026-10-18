"""Command-line interface for CommitScope."""

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="commitscope",
        description="Analyze recent development activity in a local Git repository.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="repository directory to analyze (default: current directory)",
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=500,
        metavar="N",
        help="number of recent commits to analyze (default: 500)",
    )
    return parser


def _print_report(report: dict[str, object]) -> None:
    print("CommitScope - Git Repository Activity")
    print("=" * 40)
    print(f"Repository: {report['repository']}")
    print(f"Commits analyzed: {report['commits_analyzed']}")
    print(f"Lines added: {report['insertions']}")
    print(f"Lines deleted: {report['deletions']}")

    authors = report["authors"]
    print("\nTop contributors:")
    if authors:
        for author, count in authors.items():
            print(f"  {author}: {count} commit(s)")
    else:
        print("  No commits found.")

    files = report["most_changed_files"]
    print("\nMost frequently changed files:")
    if files:
        for file_path, count in files.items():
            print(f"  {file_path}: {count} change(s)")
    else:
        print("  No file statistics available.")

    activity = report["monthly_activity"]
    print("\nMonthly activity (UTC):")
    if activity:
        for month, count in activity.items():
            print(f"  {month}: {count} commit(s)")
    else:
        print("  No commits found.")


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        from commitscope.analyzer import analyze_repository
        from git import GitError, InvalidGitRepositoryError

        report = analyze_repository(args.path, args.max_commits)
    except ImportError as error:
        print(
            "commitscope: error: GitPython and an accessible Git executable are required. "
            "Install the project requirements and Git.",
            file=sys.stderr,
        )
        return 2
    except InvalidGitRepositoryError:
        print(
            f"commitscope: error: no Git repository found for '{args.path}' "
            "or its parent directories.",
            file=sys.stderr,
        )
        return 2
    except (FileNotFoundError, NotADirectoryError, GitError, ValueError, TypeError) as error:
        print(f"commitscope: error: {error}", file=sys.stderr)
        return 2

    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
