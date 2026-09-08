from __future__ import annotations
from datetime import datetime, timezone


def local_reply(text: str) -> str | None:
    """Answer common conversational turns without pretending to be a language model."""
    normalized = ' '.join(text.lower().strip().split())
    if not normalized:
        return 'I am here. Tell me what you want to inspect, change, search, or run.'
    if normalized in {'hi', 'hello', 'hey', 'yo', 'good morning', 'good afternoon', 'good evening'}:
        return 'Hello. I am here and ready to work in this repository. You can ask me naturally, such as “show me the Python files” or “read the README”.'
    if normalized in {'are you there', 'are you here', 'you there', 'can you hear me'}:
        return 'Yes, I am here. I can read, write, edit, search, lint, manage TODOs, inspect Git, and install this repository within the workspace.'
    if normalized in {'what are you', 'who are you', 'what is this'}:
        return 'I am myai, a local-only repository assistant. I use the tools in this checkout and do not use cloud inference or external AI backends.'
    if normalized in {'what can you do', 'how can you help', 'what do you do'}:
        return 'I can inspect the repository, read and edit files, search local source and docs, create TODOs, lint Python, run diagnostics, inspect Git, and install the current checkout. Ask in ordinary language.'
    if normalized in {'thanks', 'thank you', 'thx'}:
        return 'You are welcome. I am ready for the next task.'
    if normalized in {'what time is it', 'tell me the time', 'current time'}:
        return datetime.now(timezone.utc).astimezone().strftime('It is %Y-%m-%d %H:%M:%S %Z.')
    if normalized in {'stop', 'cancel', 'never mind', 'nevermind'}:
        return 'Okay. I will not change anything.'
    return None
