# Komply

Komply is a repository scanner that enforces XML-defined coding policies.

It discovers policy files in `.komply/*.xml`, maps each policy file name to a
file extension, and checks matching files recursively.

Example:

- `.komply/cpp.xml` applies to all `*.cpp` files
- `.komply/py.xml` applies to all `*.py` files

You can override target matching on `<komply>` for extensionless or custom files:

- `match="extension"` with optional `pattern=".cpp"` (default behavior)
- `match="filename"` with `pattern="Makefile"` (or glob on filename)
- `match="glob"` with `pattern="**/Makefile"` (repo-relative path glob)

## Supported Rules

- `max-line-length value="N"`
- `max-lines value="N"`
- `max-function-lines value="N"`
- `forbid-regex pattern="..."`
- `require-regex pattern="..."`
- `forbid-trailing-whitespace`
- `require-final-newline`

All rules also support optional quality attributes:

- `tier="..."` groups findings by area (`critical`, `style`, etc.)
- `blocking="true|false"` marks a rule as hard-fail
- `weight="N"` penalty points for non-blocking findings

## Policy Format

```xml
<komply>
  <filters>
    <include glob="src/*.cpp" />
    <exclude glob="src/generated/*" />
  </filters>
  <rules>
    <max-line-length value="120" tier="maintainability" weight="2" />
    <max-function-lines value="120" tier="maintainability" weight="8" />
    <forbid-regex pattern="\busing\s+namespace\s+std\b" tier="critical" blocking="true" />
    <forbid-regex pattern="\bTODO\b" tier="delivery" weight="5" />
    <forbid-trailing-whitespace tier="style" weight="2" />
    <require-final-newline tier="style" weight="1" />
  </rules>
</komply>
```

`<filters>` is optional. If omitted, Komply checks every matching file extension
recursively from repo root.

`max-function-lines` uses a lightweight brace-based parser and is best-effort for C/C++ code.
It also supports custom delimiters for other languages:

- `open="..."` and `close="..."` block delimiters
- `start-pattern="regex"` optional header matcher
- `exclude-pattern="regex"` optional header exclusion

Example:

```xml
<max-function-lines
  value="80"
  open="begin"
  close="end"
  start-pattern="\bfunction\b"
  tier="maintainability"
  weight="8"
/>
```

Config directory resolution order:

- `--config-dir` when provided
- `<current working directory>/.komply` when present
- `<komply install root>/.komply` as fallback

## Quality Rating

Komply computes a quality score and status for each run:

- Start score at `100`
- Subtract `weight` for each non-blocking violation
- Clamp score to `0..100`
- Grade mapping: `A>=90`, `B>=80`, `C>=70`, `D>=60`, `E>=50`, else `F`
- Status:
  - `FF`: one or more blocking violations (absolute fail)
  - `PA`..`PF`: no blocking violations, pass with computed grade

## Usage

```bash
./komply
./komply --repo-root /path/to/repo
./komply --config-dir .komply
```

Exit codes:

- `0`: no blocking violations (`PA`..`PF`)
- `1`: blocking violation found (`FF`)
- `2`: configuration/runtime error

## Development

```bash
make test
```
