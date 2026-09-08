from __future__ import annotations
from dataclasses import dataclass
import re
import shlex

@dataclass(frozen=True, slots=True)
class Intent:
    command: str
    arguments: list[str]
    explanation: str


def parse_intent(text: str) -> Intent | None:
    """Translate common natural requests into existing, bounded CLI commands."""
    original = text.strip()
    lowered = original.lower()
    if not original:
        return None
    if lowered == 'help':
        return Intent('help', [], 'show available capabilities')
    if any(phrase in lowered for phrase in ('what time', 'current time', 'time is it')):
        return Intent('time', [], 'show the local time')
    if any(phrase in lowered for phrase in ('repo status', 'git status', 'what changed', 'show changes')):
        return Intent('repo', ['status'], 'inspect repository status')
    if any(phrase in lowered for phrase in ('install this repo', 'install the repo', 'install myai', 'set up this repo')):
        return Intent('install', ['--confirm'] if any(word in lowered for word in ('yes', 'confirm', 'do it')) else [], 'install the current repository')
    if any(phrase in lowered for phrase in ('list tasks', 'show todos', 'show my tasks', 'todo list')):
        return Intent('todo', ['list'], 'show the TODO list')
    match = re.search(r'(?:add|create)\s+(?:a\s+)?(?:todo|task)\s*(?:for|:)?\s*(.+)$', original, re.I)
    if match:
        return Intent('todo', ['add', match.group(1).strip()], 'add a TODO item')
    match = re.search(r'(?:complete|finish|mark)\s+(?:task|todo)\s+#?(\d+)', lowered)
    if match:
        return Intent('todo', ['done', match.group(1)], 'complete a TODO item')
    match = re.search(r'(?:read|open|show|display)\s+(?:the\s+)?(?:file\s+)?(.+)$', original, re.I)
    if match:
        path = match.group(1).strip().strip('"\'')
        path = re.split(r'\s+and\s+(?:tell|explain|show)\b', path, maxsplit=1, flags=re.I)[0].strip()
        return Intent('read', [path], 'read a repository file')
    match = re.search(r'(?:write|edit|create|add)\s+(?:to\s+)?(?:the\s+)?file\s+([^\s]+)\s+(?:with\s+)?(.+)$', original, re.I)
    if match:
        return Intent('write', [match.group(1), match.group(2).strip().strip('"\'')], 'write a repository file')
    match = re.search(r'(?:find|search|look\s+for)\s+(?:help\s+)?(?:about|for)?\s*(.+)$', original, re.I)
    if match:
        return Intent('search', [match.group(1).strip()], 'search local repository help')
    match = re.search(r'(?:list|show|find)\s+(?:all\s+)?(?:the\s+)?(.+?)\s+files?$', original, re.I)
    if match:
        pattern = match.group(1).strip()
        pattern = pattern if any(char in pattern for char in '*?[]') else f'*.{pattern.lstrip(".")}'
        return Intent('walk', [pattern], 'list repository files')
    match = re.search(r'(?:lint|check|validate)\s+(?:the\s+)?(?:file\s+)?(.+)$', original, re.I)
    if match:
        return Intent('lint', [match.group(1).strip().strip('"\'')], 'validate a source file')
    if lowered in {'diagnostics', 'run diagnostics', 'check the system'}:
        return Intent('diagnostics', [], 'run local diagnostics')
    if lowered.startswith(('commit ', 'make a commit', 'commit this')):
        confirm = '--confirm' if any(word in lowered for word in ('confirm', 'yes', 'do it')) else ''
        message = original.split(' ', 1)[1] if ' ' in original else 'Update repository'
        return Intent('repo', ['commit', message, *([confirm] if confirm else [])], 'create a guarded repository commit')
    return None
