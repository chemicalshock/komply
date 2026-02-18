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
    tier: str = "default"
    blocking: bool = False
    weight: int = 5
    open_token: str = "{"
    close_token: str = "}"
    start_regex: re.Pattern[str] | None = None
    exclude_regex: re.Pattern[str] | None = None


@dataclass(frozen=True)
class Policy:
    name: str
    matcher_kind: str
    matcher_value: str
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
    tier: str = "default"
    blocking: bool = False
    weight: int = 0


@dataclass(frozen=True)
class ScanReport:
    policies_loaded: int
    files_by_policy: dict[str, int]
    violations: list[Violation]
    blocking_violations: int
    non_blocking_violations: int
    weighted_penalty: int
    quality_score: int
    quality_grade: str
    quality_status: str


SUPPORTED_RULES = (
    "max-line-length",
    "max-lines",
    "max-function-lines",
    "forbid-regex",
    "require-regex",
    "forbid-trailing-whitespace",
    "require-final-newline",
)
SUPPORTED_MATCH_KINDS = ("extension", "filename", "glob")


def scan_repository(repo_root: Path, config_dir: Path) -> ScanReport:
    policies = load_policies(config_dir)
    files_by_policy: dict[str, int] = {}
    violations: list[Violation] = []

    for policy in policies:
        targets = discover_targets(repo_root, config_dir, policy)
        files_by_policy[policy.name] = len(targets)
        for target in targets:
            violations.extend(evaluate_file(target, policy))

    sorted_violations = sorted(
        violations,
        key=lambda item: (item.path.as_posix(), item.line or 0, item.rule),
    )
    blocking_count = sum(1 for item in sorted_violations if item.blocking)
    non_blocking_count = len(sorted_violations) - blocking_count
    weighted_penalty = sum(item.weight for item in sorted_violations if not item.blocking)
    quality_score = max(0, 100 - weighted_penalty)
    quality_grade = score_to_grade(quality_score)
    quality_status = "FF" if blocking_count else f"P{quality_grade}"

    return ScanReport(
        policies_loaded=len(policies),
        files_by_policy=files_by_policy,
        violations=sorted_violations,
        blocking_violations=blocking_count,
        non_blocking_violations=non_blocking_count,
        weighted_penalty=weighted_penalty,
        quality_score=quality_score,
        quality_grade=quality_grade,
        quality_status=quality_status,
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
    matcher_kind = "extension"
    matcher_value = extension

    try:
        root = ET.parse(config_path).getroot()
    except ET.ParseError as exc:
        raise KomplyConfigError(f"{config_path}: invalid XML ({exc})") from exc

    if root.tag == "komply":
        filters_parent = root.find("filters")
        rules_parent = root.find("rules")
        if rules_parent is None:
            raise KomplyConfigError(f"{config_path}: missing <rules> block")
        matcher_kind, matcher_value = parse_target_matcher(
            config_path=config_path,
            root=root,
            default_extension=extension,
        )
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
        matcher_kind=matcher_kind,
        matcher_value=matcher_value,
        config_path=config_path,
        includes=tuple(includes),
        excludes=tuple(excludes),
        rules=tuple(rules),
    )


