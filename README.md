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

Komply also supports an optional project runtime config file at
`.komply/00-config.xml` for scan-wide settings such as ignored directories.

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

Regex rules also support:

- `include-strings="true|false"` (default `true`); set to `false` to ignore string literals
- `include-comments="true|false"` (default `true`); set to `false` to ignore C/C++ line and block comments

For C++ code checks, set `include-strings="false"` and `include-comments="false"` so SQL and other text do not
trigger keyword rules. The bundled `NULL` and `new`/`delete` rules use these settings:

```xml
<forbid-regex pattern="\bNULL\b" include-strings="false" include-comments="false" />
<forbid-regex pattern="\b(new|delete)\b" include-strings="false" include-comments="false" />
```

This handles ordinary quoted strings and C++ raw strings such as `R"sql(...)sql"`,
including multiline raw strings. Code checks ignore comments; TODO/FIXME checks
still include comments.

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

Policy loading behavior:

- `--config-dir` remains a direct policy directory override
- Without `--config-dir`, Komply loads project policies from `<repo_root>/.komply`
  and fallback policies from `<komply install root>/.komply`
- Project policies override only matching fallback policies by filename stem
  (for example local `cpp.xml` overrides fallback `cpp.xml`)
- Fallback policies without a local override remain active
- `00-config.xml` is reserved for runtime config and is not treated as a policy

Runtime config format (`.komply/00-config.xml`):

```xml
<komply-config version="1">
  <scan>
    <ignore-directory path="build" />
    <ignore-directory path="vendor" />
    <ignore-directory path="src/generated" />
  </scan>
</komply-config>
```

Notes:

- `ignore-directory` paths are repo-relative directory paths (not globs)
- ignored directories are pruned during traversal before per-policy filters run

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

Install on Linux or macOS with Python 3.10 or newer:

```bash
git clone <repository-url>
cd komply
./install.sh
```

The installer creates only a launcher pointing to this clone. It checks
`~/.local/bin`, `~/bin`, then `/usr/local/bin`, choosing the first writable
directory already on `PATH` (excluding the clone itself). App-specific `PATH`
directories are never selected automatically.
You can then run `komply` immediately. Keep the clone in place.
If no writable directory is available, it falls back to `~/.local/bin` and
prints the line to add to your shell startup file (for example `~/.bashrc` or
`~/.zshrc`).
No Python packages or administrator permissions are required.

```bash
cd /path/to/project
komply
komply --quiet
```

The current directory is the scan root, even when it is not a Git repository.
Komply reads that directory's `.komply` policies and `00-config.xml`, with the
bundled policies providing the fallback described above. It does not search
parent directories for a project root.

Use `./install.sh --prefix /custom/path` to choose another install prefix; put
`/custom/path/bin` on `PATH`. Set `ALT_PYTHON` to choose a Python interpreter.
Updates to the clone take effect immediately. If you move the clone, rerun the
installer from its new location. To uninstall, remove the launcher at the path
printed by the installer.

You can also run directly from the clone:

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
