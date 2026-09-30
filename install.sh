#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAVA_BIN="${JAVA_BIN:-java}"
MAVEN_BIN="${MAVEN_BIN:-mvn}"
BIN_DIR="${MYAI_BIN_DIR:-${HOME}/.local/bin}"

fail() { printf 'myai install: %s\n' "$*" >&2; exit 1; }
command -v "$JAVA_BIN" >/dev/null 2>&1 || fail "java is required"
command -v "$MAVEN_BIN" >/dev/null 2>&1 || fail "maven is required"

mkdir -p "$BIN_DIR"
ln -sfn "$PROJECT_ROOT/bin/myai" "$BIN_DIR/myai"
ln -sfn "$PROJECT_ROOT/bin/myai-update" "$BIN_DIR/myai-update"
chmod +x "$PROJECT_ROOT/bin/myai"
chmod +x "$PROJECT_ROOT/bin/myai-update"

completion='\n# myai local CLI\nexport PATH="$HOME/.local/bin:$PATH"\n'
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
  [[ -f "$rc" ]] || touch "$rc"
  grep -Fq '# myai local CLI' "$rc" || printf '%s' "$completion" >> "$rc"
done

printf 'myai installed. Run: myai\n'