def parse_target_matcher(
    config_path: Path,
    root: ET.Element,
    default_extension: str,
) -> tuple[str, str]:
    raw_kind = (root.attrib.get("match") or "").strip()
    raw_pattern = (root.attrib.get("pattern") or "").strip()

    if not raw_kind:
        return "extension", default_extension
    if raw_kind not in SUPPORTED_MATCH_KINDS:
        raise KomplyConfigError(
            f"{config_path}: attribute 'match' must be one of: {', '.join(SUPPORTED_MATCH_KINDS)}"
        )
    if raw_kind == "extension":
        pattern = raw_pattern or default_extension
        if not pattern.startswith("."):
            pattern = f".{pattern}"
        return raw_kind, pattern

    if not raw_pattern:
        raise KomplyConfigError(
            f"{config_path}: attribute 'pattern' is required when match='{raw_kind}'"
        )
    return raw_kind, raw_pattern


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
        tier = parse_tier(node)
        blocking = parse_bool_attr(config_path, node, "blocking", default=False)
        default_weight = 0 if blocking else 5
        weight = parse_non_negative_int_attr(
            config_path, node, "weight", default=default_weight
        )
        if kind == "max-line-length":
            rules.append(
                Rule(
                    kind=kind,
                    value=parse_positive_int(config_path, node, "value"),
                    message=message,
                    tier=tier,
                    blocking=blocking,
                    weight=weight,
                )
            )
            continue
        if kind == "max-lines":
            rules.append(
                Rule(
                    kind=kind,
                    value=parse_positive_int(config_path, node, "value"),
                    message=message,
                    tier=tier,
                    blocking=blocking,
                    weight=weight,
                )
            )
            continue
        if kind == "max-function-lines":
            open_token = node.attrib.get("open", "{")
            close_token = node.attrib.get("close", "}")
            if not open_token or not close_token:
                raise KomplyConfigError(
                    f"{config_path}: <{kind}> attributes 'open' and 'close' must be non-empty"
                )
            if open_token == close_token:
                raise KomplyConfigError(
                    f"{config_path}: <{kind}> attributes 'open' and 'close' must differ"
                )
            rules.append(
                Rule(
                    kind=kind,
                    value=parse_positive_int(config_path, node, "value"),
                    message=message,
                    tier=tier,
                    blocking=blocking,
                    weight=weight,
                    open_token=open_token,
                    close_token=close_token,
                    start_regex=compile_optional_regex(
                        config_path,
                        node,
                        "start-pattern",
                    ),
                    exclude_regex=compile_optional_regex(
                        config_path,
                        node,
                        "exclude-pattern",
                    ),
                )
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
                    tier=tier,
                    blocking=blocking,
                    weight=weight,
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
                    tier=tier,
                    blocking=blocking,
                    weight=weight,
                )
            )
            continue
        if kind in ("forbid-trailing-whitespace", "require-final-newline"):
            rules.append(
                Rule(
                    kind=kind,
                    message=message,
                    tier=tier,
                    blocking=blocking,
                    weight=weight,
                )
            )
            continue
        raise KomplyConfigError(
            f"{config_path}: unsupported rule <{kind}>. Supported rules: {', '.join(SUPPORTED_RULES)}"
        )
    return rules


def parse_tier(node: ET.Element) -> str:
    tier = (node.attrib.get("tier") or "default").strip()
    if not tier:
        return "default"
    return tier


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


