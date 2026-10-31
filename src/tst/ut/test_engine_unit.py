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
    def test_cpp_memory_rule_allows_deleted_functions(self) -> None:
        policy = engine.parse_policy(Path(__file__).resolve().parents[3] / ".komply" / "cpp.xml")
        source = (
            "Widget() = delete;\n"
            "Widget(const Widget&) = delete /* disabled */ ;\n"
            "Widget& operator=(const Widget&) = delete\n"
            "    ;\n"
            "void reset() = delete;\n"
            "Widget(Widget&&) = delete // disabled\n"
            "    ;\n"
            "auto p = new Widget;\n"
            "delete p;\n"
            "delete (p);\n"
            "delete[] p;\n"
            "delete /* operand */\n"
            "    p;\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            for extension in ("cpp", "hpp"):
                with self.subTest(extension=extension):
                    path = Path(tmp_dir) / f"widget.{extension}"
                    path.write_text(source, encoding="utf-8")
                    findings = [v.line for v in engine.evaluate_file(path, policy)
                                if v.tier == "memory-safety"]
                    self.assertEqual(findings, [8, 9, 10, 11, 12])

    def test_own_header_first_in_bundled_policies(self) -> None:
        cases = [
            ('#include "widget{header}"\n#include <stdio.h>\n', None),
            ('#include <stdio.h>\n#include "widget{header}"\n', 2),
            ('# include OTHER\n# include <project/widget{header}>\n', 2),
            ('#include "other{header}"\n', None),
            ('#include "widget.wrong"\n', None),
            ('// #include <ignored>\n/* #include <ignored> */\n'
             '# /* comment */ include "project/widget{header}"\n', None),
            ('auto text = R"tag(\n#include <ignored>\n)tag";\n'
             '#include "widget{header}"\n', None),
            ('#include "widget{header}"\n#include "widget{header}"\n', None),
            ('#include <stdio.h>\n// #include "widget{header}"\n', None),
        ]
        root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp_dir:
            for language, header in (("c", ".h"), ("cpp", ".hpp")):
                policy = engine.parse_policy(root / ".komply" / f"{language}.xml")
                for source, expected_line in cases:
                    with self.subTest(language=language, source=source):
                        path = Path(tmp_dir) / f"widget.{language}"
                        path.write_text(source.replace("{header}", header), encoding="utf-8")
                        findings = [v for v in engine.evaluate_file(path, policy)
                                    if v.rule == "require-own-header-first"]
                        self.assertEqual([v.line for v in findings],
                                         [] if expected_line is None else [expected_line])
                        if findings:
                            self.assertEqual(findings[0].tier, "style")
                            self.assertEqual(findings[0].weight, 2)
                            self.assertIn("widget" + header, findings[0].message)
                path = Path(tmp_dir) / ("widget" + header)
                path.write_text('#include <other>\n#include "widget' + header + '"\n', encoding="utf-8")
                self.assertFalse(any(v.rule == "require-own-header-first"
                                     for v in engine.evaluate_file(path, policy)))

    def test_cpp_keyword_rules_ignore_sql_strings_and_keep_code_findings(self) -> None:
        policy = engine.parse_policy(Path(__file__).resolve().parents[3] / ".komply" / "cpp.xml")
        source = (
            'auto sql = "SELECT NULL, \\"new\\" FROM records; delete";\n'
            'auto raw = R"sql(SELECT "NULL", new\n'
            'delete FROM records)sql";\n'
            'auto wide = u8R"(SELECT "NULL", new, delete)";\n'
            'auto p = new int;\n'
            'delete p;\n'
            'auto q = NULL;\n'
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "query.cpp"
            path.write_text(source, encoding="utf-8")
            violations = engine.evaluate_file(path, policy)
        self.assertEqual(
            sorted(item.line for item in violations if item.rule == "forbid-regex"),
            [5, 6, 7],
        )

    def test_cpp_code_rules_ignore_comments_and_keep_todos(self) -> None:
        policy = engine.parse_policy(Path(__file__).resolve().parents[3] / ".komply" / "cpp.xml")
        source = (
            "// NULL new delete goto using namespace std\n"
            "/* NULL new\n"
            "delete goto using namespace std */ auto p = NULL;\n"
            "auto q = /* NULL */ new int; // delete\n"
            "// TODO: replace NULL\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "comments.cpp"
            path.write_text(source, encoding="utf-8")
            violations = engine.evaluate_file(path, policy)
        self.assertEqual(
            sorted(item.line for item in violations if item.rule == "forbid-regex"),
            [3, 4, 5],
        )

    def test_comment_mask_preserves_strings_and_offsets(self) -> None:
        source = '"https://example/*NULL*/"; NULL; /* NULL */\n// NULL\n'
        masked = engine.mask_non_code(source, mask_comments=True, mask_strings=False)
        self.assertEqual(len(masked), len(source))
        self.assertEqual(masked.splitlines()[0].rstrip(), '"https://example/*NULL*/"; NULL;')
        self.assertEqual(masked.count("\n"), source.count("\n"))
        self.assertEqual(
            engine.mask_non_code("// NULL\n/* NULL */", mask_comments=False),
            "// NULL\n/* NULL */",
        )

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
