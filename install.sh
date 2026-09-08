#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-${PROJECT_ROOT}/.venv}"
BIN_DIR="${MYAI_BIN_DIR:-${HOME}/.local/bin}"

fail() { printf 'myai install: %s\n' "$*" >&2; exit 1; }
command -v "$PYTHON_BIN" >/dev/null 2>&1 || fail "python3 is required"
"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("myai requires Python 3.11 or newer")
PY

if [[ ! -d "$VENV_DIR" ]]; then "$PYTHON_BIN" -m venv "$VENV_DIR"; fi
PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_DIR/bin/python" -m pip install --no-deps -e "$PROJECT_ROOT" >/dev/null
rm -rf "$PROJECT_ROOT/myai.egg-info"
mkdir -p "$BIN_DIR"
ln -sfn "$PROJECT_ROOT/bin/myai" "$BIN_DIR/myai"
ln -sfn "$PROJECT_ROOT/bin/myai-update" "$BIN_DIR/myai-update"
ln -sfn "$PROJECT_ROOT/bin/myai-update" "$VENV_DIR/bin/myai-update"
chmod +x "$PROJECT_ROOT/bin/myai"
chmod +x "$PROJECT_ROOT/bin/myai-update"

completion='\n# myai local CLI\nexport PATH="$HOME/.local/bin:$PATH"\n'
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
  [[ -f "$rc" ]] || touch "$rc"
  grep -Fq '# myai local CLI' "$rc" || printf '%s' "$completion" >> "$rc"
done

"$VENV_DIR/bin/python" -m compileall -q "$PROJECT_ROOT/core_engine" "$PROJECT_ROOT/agent_runtime" "$PROJECT_ROOT/tools" "$PROJECT_ROOT/cli_interface" "$PROJECT_ROOT/utils"
"$VENV_DIR/bin/python" -m cli_interface.repl --version >/dev/null
printf 'myai installed successfully. Activate with: source %s/bin/activate\n' "$VENV_DIR"
