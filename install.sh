#!/bin/sh
# Install a launcher without changing the caller's working directory.
set -eu

SOURCE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON_BIN="${ALT_PYTHON:-python3}"

exec "$PYTHON_BIN" - "$SOURCE_DIR" "$@" <<'PY'
import os
from pathlib import Path
import shlex
import sys

if sys.version_info < (3, 10):
    sys.exit("komply: Python 3.10 or newer is required")

args = sys.argv[2:]
if args == ["--help"]:
    print("Usage: ./install.sh [--prefix DIRECTORY] (default: ~/.local)")
    sys.exit(0)
if args and (len(args) != 2 or args[0] != "--prefix"):
    sys.exit("Usage: ./install.sh [--prefix DIRECTORY]")

source = Path(sys.argv[1]).resolve()
prefix = Path(args[1]).expanduser().resolve() if args else Path.home() / ".local"
bin_dir = prefix / "bin"
command = bin_dir / "komply"
if command.exists() or command.is_symlink():
    if command.is_symlink() or not command.is_file() or (
        "# Installed by komply/install.sh" not in command.read_text()
    ):
        sys.exit(f"komply: refusing to overwrite an unrelated command: {command}")

bin_dir.mkdir(parents=True, exist_ok=True)
command.write_text(
    "#!/bin/sh\n# Installed by komply/install.sh\n"
    f"exec {shlex.quote(str(source / 'komply'))} \"$@\"\n"
)
command.chmod(0o755)
print(f"Installed komply to {command}")
if str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep):
    print("Add this line to your shell startup file, then open a new shell:")
    print(f"  export PATH={shlex.quote(str(bin_dir))}:\"$PATH\"")
print("Run komply from any project directory to check that directory.")
PY
