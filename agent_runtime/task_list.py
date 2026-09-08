from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

@dataclass(slots=True)
class TaskItem:
    id: int
    title: str
    done: bool = False
    created_at: str = ''
    completed_at: str = ''

class TaskList:
    def __init__(self, workspace: str = '.') -> None:
        self.path = Path(workspace).resolve() / '.myai-tasks.json'
        self.items: list[TaskItem] = []
        self._load()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            rows = json.loads(self.path.read_text(encoding='utf-8'))
            self.items = [TaskItem(**row) for row in rows]
        except (OSError, ValueError, TypeError):
            self.items = []

    def _save(self) -> None:
        self.path.write_text(json.dumps([asdict(item) for item in self.items], indent=2) + '\n', encoding='utf-8')

    def add(self, title: str) -> TaskItem:
        item = TaskItem(max((task.id for task in self.items), default=0) + 1, title.strip(), created_at=self._now())
        if not item.title:
            raise ValueError('task title cannot be empty')
        self.items.append(item)
        self._save()
        return item

    def complete(self, task_id: int) -> TaskItem:
        for item in self.items:
            if item.id == task_id:
                item.done = True
                item.completed_at = self._now()
                self._save()
                return item
        raise ValueError(f'task {task_id} was not found')

    def clear_completed(self) -> int:
        before = len(self.items)
        self.items = [item for item in self.items if not item.done]
        self._save()
        return before - len(self.items)

    def render(self) -> str:
        if not self.items:
            return 'No tasks. Add one with: todo add "task description"'
        return '\n'.join(f"[{ 'x' if item.done else ' ' }] {item.id}: {item.title}" for item in self.items)
