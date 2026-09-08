from __future__ import annotations
from pathlib import Path
from typing import Any
import re
from .base_tool import BaseTool, ToolResult

class HelpSearch(BaseTool):
    name = 'search'
    description = 'Search local project documentation and source without network access.'
    extensions = {'.md', '.txt', '.py', '.toml', '.json', '.sh'}

    def __init__(self, workspace: str = '.') -> None:
        self.workspace = Path(workspace).resolve()

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = self.string(arguments, 'query')
        limit = arguments.get('limit', 8)
        if not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError('limit must be between 1 and 50')
        return {'query': query.lower(), 'limit': limit}

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        terms = [term for term in re.findall(r'[a-z0-9_]+', arguments['query']) if len(term) > 1]
        if not terms:
            return ToolResult(False, '', 'search query must contain letters or numbers')
        results: list[tuple[int, str, str]] = []
        ignored = {'.git', '.venv', '__pycache__', 'build', 'dist'}
        for path in self.workspace.rglob('*'):
            if path.name == '.myai-tasks.json' or not path.is_file() or path.suffix.lower() not in self.extensions or ignored.intersection(path.parts):
                continue
            try:
                lines = path.read_text(encoding='utf-8').splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, 1):
                lowered = line.lower()
                score = sum(lowered.count(term) for term in terms)
                if score:
                    results.append((score, str(path.relative_to(self.workspace)), f'{number}: {line.strip()}'))
        results.sort(key=lambda row: (-row[0], row[1], row[2]))
        if not results:
            return ToolResult(True, f'No local results for: {arguments["query"]}')
        return ToolResult(True, '\n'.join(f'{path}: {line}' for _, path, line in results[:arguments['limit']]))
