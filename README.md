# Komply

Komply is a repository scanner that enforces XML-defined coding policies.

It discovers policy files in `.komply/*.xml`, maps each policy file name to a
file extension, and checks matching files recursively.

Example:

- `.komply/cpp.xml` applies to all `*.cpp` files
- `.komply/py.xml` applies to all `*.py` files

## Supported Rules

- `max-line-length value="N"`
- `max-lines value="N"`
- `forbid-regex pattern="..."`
- `require-regex pattern="..."`
- `forbid-trailing-whitespace`
- `require-final-newline`

## Policy Format

```xml
<komply>
  <filters>
    <include glob="src/*.cpp" />
    <exclude glob="src/generated/*" />
  </filters>
  <rules>
    <max-line-length value="120" />
    <forbid-regex pattern="\bTODO\b" />
    <forbid-trailing-whitespace />
    <require-final-newline />
  </rules>
</komply>
```

`<filters>` is optional. If omitted, Komply checks every matching file extension
recursively from repo root.

Config directory resolution order:

- `--config-dir` when provided
- `<current working directory>/.komply` when present
- `<komply install root>/.komply` as fallback

## Usage

```bash
./komply
./komply --repo-root /path/to/repo
./komply --config-dir .komply
```

Exit codes:

- `0`: no violations
- `1`: violations found
- `2`: configuration/runtime error

## Development

```bash
make test
```
