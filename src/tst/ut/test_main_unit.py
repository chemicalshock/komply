from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

import main


class TestMainUnit(unittest.TestCase):
    def test_main_prints_greeting(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main.main(["--name", "unit"])

        self.assertEqual(code, 0)
        self.assertIn("Hello, unit!", output.getvalue())


if __name__ == "__main__":
    unittest.main()
