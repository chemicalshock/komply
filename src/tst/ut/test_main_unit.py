# -------------------------------------------------------------
#
#!\file test_main_unit.py
#!\brief Unit tests for the main.py module of the komply command-line tool.
#!\author Colin J.D. Stewart
#
# -------------------------------------------------------------
#            Copyright (c) 2026. Colin J.D. Stewart
#                    All rights reserved
# -------------------------------------------------------------
from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import main


class TestMainUnit(unittest.TestCase):
    def test_weighted_violations_produce_pass_f_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"20\" tier=\"quality\" weight=\"60\" />\n"
                    "    <forbid-trailing-whitespace tier=\"style\" weight=\"50\" />\n"
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

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("- bad.cpp", text)
        self.assertIn("[max-line-length] [tier:quality] [level:weighted:60]", text)
        self.assertIn("[tier:quality] [level:weighted:60]", text)
        self.assertIn("[tier:style] [level:weighted:50]", text)
        self.assertIn("lines: 1", text)
        self.assertIn("Quality: PF", text)

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
                    "    <max-lines value=\"1\" tier=\"scope\" weight=\"8\" />\n"
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

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("- src/one.cpp", text)
        self.assertIn("[max-lines] [tier:scope] [level:weighted:8]", text)
        self.assertNotIn("ignored.cpp", text)

    def test_matches_extensionless_makefile_by_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "makefile.xml").write_text(
                (
                    "<komply match=\"filename\" pattern=\"Makefile\">\n"
                    "  <rules>\n"
                    "    <forbid-regex pattern=\"\\bTODO\\b\" tier=\"build\" weight=\"3\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "Makefile").write_text("all:\n\t@echo TODO\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("- makefile: 1 file(s) matched", text)
        self.assertIn("- Makefile", text)
        self.assertIn("[forbid-regex] [tier:build] [level:weighted:3]", text)

    def test_matches_by_repo_path_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "build.xml").write_text(
                (
                    "<komply match=\"glob\" pattern=\"**/Makefile\">\n"
                    "  <rules>\n"
                    "    <forbid-regex pattern=\"\\bTODO\\b\" tier=\"build\" weight=\"3\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "src").mkdir()
            (repo_root / "src" / "Makefile").write_text("all:\n\t@echo TODO\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("- build: 1 file(s) matched", text)
        self.assertIn("- src/Makefile", text)
        self.assertIn("[forbid-regex] [tier:build] [level:weighted:3]", text)

    def test_prints_only_policies_with_non_zero_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-lines value=\"10\" tier=\"maintainability\" weight=\"2\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / ".komply" / "py.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-lines value=\"10\" tier=\"maintainability\" weight=\"2\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "sample.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("Loaded 2 policy file(s)", text)
        self.assertIn("- cpp: 1 file(s) matched", text)
        self.assertNotIn("- py: 0 file(s) matched", text)

    def test_max_function_lines_detects_large_function_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-function-lines value=\"3\" tier=\"maintainability\" weight=\"9\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "sample.cpp").write_text(
                (
                    "int helper() {\n"
                    "  int x = 0;\n"
                    "  x++;\n"
                    "  x++;\n"
                    "  return x;\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("- sample.cpp", text)
        self.assertIn("[max-function-lines] [tier:maintainability] [level:weighted:9]", text)
        self.assertIn("[tier:maintainability] [level:weighted:9]", text)
        self.assertIn("Function body has 6 lines; max is 3", text)

    def test_max_function_lines_supports_custom_open_close_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-function-lines value=\"3\" "
                    "open=\"BEGIN\" close=\"END\" "
                    "start-pattern=\"\\bfunction\\b\" "
                    "tier=\"dsl\" weight=\"12\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "sample.cpp").write_text(
                (
                    "function alpha BEGIN\n"
                    "  line1\n"
                    "  line2\n"
                    "  line3\n"
                    "  line4\n"
                    "END\n"
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("- sample.cpp", text)
        self.assertIn("[max-function-lines] [tier:dsl] [level:weighted:12]", text)
        self.assertIn("[tier:dsl] [level:weighted:12]", text)
        self.assertIn("Function body has 6 lines; max is 3", text)

    def test_groups_repeated_line_violations_with_line_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <forbid-trailing-whitespace tier=\"style\" weight=\"2\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "sample.cpp").write_text(
                "line1 \nline2 \nline3\nline4 \n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("- sample.cpp", text)
        self.assertIn("[forbid-trailing-whitespace] [tier:style] [level:weighted:2] (3 hit(s))", text)
        self.assertIn("lines: 1-2, 4", text)

    def test_forbid_regex_can_ignore_string_literals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <forbid-regex pattern=\"\\b(TODO|FIXME)\\b\" "
                    "include-strings=\"false\" tier=\"delivery\" weight=\"5\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "sample.cpp").write_text(
                (
                    "const char* msg = \"TODO in string\";\n"
                    "// TODO in comment\n"
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("- sample.cpp", text)
        self.assertIn("[forbid-regex] [tier:delivery] [level:weighted:5] (1 hit(s))", text)
        self.assertIn("lines: 2", text)
        self.assertNotIn("lines: 1", text)

    def test_blocking_violation_returns_fail_fast_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <forbid-regex pattern=\"\\busing\\s+namespace\\s+std\\b\" "
                    "tier=\"critical\" blocking=\"true\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (repo_root / "bad.cpp").write_text(
                "using namespace std;\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = main.main(["--repo-root", str(repo_root)])

        self.assertEqual(code, 1)
        text = output.getvalue()
        self.assertIn("[tier:critical] [level:blocking]", text)
        self.assertIn("Quality: FF", text)

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

    def test_returns_config_error_for_invalid_max_function_lines_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-function-lines value=\"10\" open=\"##\" close=\"##\" />\n"
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
        self.assertIn("attributes 'open' and 'close' must differ", error.getvalue())

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
                    "    <max-line-length value=\"10\" tier=\"local\" weight=\"40\" />\n"
                    "  </rules>\n"
                    "</komply>\n"
                ),
                encoding="utf-8",
            )
            (tool_root / ".komply" / "cpp.xml").write_text(
                (
                    "<komply>\n"
                    "  <rules>\n"
                    "    <max-line-length value=\"120\" tier=\"tool\" weight=\"1\" />\n"
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
        text = output.getvalue()
        self.assertIn("[tier:local]", text)
        self.assertNotIn("[tier:tool]", text)

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
                    "    <max-line-length value=\"10\" tier=\"tool\" weight=\"70\" />\n"
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
        text = output.getvalue()
        self.assertIn("[tier:tool]", text)
        self.assertIn("cpp: 1 file(s) matched", text)

    def test_load_project_runtime_config_returns_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)

            runtime_config = main.load_project_runtime_config(repo_root)

        self.assertEqual(runtime_config.version, 1)
        self.assertEqual(runtime_config.ignore_directories, ())

    def test_load_project_runtime_config_parses_and_normalizes_ignore_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "00-config.xml").write_text(
                (
                    "<komply-config version=\"1\">\n"
                    "  <scan>\n"
                    "    <ignore-directory path=\"./build/\" />\n"
                    "    <ignore-directory path=\"src/generated\" />\n"
                    "    <ignore-directory path=\"src/generated/\" />\n"
                    "  </scan>\n"
                    "</komply-config>\n"
                ),
                encoding="utf-8",
            )

            runtime_config = main.load_project_runtime_config(repo_root)

        self.assertEqual(runtime_config.version, 1)
        self.assertEqual(runtime_config.ignore_directories, ("build", "src/generated"))

    def test_load_project_runtime_config_rejects_absolute_ignore_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            (repo_root / ".komply").mkdir()
            (repo_root / ".komply" / "00-config.xml").write_text(
                (
                    "<komply-config version=\"1\">\n"
                    "  <scan>\n"
                    "    <ignore-directory path=\"/vendor\" />\n"
                    "  </scan>\n"
                    "</komply-config>\n"
                ),
                encoding="utf-8",
            )

            with self.assertRaises(main.engine.KomplyConfigError):
                main.load_project_runtime_config(repo_root)

    def test_resolve_policy_sources_merges_project_and_tool_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as tool_tmp:
            repo_root = Path(repo_tmp)
            tool_root = Path(tool_tmp)
            (repo_root / ".komply").mkdir()

            with patch.dict("os.environ", {"KOMPLY_TOOL_ROOT": str(tool_root)}):
                project_policy_dir, tool_policy_dir = main.resolve_policy_sources(
                    repo_root=repo_root,
                    config_dir_arg=None,
                )

        self.assertEqual(project_policy_dir, (repo_root / ".komply").resolve())
        self.assertEqual(tool_policy_dir, (tool_root / ".komply").resolve())


if __name__ == "__main__":
    unittest.main()
