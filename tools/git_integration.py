from __future__ import annotations
from typing import Any
from .base_tool import BaseTool, ToolResult
from .shell_runner import ShellRunner
class GitIntegration(BaseTool):
    name='git'; description='Inspect git state with safe read-only operations.'
    def __init__(self, workspace: str='.') -> None: self.runner=ShellRunner(workspace,lambda *_: True)
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation=self.string(arguments,'operation')
        if operation not in {'status','diff','log','branch'}: raise ValueError('operation is not read-only or supported')
        return {'operation':operation}
    def execute(self, arguments: dict[str, Any]) -> ToolResult: return self.runner.run({'command':f"git {arguments['operation']}"})
