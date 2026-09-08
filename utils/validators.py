from __future__ import annotations
from pathlib import Path
from .exceptions import ValidationError

def require_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise ValidationError(f'{name} must be a non-empty string')
    return value

def require_int(value: object, name: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int): raise ValidationError(f'{name} must be an integer')
    if minimum is not None and value < minimum: raise ValidationError(f'{name} must be >= {minimum}')
    return value

def confined_path(value: str | Path, root: str | Path) -> Path:
    candidate = Path(value).expanduser().resolve(); base = Path(root).expanduser().resolve()
    try: candidate.relative_to(base)
    except ValueError as exc: raise ValidationError('path escapes workspace') from exc
    return candidate
