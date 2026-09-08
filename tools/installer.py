from __future__ import annotations
from pathlib import Path
from typing import Any
import subprocess
from .base_tool import BaseTool, ToolResult

class Installer(BaseTool):
    name = 'install'
    description = 'Install the current repository into its local virtual environment.'

    def __init__(self, workspace: str = '.') -> None:
        self.workspace = Path(workspace).resolve()

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        confirm = arguments.get('confirm', False)
        if not isinstance(confirm, bool):
            raise ValueError('confirm must be boolean')
        return {'confirm': confirm}

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        if not arguments['confirm']:
            return ToolResult(False, '', 'installation requires explicit confirmation; say "install this repo yes"')
        script = self.workspace / 'install.sh'
        if not script.is_file():
            return ToolResult(False, '', 'install.sh was not found in the selected repository')
        try:
            completed = subprocess.run(['bash', str(script)], cwd=self.workspace, text=True, capture_output=True, check=False)
        except OSError as exc:
            return ToolResult(False, '', str(exc))
        output = (completed.stdout + completed.stderr).strip()
        return ToolResult(completed.returncode == 0, output, f'installer exited with {completed.returncode}' if completed.returncode else None)
