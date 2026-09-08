from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from utils.validators import require_string

@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    output: str
    error: str | None = None

class BaseTool(ABC):
    name: str
    description: str
    @abstractmethod
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]: ...
    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> ToolResult: ...
    def run(self, arguments: dict[str, Any]) -> ToolResult:
        if not isinstance(arguments, dict): return ToolResult(False, '', 'arguments must be a JSON object')
        try: return self.execute(self.validate(arguments))
        except Exception as exc: return ToolResult(False, '', f'{type(exc).__name__}: {exc}')
    @staticmethod
    def string(arguments: dict[str, Any], name: str, default: str | None = None) -> str:
        value = arguments.get(name, default)
        return require_string(value, name)