def parse_non_negative_int_attr(
    config_path: Path, node: ET.Element, name: str, default: int
) -> int:
    raw = (node.attrib.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise KomplyConfigError(
            f"{config_path}: <{node.tag}> attribute '{name}' must be an integer"
        ) from exc
    if value < 0:
        raise KomplyConfigError(
            f"{config_path}: <{node.tag}> attribute '{name}' must be >= 0"
        )
    return value


def parse_bool_attr(
    config_path: Path, node: ET.Element, name: str, default: bool
) -> bool:
    raw = (node.attrib.get(name) or "").strip().lower()
    if not raw:
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    raise KomplyConfigError(
        f"{config_path}: <{node.tag}> attribute '{name}' must be a boolean"
    )


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


def compile_optional_regex(
    config_path: Path,
    node: ET.Element,
    attr: str,
) -> re.Pattern[str] | None:
    raw = (node.attrib.get(attr) or "").strip()
    if not raw:
        return None
    try:
        return re.compile(raw)
    except re.error as exc:
        raise KomplyConfigError(
            f"{config_path}: invalid regex in '{attr}' ({exc})"
        ) from exc


def discover_targets(repo_root: Path, config_dir: Path, policy: Policy) -> list[Path]:
    config_prefix: str | None = None
    try:
        config_dir_rel = config_dir.relative_to(repo_root)
        config_prefix = config_dir_rel.as_posix() + "/"
    except ValueError:
        config_prefix = None
    targets: list[Path] = []

    iterator = candidate_iterator(repo_root, policy)
    for path in iterator:
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        if config_prefix and rel.startswith(config_prefix):
            continue
        if rel.startswith(".git/"):
            continue
        if not matches_policy_target(path, rel, policy):
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


def candidate_iterator(repo_root: Path, policy: Policy):
    if policy.matcher_kind == "extension":
        return repo_root.rglob(f"*{policy.matcher_value}")
    return repo_root.rglob("*")


def matches_policy_target(path: Path, rel_path: str, policy: Policy) -> bool:
    if policy.matcher_kind == "extension":
        return rel_path.endswith(policy.matcher_value)
    if policy.matcher_kind == "filename":
        return fnmatch(path.name, policy.matcher_value)
    if policy.matcher_kind == "glob":
        return fnmatch(rel_path, policy.matcher_value)
    return False


def evaluate_file(path: Path, policy: Policy) -> list[Violation]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    violations: list[Violation] = []
    function_spans: list[tuple[int, int]] | None = None

    for rule in policy.rules:
        if rule.kind == "max-line-length":
            assert rule.value is not None
            for idx, line in enumerate(lines, start=1):
                if len(line) > rule.value:
                    violations.append(
                        make_violation(
                            path=path,
                            rule=rule,
                            line=idx,
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
                    make_violation(
                        path=path,
                        rule=rule,
                        message=rule.message
                        or f"File has {line_count} lines; max is {rule.value}",
                    )
                )
            continue

        if rule.kind == "max-function-lines":
            assert rule.value is not None
            if function_spans is None:
                function_spans = find_function_spans(
                    text=text,
                    open_token=rule.open_token,
                    close_token=rule.close_token,
                    start_regex=rule.start_regex,
                    exclude_regex=rule.exclude_regex,
                )
            for start_line, end_line in function_spans:
                function_lines = end_line - start_line + 1
                if function_lines > rule.value:
                    violations.append(
                        make_violation(
                            path=path,
                            rule=rule,
                            line=start_line,
                            message=rule.message
                            or f"Function body has {function_lines} lines; max is {rule.value}",
                        )
                    )
            continue

        if rule.kind == "forbid-regex":
            assert rule.regex is not None
            assert rule.pattern is not None
            for match in rule.regex.finditer(text):
                violations.append(
                    make_violation(
                        path=path,
                        rule=rule,
                        line=line_number(text, match.start()),
                        message=rule.message or f"Forbidden pattern matched: {rule.pattern}",
                    )
                )
            continue

        if rule.kind == "require-regex":
            assert rule.regex is not None
            assert rule.pattern is not None
            if not rule.regex.search(text):
                violations.append(
                    make_violation(
                        path=path,
                        rule=rule,
                        message=rule.message or f"Required pattern missing: {rule.pattern}",
                    )
                )
            continue

        if rule.kind == "forbid-trailing-whitespace":
            for idx, line in enumerate(lines, start=1):
                if line != line.rstrip(" \t"):
                    violations.append(
                        make_violation(
                            path=path,
                            rule=rule,
                            line=idx,
                            message=rule.message or "Trailing whitespace is not allowed",
                        )
                    )
            continue

        if rule.kind == "require-final-newline":
            if text and not text.endswith("\n"):
                violations.append(
                    make_violation(
                        path=path,
                        rule=rule,
                        line=max(1, len(lines)),
                        message=rule.message or "File must end with a newline",
                    )
                )
            continue

    return violations


def line_number(text: str, char_offset: int) -> int:
    return text.count("\n", 0, char_offset) + 1


def find_function_spans(
    text: str,
    open_token: str = "{",
    close_token: str = "}",
    start_regex: re.Pattern[str] | None = None,
    exclude_regex: re.Pattern[str] | None = None,
) -> list[tuple[int, int]]:
    cleaned = mask_non_code(text)
    block_pairs = match_token_pairs(cleaned, open_token=open_token, close_token=close_token)
    spans: list[tuple[int, int]] = []
    for open_idx, (open_line, close_line) in block_pairs.items():
        header = extract_header_context(cleaned, open_idx, open_token)
        if start_regex is not None and not start_regex.search(header):
            continue
        if exclude_regex is not None and exclude_regex.search(header):
            continue
        if start_regex is None and open_token == "{" and close_token == "}":
            if not is_function_open_brace(cleaned, open_idx):
                continue
        spans.append((open_line, close_line))
    spans.sort()
    return spans


def mask_non_code(text: str) -> str:
    out: list[str] = []
    in_line_comment = False
    in_block_comment = False
    in_single_quote = False
    in_double_quote = False
    escaped = False

    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        nxt = text[i + 1] if i + 1 < length else ""

        if in_line_comment:
            if char == "\n":
                in_line_comment = False
                out.append("\n")
            else:
                out.append(" ")
            i += 1
            continue

        if in_block_comment:
            if char == "*" and nxt == "/":
                in_block_comment = False
                out.extend((" ", " "))
                i += 2
                continue
            out.append("\n" if char == "\n" else " ")
            i += 1
            continue

        if in_single_quote:
            if char == "\n":
                in_single_quote = False
                escaped = False
                out.append("\n")
                i += 1
                continue
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                in_single_quote = False
            out.append(" ")
            i += 1
            continue

        if in_double_quote:
            if char == "\n":
                in_double_quote = False
                escaped = False
                out.append("\n")
                i += 1
                continue
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_double_quote = False
            out.append(" ")
            i += 1
            continue

        if char == "/" and nxt == "/":
            in_line_comment = True
            out.extend((" ", " "))
            i += 2
            continue
        if char == "/" and nxt == "*":
            in_block_comment = True
            out.extend((" ", " "))
            i += 2
            continue
        if char == "'":
            in_single_quote = True
            out.append(" ")
            i += 1
            continue
        if char == '"':
            in_double_quote = True
            out.append(" ")
            i += 1
            continue

        out.append(char)
        i += 1

    return "".join(out)


def match_token_pairs(
    text: str,
    open_token: str,
    close_token: str,
) -> dict[int, tuple[int, int]]:
    pairs: dict[int, tuple[int, int]] = {}
    stack: list[tuple[int, int]] = []
    line = 1
    i = 0
    text_len = len(text)

    while i < text_len:
        if text.startswith(open_token, i):
            stack.append((i, line))
            i += len(open_token)
            continue
        if text.startswith(close_token, i):
            if stack:
                open_index, open_line = stack.pop()
                pairs[open_index] = (open_line, line)
            i += len(close_token)
            continue
        if text[i] == "\n":
            line += 1
        i += 1
    return pairs


def is_function_open_brace(text: str, open_idx: int) -> bool:
    header = extract_header_context(text, open_idx, "{")
    normalized = " ".join(header.split())

    if not normalized:
        return False
    if "(" not in normalized or ")" not in normalized:
        return False
    if re.search(r"\b(if|for|while|switch|catch)\s*\([^)]*\)\s*$", normalized):
        return False
    if re.search(r"\b(else|do|try)\s*$", normalized):
        return False
    if re.search(r"^\s*(class|struct|enum|namespace|union)\b", normalized):
        return False
    if re.search(r"\[[^\]]*\]\s*(\([^)]*\))?\s*(mutable\s*)?(noexcept\s*)?(->\s*[^\s{]+)?\s*$", normalized):
        return False
    return True


def extract_header_context(text: str, open_idx: int, open_token: str) -> str:
    context = text[max(0, open_idx - 400) : open_idx]
    header = context.rsplit(";", maxsplit=1)[-1]
    header = header.rsplit("}", maxsplit=1)[-1]
    header = header.rsplit(open_token, maxsplit=1)[-1]
    return header


def score_to_grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    if score >= 50:
        return "E"
    return "F"


def make_violation(path: Path, rule: Rule, message: str, line: int | None = None) -> Violation:
    return Violation(
        path=path,
        line=line,
        rule=rule.kind,
        message=message,
        tier=rule.tier,
        blocking=rule.blocking,
        weight=rule.weight,
    )
