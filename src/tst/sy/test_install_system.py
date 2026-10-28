from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]


class TestInstallSystem(unittest.TestCase):
    def test_installed_launcher_runs_checkout_from_another_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout = root / "source checkout's directory"
            checkout.mkdir()
            for name in ("install.sh", "komply", "src", ".komply"):
                source = REPO_ROOT / name
                if source.is_dir():
                    shutil.copytree(source, checkout / name)
                else:
                    shutil.copy2(source, checkout / name)
            prefix = root / "installed copy's prefix"
            project = root / "project"
            project.mkdir()
            for _ in range(2):
                installed = subprocess.run(
                    [str(checkout / "install.sh"), "--prefix", str(prefix)],
                    cwd=project, text=True, capture_output=True,
                )
                self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertEqual(list(prefix.iterdir()), [prefix / "bin"])
            self.assertEqual(list((prefix / "bin").iterdir()), [prefix / "bin" / "komply"])
            self.assertIn(str(checkout).split("'")[0], (prefix / "bin" / "komply").read_text())
            environment = dict(os.environ, PATH=f"{prefix / 'bin'}:{os.environ['PATH']}")
            (project / "example.cpp").write_text("int main() { return 0; }\n")
            fallback = subprocess.run(
                ["komply", "--quiet"], cwd=project, env=environment,
                text=True, capture_output=True,
            )
            self.assertEqual(fallback.returncode, 0, fallback.stderr)
            self.assertIn("Summary: 1 file(s) checked", fallback.stdout)

            # Changes in the clone are used immediately by the installed command.
            (checkout / ".komply" / "cpp.xml").write_text(
                '<komply><rules><forbid-regex pattern="int" blocking="true" />'
                '</rules></komply>\n'
            )
            updated = subprocess.run(
                ["komply", "--quiet"], cwd=project, env=environment,
                text=True, capture_output=True,
            )
            self.assertEqual(updated.returncode, 1, updated.stderr)
            self.assertIn("Quality: FF", updated.stdout)

            policies = project / ".komply"
            policies.mkdir()
            (policies / "cpp.xml").write_text(
                '<komply><rules><forbid-regex pattern="BAD" blocking="true" />'
                '</rules></komply>\n'
            )
            (project / "example.cpp").write_text("BAD\n")
            (project / "vendor").mkdir()
            (project / "vendor" / "ignored.cpp").write_text("BAD\n")
            (policies / "00-config.xml").write_text(
                '<komply-config version="1"><scan><ignore-directory path="vendor" />'
                '</scan></komply-config>\n'
            )
            local = subprocess.run(
                ["komply", "--quiet"], cwd=project, env=environment,
                text=True, capture_output=True,
            )
            self.assertEqual(local.returncode, 1, local.stderr)
            self.assertIn("Quality: FF", local.stdout)
            self.assertIn("Summary: 1 file(s) checked", local.stdout)
            self.assertNotIn("ignored.cpp", local.stdout)

    def test_installer_preserves_unrelated_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prefix = Path(temporary)
            (prefix / "bin").mkdir()
            command = prefix / "bin" / "komply"
            command.write_text("unrelated tool\n")
            result = subprocess.run(
                [str(REPO_ROOT / "install.sh"), "--prefix", str(prefix)],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to overwrite", result.stderr)
            self.assertEqual(command.read_text(), "unrelated tool\n")
