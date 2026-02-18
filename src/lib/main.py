from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import engine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="komply",
        description="Run XML-defined compliance checks on source files.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Path to the repository root.",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help=(
            "Directory containing XML policies. "
            "Default: use local .komply if present, else tool .komply."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the final summary and violations.",
    )
    return parser


def resolve_config_dir(repo_root: Path, config_dir_arg: Path | None) -> Path:
    if config_dir_arg is not None:
        if config_dir_arg.is_absolute():
            return config_dir_arg.resolve()
        return (repo_root / config_dir_arg).resolve()

    local_config_dir = (repo_root / ".komply").resolve()
    if local_config_dir.is_dir():
        return local_config_dir

    tool_root = os.environ.get("KOMPLY_TOOL_ROOT")
    if tool_root:
        tool_config_dir = (Path(tool_root) / ".komply").resolve()
        if tool_config_dir.is_dir():
            return tool_config_dir
        return tool_config_dir

    return local_config_dir


def render_report(repo_root: Path, report: engine.ScanReport, quiet: bool = False) -> None:
    total_files = sum(report.files_by_policy.values())
    total_violations = len(report.violations)
    files_with_violations = len({item.path for item in report.violations})

    if not quiet:
        print(f"Loaded {report.policies_loaded} policy file(s)")
        for policy_name, file_count in sorted(report.files_by_policy.items()):
            print(f"- {policy_name}: {file_count} file(s) matched")

    if total_violations:
        print("Violations:")
        grouped = group_violations(repo_root, report.violations)
        for path, rule_groups in grouped.items():
            print(f"- {path}")
            for (rule, tier, level), entries in rule_groups.items():
                print(f"  [{rule}] [tier:{tier}] [level:{level}] ({len(entries)} hit(s))")
                messages = {message for _, message in entries}
                if len(messages) == 1:
                    message = entries[0][1]
                    lines = sorted({line for line, _ in entries if line is not None})
                    file_level_hits = sum(1 for line, _ in entries if line is None)
                    print(f"    {message}")
                    if lines:
                        print(f"    lines: {format_line_numbers(lines)}")
                    if file_level_hits:
                        print(f"    file-level hits: {file_level_hits}")
                    continue

                print("    hits:")
                for line, message in entries:
                    if line is None:
                        print(f"      - file: {message}")
                    else:
                        print(f"      - line {line}: {message}")

    print(
        f"Quality: {report.quality_status} "
        f"(grade={report.quality_grade}, score={report.quality_score}, "
        f"penalty={report.weighted_penalty}, "
        f"blocking={report.blocking_violations}, "
        f"weighted={report.non_blocking_violations})"
    )
    print(
        f"Summary: {total_files} file(s) checked, "
        f"{total_violations} violation(s), {files_with_violations} file(s) failing"
    )


def group_violations(
    repo_root: Path, violations: list[engine.Violation]
) -> dict[str, dict[tuple[str, str, str], list[tuple[int | None, str]]]]:
    grouped: dict[str, dict[tuple[str, str, str], list[tuple[int | None, str]]]] = {}
    for violation in violations:
        rel_path = violation.path.relative_to(repo_root).as_posix()
        level = "blocking" if violation.blocking else f"weighted:{violation.weight}"
        key = (violation.rule, violation.tier, level)
        path_group = grouped.setdefault(rel_path, {})
        entries = path_group.setdefault(key, [])
        entries.append((violation.line, violation.message))
    return grouped


def format_line_numbers(lines: list[int]) -> str:
    if not lines:
        return ""
    ranges: list[str] = []
    start = lines[0]
    prev = lines[0]

    for line in lines[1:]:
        if line == prev + 1:
            prev = line
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        start = line
        prev = line

    ranges.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(ranges)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)

    repo_root = (args.repo_root or Path.cwd()).resolve()
    config_dir = resolve_config_dir(repo_root, args.config_dir)

    try:
        report = engine.scan_repository(repo_root=repo_root, config_dir=config_dir)
    except engine.KomplyConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    render_report(repo_root, report, quiet=args.quiet)
    if report.quality_status == "FF":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
