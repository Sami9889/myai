from __future__ import annotations
from pathlib import Path
from typing import Any
from .base_tool import BaseTool, ToolResult
from utils.validators import confined_path, require_int
class FileReader(BaseTool):
    name='read_file'; description='Read a bounded text file from the workspace.'
    def __init__(self, workspace: str = '.') -> None: self.workspace=Path(workspace).resolve()
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path=confined_path(self.string(arguments,'path'),self.workspace); start=require_int(arguments.get('start',0),'start',0); end=arguments.get('end')
        if end is not None: end=require_int(end,'end',start)
        return {'path':path,'start':start,'end':end}
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        lines=arguments['path'].read_text(encoding='utf-8').splitlines(True); return ToolResult(True,''.join(lines[arguments['start']:arguments['end']]))
