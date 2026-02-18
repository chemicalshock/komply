# -------------------------------------------------------------
#
#!\file run_sy.py
#!\brief System test runner for the komply command-line tool.
#!\author Colin J.D. Stewart
#
# -------------------------------------------------------------
#            Copyright (c) 2026. Colin J.D. Stewart
#                    All rights reserved
# -------------------------------------------------------------
from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LIB_ROOT = REPO_ROOT / "src" / "lib"
SY_ROOT = REPO_ROOT / "src" / "tst" / "sy"

if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))
if str(SY_ROOT) not in sys.path:
    sys.path.insert(0, str(SY_ROOT))


def _supports_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


COLOR = _supports_color()


def _c(text: str, code: str) -> str:
    if not COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


LABEL_HEADER = _c("[==========]", "32")
LABEL_RUN = _c("[ RUN      ]", "32")
LABEL_PASS = _c("[       OK ]", "32")
LABEL_FAIL = _c("[  FAILED  ]", "31")
LABEL_SKIP = _c("[  SKIPPED ]", "33")
LABEL_CASE = _c("[ CASE     ]", "36")
LABEL_PASSED = _c("[  PASSED  ]", "32")


def _extract_case_and_test(test: unittest.case.TestCase) -> tuple[str, str]:
    parts = test.id().split(".")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return test.__class__.__name__, str(test)


def _format_reason(err_text: str) -> str:
    lines = [line.strip() for line in err_text.strip().splitlines() if line.strip()]
    if not lines:
        return "unknown error"
    return lines[-1]


class ColoredTestResult(unittest.TestResult):
    def __init__(self) -> None:
        super().__init__()
        self._suite_start = time.monotonic()
        self._test_start = 0.0
        self._current_case: str | None = None

    def startTest(self, test: unittest.case.TestCase) -> None:
        super().startTest(test)
        case_name, test_name = _extract_case_and_test(test)
        if case_name != self._current_case:
            print(f"{LABEL_CASE} {case_name}")
            self._current_case = case_name
        print(f"{LABEL_RUN} {case_name}.{test_name}")
        self._test_start = time.monotonic()

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        super().addSuccess(test)
        case_name, test_name = _extract_case_and_test(test)
        dt = time.monotonic() - self._test_start
        print(f"{LABEL_PASS} {case_name}.{test_name} ({dt:.3f}s)")

    def addFailure(self, test: unittest.case.TestCase, err) -> None:  # type: ignore[override]
        super().addFailure(test, err)
        case_name, test_name = _extract_case_and_test(test)
        dt = time.monotonic() - self._test_start
        reason = _format_reason(self.failures[-1][1])
        print(f"{LABEL_FAIL} {case_name}.{test_name} - {reason} ({dt:.3f}s)")

    def addError(self, test: unittest.case.TestCase, err) -> None:  # type: ignore[override]
        super().addError(test, err)
        case_name, test_name = _extract_case_and_test(test)
        dt = time.monotonic() - self._test_start
        reason = _format_reason(self.errors[-1][1])
        print(f"{LABEL_FAIL} {case_name}.{test_name} - {reason} ({dt:.3f}s)")

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        case_name, test_name = _extract_case_and_test(test)
        dt = time.monotonic() - self._test_start
        print(f"{LABEL_SKIP} {case_name}.{test_name} - {reason} ({dt:.3f}s)")

    def addExpectedFailure(self, test: unittest.case.TestCase, err) -> None:  # type: ignore[override]
        super().addExpectedFailure(test, err)
        case_name, test_name = _extract_case_and_test(test)
        dt = time.monotonic() - self._test_start
        print(f"{LABEL_PASS} {case_name}.{test_name} (expected failure) ({dt:.3f}s)")

    def addUnexpectedSuccess(self, test: unittest.case.TestCase) -> None:
        super().addUnexpectedSuccess(test)
        case_name, test_name = _extract_case_and_test(test)
        dt = time.monotonic() - self._test_start
        print(f"{LABEL_FAIL} {case_name}.{test_name} - unexpected success ({dt:.3f}s)")

    def print_summary(self) -> int:
        total_time_s = time.monotonic() - self._suite_start
        failed = len(self.failures) + len(self.errors) + len(self.unexpectedSuccesses)
        skipped = len(self.skipped)
        expected_fail = len(self.expectedFailures)
        passed = self.testsRun - failed - skipped - expected_fail

        print(f"{LABEL_HEADER} {self.testsRun} test(s) ran ({total_time_s:.3f}s total)")
        if failed == 0:
            print(f"{LABEL_PASSED} {passed} passed, {skipped} skipped")
            return 0

        print(f"{LABEL_FAIL} {failed} failed, {passed} passed, {skipped} skipped")
        return 1


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(SY_ROOT), pattern="test_*.py")
    total = suite.countTestCases()
    print(f"{LABEL_HEADER} Running {total} system test(s)")

    result = ColoredTestResult()
    suite.run(result)
    return result.print_summary()


if __name__ == "__main__":
    raise SystemExit(main())

