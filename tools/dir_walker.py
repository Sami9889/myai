from __future__ import annotations
from pathlib import Path
from typing import Any
import fnmatch
from .base_tool import BaseTool, ToolResult
class DirWalker(BaseTool):
    name='walk'; description='Index files while respecting common ignore directories.'
    def __init__(self, workspace: str='.') -> None: self.workspace=Path(workspace).resolve()
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]: return {'pattern':arguments.get('pattern','*')}
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        ignored={'.git','.venv','__pycache__','node_modules'}; rows=[]
        for path in self.workspace.rglob(arguments['pattern']):
            if path.is_file() and not ignored.intersection(path.parts): rows.append(str(path.relative_to(self.workspace)))
        return ToolResult(True,'\n'.join(sorted(rows)))
