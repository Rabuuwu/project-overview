"""Command-line interface for project-doctor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .core import check_project, discover_projects, inspect_project


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project-doctor",
        description="A read-only overview of projects and repository hygiene signals.",
        epilog="No project commands are executed and environment-file contents are never read.",
    )
    parser.add_argument("--version", action="version", version=f"project-doctor {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    listing = commands.add_parser("list", help="discover projects under a directory")
    listing.add_argument("--root", type=Path, default=Path.cwd(), help="workspace directory (default: current directory)")
    listing.add_argument("--recursive", action="store_true", help="search nested folders, up to four levels deep")
    listing.add_argument("--json", action="store_true", help="print machine-readable JSON")

    for name, help_text in (("inspect", "show project metadata"), ("check", "show basic hygiene signals")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("project", type=Path, help="project path, absolute or relative to --root")
        command.add_argument("--root", type=Path, default=Path.cwd(), help="base directory for relative paths")
        command.add_argument("--json", action="store_true", help="print machine-readable JSON")
    return parser


def _resolve_project(value: Path, root: Path) -> Path:
    path = value.expanduser()
    if not path.is_absolute():
        path = root.expanduser() / path
    return path.resolve()


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _print_project(project: dict[str, Any]) -> None:
    print(f"{project['name']}  ({project['path']})")
    print("  Stack: " + (", ".join(project["languages"]) or "not detected"))
    print("  Git: " + ("present" if project["git_repository"] else "not detected"))
    print("  README: " + (project["readme"] or "missing"))
    agents_summary = "root present" if project["agents_instructions"] else "root not found"
    if project["nested_agents_instructions"]:
        agents_summary += "; nested: " + ", ".join(project["nested_agents_instructions"])
    print("  AGENTS.md: " + agents_summary)
    print("  Tests directory: " + ("present" if project["tests_directory"] else "not found"))
    print("  Package manager: " + (project["package_manager"] or "not detected"))
    if project["available_script_names"]:
        print("  Script names (not executed): " + ", ".join(project["available_script_names"]))
    if project["environment_files_present"]:
        print("  Environment files present (contents not read): " + ", ".join(project["environment_files_present"]))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "list":
            projects = [inspect_project(path) for path in discover_projects(args.root, recursive=args.recursive)]
            if args.json:
                _print_json({"root": str(args.root.expanduser().resolve()), "projects": projects, "count": len(projects)})
            elif not projects:
                print(f"No projects found under {args.root.expanduser().resolve()}.")
            else:
                for project in projects:
                    _print_project(project)
                    print()
                print(f"{len(projects)} project(s). Use `project-doctor inspect <path>` or `check <path>` for details.")
            return 0

        project_path = _resolve_project(args.project, args.root)
        result = inspect_project(project_path) if args.command == "inspect" else check_project(project_path)
        if args.json:
            _print_json(result)
        elif args.command == "inspect":
            _print_project(result)
        else:
            _print_project(result["project"])
            print("\nFindings:")
            for finding in result["findings"]:
                print(f"  [{finding['level'].upper()}] {finding['message']}")
            print(f"\n{result['warnings']} warning(s). This is a metadata check, not a production-readiness verdict.")
        return 0
    except (OSError, ValueError) as exc:
        print(f"project-doctor: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
