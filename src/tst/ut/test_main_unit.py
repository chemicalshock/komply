from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import main


class TestMainUnit(unittest.TestCase):
    def test_reports_violations_for_matching_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"20\" />\n"
                    "    <forbid-trailing-whitespace />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "bad.cpp").write_text(
                "int main() { return 0; }                     \n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 1)
        text = output.getvalue()
        self.assertIn("bad.cpp:1 [max-line-length]", text)
        self.assertIn("bad.cpp:1 [forbid-trailing-whitespace]", text)

    def test_honors_include_and_exclude_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <filters>\n"
                    "    <include glob=\"src/*.cpp\" />\n"
                    "    <exclude glob=\"src/generated/*\" />\n"
                    "  </filters>\n"
                    "  <rules>\n"
                    "    <max-lines value=\"1\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "src").mkdir()
            (repo_root / "src" / "generated").mkdir()
            (repo_root / "src" / "one.cpp").write_text("line1\nline2\n", encoding="utf-8")
            (repo_root / "src" / "generated" / "ignored.cpp").write_text(
                "line1\nline2\nline3\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 1)
        text = output.getvalue()
        self.assertIn("src/one.cpp [max-lines]", text)
        self.assertNotIn("ignored.cpp", text)

    def test_returns_config_error_for_invalid_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <unknown-rule />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            error = io.StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Configuration error:", error.getvalue())

    def test_prioritizes_local_config_over_tool_config(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as tool_tmp:
            repo_root = Path(repo_tmp)
            tool_root = Path(tool_tmp)

            (repo_root / ".komply").mkdir()
            (tool_root / ".komply").mkdir()
            (repo_root / "src").mkdir()
            (repo_root / "src" / "sample.cpp").write_text(
                "int main() { return 0; }\n",
                encoding="utf-8",
            )

            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"10\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (tool_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"120\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with patch.dict("os.environ", {"KOMPLY_TOOL_ROOT": str(tool_root)}):
                with redirect_stdout(output):
                    code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 1)
        self.assertIn("src/sample.cpp:1 [max-line-length]", output.getvalue())

    def test_falls_back_to_tool_config_when_local_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as tool_tmp:
            repo_root = Path(repo_tmp)
            tool_root = Path(tool_tmp)

            (repo_root / "src").mkdir()
            (repo_root / "src" / "sample.cpp").write_text(
                "int main() { return 0; }\n",
                encoding="utf-8",
            )
            (tool_root / ".komply").mkdir()
            (tool_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"120\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with patch.dict("os.environ", {"KOMPLY_TOOL_ROOT": str(tool_root)}):
                with redirect_stdout(output):
                    code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 0)
        self.assertIn("cpp: 1 file(s) matched", output.getvalue())


if __name__ == "__main__":
    unittest.main()
