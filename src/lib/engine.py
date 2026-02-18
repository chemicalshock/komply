from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
import re
import xml.etree.ElementTree as ET


class KomplyConfigError(Exception):
    """Raised when policy files are missing or invalid."""


@dataclass(frozen=True)
class Rule:
    kind: str
    value: int | None = None
    pattern: str | None = None
    regex: re.Pattern[str] | None = None
    message: str | None = None


@dataclass(frozen=True)
class Policy:
    name: str
    extension: str
    config_path: Path
    includes: tuple[str, ...]
    excludes: tuple[str, ...]
    rules: tuple[Rule, ...]


@dataclass(frozen=True)
class Violation:
    path: Path
    rule: str
    message: str
    line: int | None = None


@dataclass(frozen=True)
class ScanReport:
    policies_loaded: int
    files_by_policy: dict[str, int]
    violations: list[Violation]


SUPPORTED_RULES = (
    "max-line-length",
    "max-lines",
    "forbid-regex",
    "require-regex",
    "forbid-trailing-whitespace",
    "require-final-newline",
)


def scan_repository(repo_root: Path, config_dir: Path) -> ScanReport:
    policies = load_policies(config_dir)
    files_by_policy: dict[str, int] = {}
    violations: list[Violation] = []

    for policy in policies:
        targets = discover_targets(repo_root, config_dir, policy)
        files_by_policy[policy.name] = len(targets)
        for target in targets:
            violations.extend(evaluate_file(target, policy))

    return ScanReport(
        policies_loaded=len(policies),
        files_by_policy=files_by_policy,
        violations=sorted(
            violations,
            key=lambda item: (item.path.as_posix(), item.line or 0, item.rule),
        ),
    )


def load_policies(config_dir: Path) -> list[Policy]:
    if not config_dir.exists():
        raise KomplyConfigError(f"Configuration directory not found: {config_dir}")
    if not config_dir.is_dir():
        raise KomplyConfigError(f"Configuration path is not a directory: {config_dir}")

    xml_paths = sorted(path for path in config_dir.glob("*.xml") if path.is_file())
    if not xml_paths:
        raise KomplyConfigError(f"No XML policies found in: {config_dir}")

    return [parse_policy(path) for path in xml_paths]


def parse_policy(config_path: Path) -> Policy:
    if not config_path.stem:
        raise KomplyConfigError(
            f"Policy file name must include a type stem: {config_path.name}"
        )
    extension = config_path.stem
    if not extension.startswith("."):
        extension = f".{extension}"

    try:
        root = ET.parse(config_path).getroot()
    except ET.ParseError as exc:
        raise KomplyConfigError(f"{config_path}: invalid XML ({exc})") from exc

    if root.tag == "komply":
        filters_parent = root.find("filters")
        rules_parent = root.find("rules")
        if rules_parent is None:
            raise KomplyConfigError(f"{config_path}: missing <rules> block")
    elif root.tag == "rules":
        filters_parent = None
        rules_parent = root
    else:
        raise KomplyConfigError(
            f"{config_path}: root tag must be <komply> or <rules>, found <{root.tag}>"
        )

    includes, excludes = parse_filters(filters_parent)
    rules = parse_rules(config_path, rules_parent)
    if not rules:
        raise KomplyConfigError(f"{config_path}: no rules defined")

    return Policy(
        name=config_path.stem,
        extension=extension,
        config_path=config_path,
        includes=tuple(includes),
        excludes=tuple(excludes),
        rules=tuple(rules),
    )


def parse_filters(filters_parent: ET.Element | None) -> tuple[list[str], list[str]]:
    if filters_parent is None:
        return [], []

    includes: list[str] = []
    excludes: list[str] = []
    for node in filters_parent:
        glob = (node.attrib.get("glob") or "").strip()
        if not glob:
            continue
        if node.tag == "include":
            includes.append(glob)
        elif node.tag == "exclude":
            excludes.append(glob)

    return includes, excludes


def parse_rules(config_path: Path, rules_parent: ET.Element) -> list[Rule]:
    rules: list[Rule] = []
    for node in rules_parent:
        kind = node.tag
        message = node.attrib.get("message")
        if kind == "max-line-length":
            rules.append(
                Rule(kind=kind, value=parse_positive_int(config_path, node, "value"), message=message)
            )
            continue
        if kind == "max-lines":
            rules.append(
                Rule(kind=kind, value=parse_positive_int(config_path, node, "value"), message=message)
            )
            continue
        if kind == "forbid-regex":
            pattern = require_attr(config_path, node, "pattern")
            rules.append(
                Rule(
                    kind=kind,
                    pattern=pattern,
                    regex=compile_regex(config_path, pattern, node.attrib.get("flags", "")),
                    message=message,
                )
            )
            continue
        if kind == "require-regex":
            pattern = require_attr(config_path, node, "pattern")
            rules.append(
                Rule(
                    kind=kind,
                    pattern=pattern,
                    regex=compile_regex(config_path, pattern, node.attrib.get("flags", "")),
                    message=message,
                )
            )
            continue
        if kind in ("forbid-trailing-whitespace", "require-final-newline"):
            rules.append(Rule(kind=kind, message=message))
            continue
        raise KomplyConfigError(
            f"{config_path}: unsupported rule <{kind}>. Supported rules: {', '.join(SUPPORTED_RULES)}"
        )
    return rules


