from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class TestCliSystem(unittest.TestCase):
    def test_shell_entrypoint_runs(self) -> None:
        proc = subprocess.run(
            ["sh", str(REPO_ROOT / "src" / "bin" / "main"), "--name", "system"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("Hello, system!", proc.stdout)


if __name__ == "__main__":
    unittest.main()
