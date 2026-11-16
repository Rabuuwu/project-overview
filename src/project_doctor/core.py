"""Read-only discovery of project metadata. No project commands are executed."""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any


MANIFESTS = {
    "package.json": "Node.js",
    "pyproject.toml": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "composer.json": "PHP",
    "Gemfile": "Ruby",
    "pom.xml": "Java / Maven",
    "build.gradle": "Java / Gradle",
    "build.gradle.kts": "Kotlin / Gradle",
    "mix.exs": "Elixir",
    "pubspec.yaml": "Dart / Flutter",
}

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    "target",
    "__pycache__",
}

NODE_LOCKFILES = {
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "Yarn",
    "package-lock.json": "npm",
    "bun.lock": "Bun",
    "bun.lockb": "Bun",
}


def _is_project(path: Path) -> bool:
    return (path / ".git").exists() or any((path / name).is_file() for name in MANIFESTS)


def discover_projects(root: Path, recursive: bool = False, max_depth: int = 4) -> list[Path]:
    """Find project roots without entering dependency, build, or hidden folders."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Root directory does not exist: {root}")
    if _is_project(root):
        return [root]

    found: list[Path] = []
    if not recursive:
        candidates = sorted((p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")), key=lambda p: p.name.casefold())
        return [path.resolve() for path in candidates if _is_project(path)]

    for current, dirs, _files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        dirs[:] = sorted(
            (name for name in dirs if name not in IGNORED_DIRS and not name.startswith(".")),
            key=str.casefold,
        )
        if depth >= max_depth:
            dirs[:] = []
        if current_path != root and _is_project(current_path):
            found.append(current_path.resolve())
            dirs[:] = []
    return sorted(found, key=lambda p: str(p).casefold())


def _read_manifest(path: Path, filename: str) -> dict[str, Any]:
    try:
        if filename.endswith(".json"):
            data = json.loads((path / filename).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            return data
        with (path / filename).open("rb") as manifest:
            data = tomllib.load(manifest)
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        return {}


def _nested_agents_files(root: Path, max_depth: int = 5) -> list[str]:
    found: list[str] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        dirs[:] = sorted(
            (name for name in dirs if name not in IGNORED_DIRS and not name.startswith(".")),
            key=str.casefold,
        )
        if depth >= max_depth:
            dirs[:] = []
        if current_path != root and "AGENTS.md" in files:
            found.append((current_path / "AGENTS.md").relative_to(root).as_posix())
    return sorted(found, key=str.casefold)


def inspect_project(path: Path) -> dict[str, Any]:
    """Return a concise metadata summary; never read environment-file contents."""
    path = path.expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"Project directory does not exist: {path}")

    manifests = [name for name in MANIFESTS if (path / name).is_file()]
    languages = list(dict.fromkeys(MANIFESTS[name] for name in manifests))
    if (path / "index.html").is_file():
        languages.extend(language for language in ("HTML", "CSS", "JavaScript") if language not in languages)
    scripts: list[str] = []
    project_name = path.name
    declared_manager: str | None = None
    for filename in manifests:
        data = _read_manifest(path, filename)
        if filename == "package.json":
            project_name = str(data.get("name") or project_name)
            package_manager_value = data.get("packageManager")
            if isinstance(package_manager_value, str):
                declared_manager = package_manager_value.split("@", 1)[0]
            package_scripts = data.get("scripts") or {}
            if isinstance(package_scripts, dict):
                scripts.extend(str(key) for key in package_scripts if isinstance(key, str))
        elif filename == "pyproject.toml":
            project = data.get("project") or {}
            if isinstance(project, dict):
                project_name = str(project.get("name") or project_name)
                entry_points = project.get("scripts") or {}
                if isinstance(entry_points, dict):
                    scripts.extend(str(key) for key in entry_points if isinstance(key, str))

    readmes = sorted(
        (name for name in ("README.md", "README.rst", "README.txt", "README") if (path / name).is_file()),
        key=str.casefold,
    )
    lockfiles = [name for name in NODE_LOCKFILES if (path / name).is_file()]
    package_manager = declared_manager or next((NODE_LOCKFILES[name] for name in lockfiles), None)
    if (path / "pnpm-workspace.yaml").is_file():
        package_manager = "pnpm workspace"
    elif (path / "uv.lock").is_file():
        package_manager = "uv"
    elif (path / "poetry.lock").is_file():
        package_manager = "Poetry"
    elif (path / "Pipfile.lock").is_file():
        package_manager = "Pipenv"
    elif (path / "requirements.txt").is_file():
        package_manager = "pip"
    elif "package.json" in manifests and package_manager is None:
        package_manager = "npm (inferred; no lockfile)"
    elif "pyproject.toml" in manifests and package_manager is None:
        package_manager = "pip (inferred; no lockfile)"

    tests_present = any((path / name).is_dir() for name in ("tests", "test", "__tests__"))
    env_files = [name for name in (".env", ".env.local", ".env.development", ".env.production") if (path / name).is_file()]
    root_agents = (path / "AGENTS.md").is_file()
    return {
        "name": project_name,
        "path": str(path),
        "git_repository": (path / ".git").exists(),
        "languages": languages,
        "manifests": manifests,
        "readme": readmes[0] if readmes else None,
        "agents_instructions": root_agents,
        "nested_agents_instructions": _nested_agents_files(path),
        "docs_directory": (path / "docs").is_dir(),
        "tests_directory": tests_present,
        "package_manager": package_manager,
        "lockfiles": lockfiles,
        "available_script_names": sorted(set(scripts)),
        "environment_files_present": env_files,
        "environment_file_contents_read": False,
    }


def check_project(path: Path) -> dict[str, Any]:
    """Report basic project hygiene signals, not a production-readiness verdict."""
    summary = inspect_project(path)
    findings: list[dict[str, str]] = []

    def add(level: str, code: str, message: str) -> None:
        findings.append({"level": level, "code": code, "message": message})

    if summary["readme"]:
        add("ok", "readme-present", f"Found {summary['readme']}.")
    else:
        add("warning", "readme-missing", "No root README was found.")

    if summary["git_repository"]:
        add("ok", "git-present", "Git metadata is present; working-tree status is not inspected.")
    else:
        add("info", "git-missing", "No .git entry was found in this directory.")

    if summary["agents_instructions"]:
        add("ok", "agents-present", "Found root AGENTS.md instructions.")
    else:
        suffix = (
            " Nested instruction files: " + ", ".join(summary["nested_agents_instructions"]) + "."
            if summary["nested_agents_instructions"]
            else ""
        )
        add("info", "agents-optional", "No root AGENTS.md was found; this is optional." + suffix)

    if summary["manifests"]:
        add("ok", "manifest-present", "Detected: " + ", ".join(summary["manifests"]) + ".")
    else:
        add("info", "manifest-missing", "No supported root dependency manifest was found.")

    if "package.json" in summary["manifests"] and not summary["lockfiles"]:
        add("warning", "node-lockfile-missing", "package.json exists but no supported Node lockfile was found.")
    elif summary["lockfiles"]:
        add("ok", "lockfile-present", "Found: " + ", ".join(summary["lockfiles"]) + ".")

    if summary["tests_directory"]:
        add("ok", "tests-directory-present", "A root tests directory was found; tests were not executed.")
    else:
        add("info", "tests-directory-missing", "No conventional root tests directory was found; tests were not executed.")

    if summary["environment_files_present"]:
        add("info", "environment-files-present", "Environment file names detected; their contents were not read.")
    return {"project": summary, "findings": findings, "warnings": sum(x["level"] == "warning" for x in findings)}
