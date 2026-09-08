from __future__ import annotations
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
import os
from datetime import datetime, timezone
from .base_tool import BaseTool, ToolResult
from utils.validators import confined_path
class FileWriter(BaseTool):
    name='write_file'; description='Atomically write a text file in the workspace.'
    def __init__(self, workspace: str='.') -> None: self.workspace=Path(workspace).resolve()
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path=confined_path(self.string(arguments,'path'),self.workspace); content=arguments.get('content')
        if not isinstance(content,str): raise ValueError('content must be a string')
        return {'path':path,'content':content}
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        path=arguments['path']; path.parent.mkdir(parents=True,exist_ok=True)
        with NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as stream: stream.write(arguments['content']); temporary=stream.name
        os.replace(temporary,path)
        edited_at = datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
        return ToolResult(True, f'Edited: {path}\nTime: {edited_at}')
