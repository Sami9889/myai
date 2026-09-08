from __future__ import annotations
from typing import Any
from .base_tool import BaseTool, ToolResult
from .shell_runner import ShellRunner
class CodeExecutor(BaseTool):
    name='python'; description='Execute a Python snippet with timeout and no inherited environment.'
    def __init__(self, workspace: str='.', confirmer=None) -> None: self.runner=ShellRunner(workspace,confirmer)
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]: return {'code':self.string(arguments,'code'),'timeout':arguments.get('timeout',10)}
    def execute(self, arguments: dict[str, Any]) -> ToolResult: return self.runner.run({'command':'python3 -I -c '+repr(arguments['code']),'timeout':arguments['timeout']})
