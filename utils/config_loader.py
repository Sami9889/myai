from __future__ import annotations
import json
from pathlib import Path

def load_config(path: str | Path = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
