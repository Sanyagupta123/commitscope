# CommitScope

CommitScope is a small, read-only command-line tool that summarizes recent
activity in a local Git repository. It uses the repository's actual commit
history to report contributors, frequently changed files, monthly commit
activity, and line-change totals.

## Problem

Git history contains useful signals about how a project changes, but manually
reviewing commits to find contributors, active months, or often-touched files
can be tedious. CommitScope provides a quick, local summary without sending
repository data to an external service.

## Features

- Analyzes the most recent commits, with a configurable history limit.
- Counts commits by author and file appearances in available commit statistics.
- Groups commits by month using UTC commit timestamps.
- Totals insertions and deletions when Git provides commit statistics.
- Discovers the repository root when run from a nested directory.
- Does not change the analyzed repository.

Frequently changed files are not necessarily defective or risky; the count is
only how often a filename appears in available commit statistics.

## Technology

- Python 3.10+
- GitPython
- `argparse` and `collections.Counter` from the Python standard library
- pytest
- Git executable

## Project structure

```text
commitscope/
├── commitscope/
│   ├── __init__.py
│   ├── analyzer.py
│   └── cli.py
├── tests/
│   └── test_analyzer.py
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation

Install Python 3.10 or newer and Git. Confirm that `python` and `git` can be
run from your terminal. On Windows, the Git installer can add Git to `PATH`;
if Git is installed but unavailable in a terminal, add its `cmd` directory
(commonly `C:\Program Files\Git\cmd`) to `PATH`.

From the project directory, create and activate a virtual environment.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, either adjust the execution policy for your
user according to your organization's guidance or run the commands using
`.venv\Scripts\python.exe` without activating the environment.

### Git Bash, macOS, and Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project requirements:

```console
python -m pip install -r requirements.txt
```

## Usage

Run these commands from the project directory with the virtual environment
active:

```console
python -m commitscope.cli .
python -m commitscope.cli ../tracelens --max-commits 200
python -m commitscope.cli . --max-commits 100
python -m commitscope.cli --help
```

The path is optional and defaults to the current directory. `--max-commits`
defaults to 500 and must be a positive integer. A relative or `~`-prefixed
path is accepted. The analyzer searches parent directories for the Git root.

### Illustrative report format

The following values are illustrative only, not the output of a real
repository:

```text
CommitScope - Git Repository Activity
========================================
Repository: /path/to/local/project
Commits analyzed: 42
Lines added: 1234
Lines deleted: 321

Top contributors:
  Contributor Name: 25 commit(s)

Most frequently changed files:
  src/module.py: 8 change(s)

Monthly activity (UTC):
  2025-01: 12 commit(s)
```

To analyze another local repository, pass its directory as the positional
argument. For example, `python -m commitscope.cli C:\work\project` in
PowerShell or `python -m commitscope.cli ~/work/project` in Git Bash.

## Testing

The tests create temporary repositories, configure a local author, and commit
test data only inside pytest's temporary directories:

```console
python -m pytest
```

## Known limitations

- Only the selected recent commit window is examined. A smaller
  `--max-commits` value does not represent the repository's full history.
- Merge commits can affect insertion and deletion totals.
- Root commits and binary files can have special or limited statistics.
- If a commit diff/statistic is unavailable, its author and month are still
  counted, but its file and line statistics are omitted.
- Different author names in Git history are counted separately, even if they
  belong to the same person.
- Monthly activity is grouped by the commit timestamp converted to UTC.
- Frequently changed files are not automatically bugs, defects, or security
  risks.

## Troubleshooting

- **Git is missing or not found:** Install Git and make sure the Git
  executable is on `PATH`; check with `git --version`.
- **Invalid repository path:** Ensure the path exists, is a directory, and is
  inside a Git working tree (or is a Git repository directory). CommitScope
  prints an error and exits with a non-zero status otherwise.
- **Python cannot import `commitscope`:** Run commands from this project
  directory and use the Python interpreter where the requirements were
  installed. From elsewhere, invoke the module with the project directory as
  the working directory or install the project as a package.
