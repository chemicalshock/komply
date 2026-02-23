# -------------------------------------------------------------
#
#!\file test_engine_unit.py
#!\brief Unit tests for the engine.py module of the komply tool.
#!\author Ryan (ORIM)
#
# -------------------------------------------------------------
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import engine


class TestEngineUnit(unittest.TestCase):
    def test_load_policies_excludes_reserved_runtime_config_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir)
            (config_dir / "00-config.xml").write_text(
                (
                    "<komply-config version=\"1\">\n"
                    "  <scan>\n"
                    "    <ignore-directory path=\"build\" />\n"
                    "  </scan>\n"
                    "</komply-config>\n"
                ),
                encoding="utf-8",
            )
            (config_dir / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"120\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )

            policies = engine.load_policies(config_dir)

        self.assertEqual([policy.name for policy in policies], ["cpp"])

    def test_load_effective_policies_merges_project_override_and_keeps_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as project_tmp, tempfile.TemporaryDirectory() as tool_tmp:
            project_dir = Path(project_tmp)
            tool_dir = Path(tool_tmp)

            (project_dir / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"10\" tier=\"local\" weight=\"9\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (tool_dir / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"120\" tier=\"tool\" weight=\"1\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (tool_dir / "python.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <require-final-newline tier=\"tool-py\" weight=\"2\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )

            policies = engine.load_effective_policies(
                project_policy_dir=project_dir,
                tool_policy_dir=tool_dir,
            )

        self.assertEqual([policy.name for policy in policies], ["cpp", "python"])
        self.assertEqual(policies[0].config_path.parent, project_dir)
        self.assertEqual(policies[0].rules[0].tier, "local")
        self.assertEqual(policies[1].config_path.parent, tool_dir)

    def test_scan_repository_prunes_runtime_ignored_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            project_policy_dir = repo_root / ".komply"
            project_policy_dir.mkdir()
            (project_policy_dir / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-lines value=\"1\" tier=\"scope\" weight=\"8\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "src").mkdir()
            (repo_root / "vendor").mkdir()
            (repo_root / "src" / "keep.cpp").write_text("a\nb\n", encoding="utf-8")
            (repo_root / "vendor" / "drop.cpp").write_text("a\nb\nc\n", encoding="utf-8")

            report = engine.scan_repository(
                repo_root=repo_root,
                project_policy_dir=project_policy_dir,
                tool_policy_dir=None,
                runtime_config=engine.ProjectRuntimeConfig(ignore_directories=("vendor",)),
            )

        self.assertEqual(report.files_by_policy.get("cpp"), 1)
        self.assertEqual(len(report.violations), 1)
        self.assertTrue(all("vendor/" not in item.path.as_posix() for item in report.violations))


if __name__ == "__main__":
    unittest.main()
