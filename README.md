# Python Project Template

Minimal starter template for a small Python CLI project using only the standard
library.

## Layout

- `mytool`: top-level launcher script
- `src/bin/main`: shell entrypoint (sets `PYTHONPATH`, selects Python)
- `src/lib/main.py`: Python CLI module
- `src/tst/ut`: unit tests + unit test runner
- `src/tst/sy`: system tests + system test runner
- `makefile`: test commands

## Quick Start

```bash
./mytool --name developer
make test
```

## Notes

- Uses `unittest` so no third-party dependencies are required.
- `ALT_PYTHON` can override the interpreter used by `src/bin/main`.
