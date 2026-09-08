from __future__ import annotations
from pathlib import Path
from typing import Any
import subprocess
from .base_tool import BaseTool, ToolResult
from utils.security_gates import require_confirmation
class ShellRunner(BaseTool):
    name='shell'; description='Run a non-network shell command after policy confirmation.'
    def __init__(self, workspace: str='.', confirmer=None) -> None: self.workspace=Path(workspace).resolve(); self.confirmer=confirmer or (lambda command, reason: False)
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        command=self.string(arguments,'command'); timeout=arguments.get('timeout',30)
        if not isinstance(timeout,(int,float)) or timeout<=0 or timeout>300: raise ValueError('timeout must be between 0 and 300 seconds')
        return {'command':command,'timeout':timeout}
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        require_confirmation(arguments['command'],self.confirmer)
        try:
            completed=subprocess.run(arguments['command'],shell=True,cwd=self.workspace,text=True,capture_output=True,timeout=arguments['timeout'],check=False)
            output=completed.stdout + completed.stderr; return ToolResult(completed.returncode==0,output,f'exit code {completed.returncode}' if completed.returncode else None)
        except subprocess.TimeoutExpired: return ToolResult(False,'','command timed out')
