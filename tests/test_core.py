from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from project_doctor.core import check_project, discover_projects, inspect_project


class ProjectDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_project(self, name: str) -> Path:
        project = self.root / name
        project.mkdir()
        return project

    def test_discovers_manifest_projects_and_skips_hidden_directories(self) -> None:
        app = self.make_project("app")
        (app / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
        hidden = self.make_project(".hidden")
        (hidden / "package.json").write_text("{}", encoding="utf-8")
        self.assertEqual([app.resolve()], discover_projects(self.root))

    def test_reads_manifest_metadata_without_reading_env_file_contents(self) -> None:
        project = self.make_project("web-app")
        (project / "package.json").write_text(
            json.dumps({"name": "web-app", "scripts": {"test": "echo should-not-run"}}), encoding="utf-8"
        )
        (project / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
        (project / "README.md").write_text("# Demo\n", encoding="utf-8")
        (project / "tests").mkdir()
        (project / ".env").write_text("DO_NOT_READ=secret-value\n", encoding="utf-8")

        result = inspect_project(project)
        self.assertEqual("web-app", result["name"])
        self.assertEqual("pnpm", result["package_manager"])
        self.assertEqual(["test"], result["available_script_names"])
        self.assertEqual([".env"], result["environment_files_present"])
        self.assertFalse(result["environment_file_contents_read"])
        self.assertNotIn("secret-value", json.dumps(result))

    def test_check_reports_actionable_metadata_without_running_tests(self) -> None:
        project = self.make_project("api")
        (project / "package.json").write_text('{"name":"api"}', encoding="utf-8")
        result = check_project(project)
        codes = {finding["code"] for finding in result["findings"]}
        self.assertIn("readme-missing", codes)
        self.assertIn("node-lockfile-missing", codes)
        self.assertIn("tests-directory-missing", codes)
        self.assertEqual(2, result["warnings"])

    def test_detects_static_site_and_nested_agent_instructions(self) -> None:
        project = self.make_project("portfolio")
        (project / ".git").mkdir()
        (project / "index.html").write_text("<main>Portfolio</main>", encoding="utf-8")
        (project / "app.js").write_text("console.log('portfolio')", encoding="utf-8")
        nested = project / "apps" / "web"
        nested.mkdir(parents=True)
        (nested / "AGENTS.md").write_text("Follow local instructions.\n", encoding="utf-8")

        result = inspect_project(project)
        self.assertEqual(["HTML", "CSS", "JavaScript"], result["languages"])
        self.assertEqual(["apps/web/AGENTS.md"], result["nested_agents_instructions"])


if __name__ == "__main__":
    unittest.main()
