# project-doctor

## Workspace discovery — updated 2026-11-18

`list --root` always lists projects **under** the workspace, even if the workspace
itself contains package.json or .git. Use `inspect . --root <path>` to inspect
that directory itself. An empty workspace returns an empty list.

Hidden directories, dependency/build directories and directory symlinks are
excluded in both modes. Recursive mode includes nested repositories (for example
smartwatch-os/RabuWatchOS), searches at most four levels and stops at each project
boundary instead of listing a monorepo's internal packages as separate projects.
Discovery is generic: visible personal repositories are not automatically excluded.
Review the list before using it to drive any external automation.

GitHub Actions runs unit and CLI regression tests on Python 3.11, 3.12 and 3.13.
The workflow's remote result must be checked after pushing; local tests do not
prove that GitHub Actions has run.

`project-doctor` is a small, dependency-free CLI for taking a read-only inventory of a workspace containing multiple repositories. It is designed for a portfolio of independent applications such as DealQuill, D&D Companion, TradingHelper, and FSE-IT.

## What it does

- discovers Git repositories and common language manifests in a workspace;
- summarizes stack, root and nested agent instructions, docs, tests, lockfiles, and available script names;
- reports basic repository hygiene signals in a human-readable or JSON format;
- never runs a project's scripts, installs packages, contacts the network, or modifies project files;
- detects a few environment-file names but never reads their contents.

This is a metadata overview, not a security audit, CI replacement, or production-readiness assessment. It deliberately does not guess whether dependencies are current or whether tests pass.

## Requirements and installation

- Python 3.11 or newer;
- no runtime third-party dependencies.

From this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
project-doctor --version
```

On Windows, activate with `.venv\\Scripts\\activate`.

## Usage

List project repositories directly under a workspace:

```bash
project-doctor list --root ~/Projekty
project-doctor list --root ~/Projekty --json
```

Nested project discovery is opt-in and bounded to four directory levels. Hidden directories and common dependency/build folders are skipped:

```bash
project-doctor list --root ~/Projekty --recursive
```

Inspect one project and see script names without executing them:

```bash
project-doctor inspect DealQuill --root ~/Projekty
project-doctor inspect ~/Projekty/TradingHelper --json
```

Show lightweight hygiene signals:

```bash
project-doctor check DnDCompanion --root ~/Projekty
project-doctor check FSE-IT --root ~/Projekty --json
```

Run directly from a checkout without installing:

```bash
./bin/project-doctor list --root ~/Projekty
# or: PYTHONPATH=src python -m project_doctor list --root ~/Projekty
```

## Checks and limitations

`check` looks for a root README, Git metadata, optional root and nested `AGENTS.md` instructions, supported root manifests, common lockfiles, and a conventional tests directory. Static sites with a root `index.html` are identified as HTML/CSS/JavaScript. Missing README and a Node package lockfile are warnings. Other missing metadata is informational. A tests directory means only that one exists; tests are never run.

The first version inspects only the project root (plus bounded directory discovery when `--recursive` is selected). It does not parse every nested package in a monorepo, inspect Git working-tree changes, read `.env` data, infer deployability, or execute commands declared by projects. JSON output is stable enough for local automation but is not yet a versioned public API.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## Verification — 2026-11-18

- `./_tools/devhouse test project-overview` from the parent workspace: **11 tests passed**.
- Python syntax compilation and `git diff --check`: passed.
- Actual workspace smoke: default listing found 11 direct projects; recursive listing
  found 12, including `smartwatch-os/RabuWatchOS`, without returning the parent.
- GitHub Actions configuration added; remote execution not yet verified.

This fixes discovery in project-doctor. Separate devhouse issues (setup dispatch,
project-specific test coverage and opt-in recursive discovery) are not resolved by
this change; a working list does not guarantee that every project's test adapter
is complete.