def parse_positive_int(config_path: Path, node: ET.Element, name: str) -> int:
    raw = require_attr(config_path, node, name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise KomplyConfigError(
            f"{config_path}: <{node.tag}> attribute '{name}' must be an integer"
        ) from exc
    if value <= 0:
        raise KomplyConfigError(
            f"{config_path}: <{node.tag}> attribute '{name}' must be > 0"
        )
    return value


def require_attr(config_path: Path, node: ET.Element, name: str) -> str:
    value = (node.attrib.get(name) or "").strip()
    if not value:
        raise KomplyConfigError(
            f"{config_path}: <{node.tag}> requires attribute '{name}'"
        )
    return value


def compile_regex(config_path: Path, pattern: str, flag_text: str) -> re.Pattern[str]:
    flags = 0
    for letter in flag_text:
        if letter == "i":
            flags |= re.IGNORECASE
            continue
        if letter == "m":
            flags |= re.MULTILINE
            continue
        if letter == "s":
            flags |= re.DOTALL
            continue
        if letter == "x":
            flags |= re.VERBOSE
            continue
        raise KomplyConfigError(
            f"{config_path}: unsupported regex flag '{letter}'"
        )

    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise KomplyConfigError(
            f"{config_path}: invalid regex '{pattern}' ({exc})"
        ) from exc


def discover_targets(repo_root: Path, config_dir: Path, policy: Policy) -> list[Path]:
    config_prefix: str | None = None
    try:
        config_dir_rel = config_dir.relative_to(repo_root)
        config_prefix = config_dir_rel.as_posix() + "/"
    except ValueError:
        config_prefix = None
    targets: list[Path] = []

    for path in repo_root.rglob(f"*{policy.extension}"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        if config_prefix and rel.startswith(config_prefix):
            continue
        if rel.startswith(".git/"):
            continue
        if not matches_filters(rel, policy.includes, policy.excludes):
            continue
        targets.append(path)

    return sorted(targets)


def matches_filters(path: str, includes: tuple[str, ...], excludes: tuple[str, ...]) -> bool:
    if includes and not any(fnmatch(path, pattern) for pattern in includes):
        return False
    if any(fnmatch(path, pattern) for pattern in excludes):
        return False
    return True


def evaluate_file(path: Path, policy: Policy) -> list[Violation]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    violations: list[Violation] = []

    for rule in policy.rules:
        if rule.kind == "max-line-length":
            assert rule.value is not None
            for idx, line in enumerate(lines, start=1):
                if len(line) > rule.value:
                    violations.append(
                        Violation(
                            path=path,
                            line=idx,
                            rule=rule.kind,
                            message=rule.message
                            or f"Line length {len(line)} exceeds max {rule.value}",
                        )
                    )
            continue

        if rule.kind == "max-lines":
            assert rule.value is not None
            line_count = len(lines)
            if line_count > rule.value:
                violations.append(
                    Violation(
                        path=path,
                        rule=rule.kind,
                        message=rule.message
                        or f"File has {line_count} lines; max is {rule.value}",
                    )
                )
            continue

        if rule.kind == "forbid-regex":
            assert rule.regex is not None
            assert rule.pattern is not None
            for match in rule.regex.finditer(text):
                violations.append(
                    Violation(
                        path=path,
                        line=line_number(text, match.start()),
                        rule=rule.kind,
                        message=rule.message or f"Forbidden pattern matched: {rule.pattern}",
                    )
                )
            continue

        if rule.kind == "require-regex":
            assert rule.regex is not None
            assert rule.pattern is not None
            if not rule.regex.search(text):
                violations.append(
                    Violation(
                        path=path,
                        rule=rule.kind,
                        message=rule.message or f"Required pattern missing: {rule.pattern}",
                    )
                )
            continue

        if rule.kind == "forbid-trailing-whitespace":
            for idx, line in enumerate(lines, start=1):
                if line != line.rstrip(" \t"):
                    violations.append(
                        Violation(
                            path=path,
                            line=idx,
                            rule=rule.kind,
                            message=rule.message or "Trailing whitespace is not allowed",
                        )
                    )
            continue

        if rule.kind == "require-final-newline":
            if text and not text.endswith("\n"):
                violations.append(
                    Violation(
                        path=path,
                        line=max(1, len(lines)),
                        rule=rule.kind,
                        message=rule.message or "File must end with a newline",
                    )
                )
            continue

    return violations


def line_number(text: str, char_offset: int) -> int:
    return text.count("\n", 0, char_offset) + 1
