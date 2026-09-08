from __future__ import annotations
from pathlib import Path
from typing import Any
import ast
from .base_tool import BaseTool, ToolResult
class LinterBridge(BaseTool):
    name='lint'; description='Run Python syntax validation without external linters.'
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]: return {'path':Path(self.string(arguments,'path'))}
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        try: ast.parse(arguments['path'].read_text(encoding='utf-8'),str(arguments['path'])); return ToolResult(True,'syntax valid')
        except SyntaxError as exc: return ToolResult(False,'',f'{exc.filename}:{exc.lineno}:{exc.offset}: {exc.msg}')
