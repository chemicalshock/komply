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


if __name__ == "__main__":
    unittest.main()
