from __future__ import annotations
from pathlib import Path
from typing import Any
import subprocess
from .base_tool import BaseTool, ToolResult
from utils.validators import confined_path

class RepoManager(BaseTool):
    name = 'repo'
    description = 'Inspect and explicitly publish changes in the current Git repository.'

    def __init__(self, workspace: str = '.') -> None:
        self.workspace = Path(workspace).resolve()

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation = self.string(arguments, 'operation')
        if operation not in {'status', 'add', 'commit', 'push'}:
            raise ValueError('operation must be status, add, commit, or push')
        confirm = arguments.get('confirm', False)
        if not isinstance(confirm, bool):
            raise ValueError('confirm must be boolean')
        paths = arguments.get('paths', [])
        if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
            raise ValueError('paths must be a list of strings')
        message = arguments.get('message', '')
        if not isinstance(message, str):
            raise ValueError('message must be a string')
        return {'operation': operation, 'confirm': confirm, 'paths': paths, 'message': message}

    def _run(self, args: list[str]) -> ToolResult:
        try:
            completed = subprocess.run(['git', *args], cwd=self.workspace, text=True, capture_output=True, check=False)
        except OSError as exc:
            return ToolResult(False, '', str(exc))
        output = (completed.stdout + completed.stderr).strip()
        return ToolResult(completed.returncode == 0, output, f'git exited with {completed.returncode}' if completed.returncode else None)

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        operation = arguments['operation']
        if operation == 'status':
            return self._run(['status', '--short', '--branch'])
        if not arguments['confirm']:
            return ToolResult(False, '', f'{operation} requires explicit --confirm')
        if operation == 'add':
            paths = arguments['paths'] or ['.']
            safe_paths = [str(confined_path(path, self.workspace).relative_to(self.workspace)) for path in paths]
            return self._run(['add', '--', *safe_paths])
        if operation == 'commit':
            message = arguments['message'].strip()
            if not message:
                return ToolResult(False, '', 'commit requires a non-empty message')
            return self._run(['commit', '-m', message])
        return self._run(['push', 'origin', 'HEAD'])
