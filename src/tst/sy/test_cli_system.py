# -------------------------------------------------------------
#
#!\file test_cli_system.py
#!\brief System tests for the komply command-line tool.
#!\author Colin J.D. Stewart
#
# -------------------------------------------------------------
#            Copyright (c) 2026. Colin J.D. Stewart
#                    All rights reserved
# -------------------------------------------------------------
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class TestCliSystem(unittest.TestCase):
    def test_shell_entrypoint_runs(self) -> None:
        proc = subprocess.run(
            ["sh", str(REPO_ROOT / "src" / "bin" / "main")],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("Summary:", proc.stdout)

    def test_scans_callers_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scan_root = Path(tmp_dir)
            (scan_root / ".komply").mkdir()
            (scan_root / "src" / "lib").mkdir(parents=True)
            (scan_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"120\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (scan_root / "src" / "lib" / "example.cpp").write_text(
                "int main() { return 0; }\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                ["sh", str(REPO_ROOT / "src" / "bin" / "main"), "--quiet"],
                cwd=scan_root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("Summary: 1 file(s) checked", proc.stdout)

    def test_falls_back_to_tool_config_when_caller_has_no_komply_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scan_root = Path(tmp_dir)
            (scan_root / "src" / "lib").mkdir(parents=True)
            (scan_root / "src" / "lib" / "example.cpp").write_text(
                "int main() { return 0; }\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                ["sh", str(REPO_ROOT / "src" / "bin" / "main"), "--quiet"],
                cwd=scan_root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("Summary: 1 file(s) checked", proc.stdout)

    def test_runtime_config_only_local_komply_still_uses_tool_fallback_policies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scan_root = Path(tmp_dir)
            (scan_root / ".komply").mkdir()
            (scan_root / ".komply" / "00-config.xml").write_text(
                (
                    "<komply-config version=\"1\">\n"
                    "  <scan>\n"
                    "    <ignore-directory path=\"build\" />\n"
                    "  </scan>\n"
                    "</komply-config>\n"
                ),
                encoding="utf-8",
            )
            (scan_root / "src" / "lib").mkdir(parents=True)
            (scan_root / "src" / "lib" / "example.cpp").write_text(
                "int main() { return 0; }\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                ["sh", str(REPO_ROOT / "src" / "bin" / "main"), "--quiet"],
                cwd=scan_root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("Summary: 1 file(s) checked", proc.stdout)

    def test_local_policy_overrides_matching_fallback_and_keeps_other_fallback_policies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scan_root = Path(tmp_dir)
            (scan_root / ".komply").mkdir()
            (scan_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <forbid-regex pattern=\"\\bLOCAL_ONLY\\b\" "
                    "tier=\"local-override\" weight=\"7\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (scan_root / "src").mkdir()
            (scan_root / "src" / "sample.cpp").write_text(
                "int main() { /* LOCAL_ONLY */ return 0; }\n",
                encoding="utf-8",
            )
            (scan_root / "src" / "sample.py").write_text(
                "print('ok')\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                ["sh", str(REPO_ROOT / "src" / "bin" / "main")],
                cwd=scan_root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("[tier:local-override]", proc.stdout)
        self.assertIn("- cpp: 1 file(s) matched", proc.stdout)
        self.assertIn("- python: 1 file(s) matched", proc.stdout)

    def test_runtime_config_ignored_directories_are_applied_before_policy_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scan_root = Path(tmp_dir)
            (scan_root / ".komply").mkdir()
            (scan_root / ".komply" / "00-config.xml").write_text(
                (
                    "<komply-config version=\"1\">\n"
                    "  <scan>\n"
                    "    <ignore-directory path=\"vendor\" />\n"
                    "  </scan>\n"
                    "</komply-config>\n"
                ),
                encoding="utf-8",
            )
            (scan_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-lines value=\"1\" tier=\"scope\" weight=\"8\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (scan_root / "src").mkdir()
            (scan_root / "vendor").mkdir()
            (scan_root / "src" / "keep.cpp").write_text("line1\nline2\n", encoding="utf-8")
            (scan_root / "vendor" / "drop.cpp").write_text(
                "line1\nline2\nline3\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                ["sh", str(REPO_ROOT / "src" / "bin" / "main")],
                cwd=scan_root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("- src/keep.cpp", proc.stdout)
        self.assertNotIn("vendor/drop.cpp", proc.stdout)
        self.assertIn("Summary: 1 file(s) checked", proc.stdout)

    def test_invalid_runtime_config_returns_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scan_root = Path(tmp_dir)
            (scan_root / ".komply").mkdir()
            (scan_root / ".komply" / "00-config.xml").write_text(
                (
                    "<komply-config version=\"1\">\n"
                    "  <scan>\n"
                    "    <ignore-directory path=\"/absolute\" />\n"
                    "  </scan>\n"
                    "</komply-config>\n"
                ),
                encoding="utf-8",
            )
            (scan_root / "src").mkdir()
            (scan_root / "src" / "example.cpp").write_text(
                "int main() { return 0; }\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                ["sh", str(REPO_ROOT / "src" / "bin" / "main"), "--quiet"],
                cwd=scan_root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("Configuration error:", proc.stderr)

    def test_reserved_00_config_filename_is_not_treated_as_policy_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scan_root = Path(tmp_dir)
            (scan_root / ".komply").mkdir()
            (scan_root / ".komply" / "00-config.xml").write_text(
                (
                    "<komply-config version=\"1\">\n"
                    "  <scan>\n"
                    "    <ignore-directory path=\"build\" />\n"
                    "  </scan>\n"
                    "</komply-config>\n"
                ),
                encoding="utf-8",
            )
            (scan_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"120\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (scan_root / "example.cpp").write_text(
                "int main() { return 0; }\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                ["sh", str(REPO_ROOT / "src" / "bin" / "main"), "--quiet"],
                cwd=scan_root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("Summary: 1 file(s) checked", proc.stdout)


if __name__ == "__main__":
    unittest.main()
