from __future__ import annotations
from typing import Any
from .base_tool import BaseTool, ToolResult
from .file_writer import FileWriter
from .file_reader import FileReader
class FilePatcher(BaseTool):
    name='patch_file'; description='Replace one exact block in a workspace file.'
    def __init__(self, workspace: str='.') -> None: self.reader=FileReader(workspace); self.writer=FileWriter(workspace)
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path=self.string(arguments,'path'); old=self.string(arguments,'old'); new=arguments.get('new')
        if not isinstance(new,str): raise ValueError('new must be a string')
        return {'path':path,'old':old,'new':new}
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        result=self.reader.run({'path':arguments['path']})
        if not result.ok: return result
        if result.output.count(arguments['old']) != 1: return ToolResult(False,'','old block must occur exactly once')
        return self.writer.run({'path':arguments['path'],'content':result.output.replace(arguments['old'],arguments['new'],1)})
