from __future__ import annotations
import logging
from pathlib import Path

def get_logger(name: str = "myai", path: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers: return logger
    logger.setLevel(logging.INFO)
    handler: logging.Handler = logging.FileHandler(Path(path).expanduser()) if path else logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logger.addHandler(handler)
    return logger
