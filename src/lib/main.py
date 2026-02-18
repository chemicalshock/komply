from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mytool",
        description="Simple starter CLI for a Python project template.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Path to the repository root (set by shell launcher).",
    )
    parser.add_argument(
        "--name",
        default="world",
        help="Name to greet.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    location = f" from {args.repo_root}" if args.repo_root else ""
    print(f"Hello, {args.name}!{location}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
