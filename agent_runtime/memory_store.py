from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
import json
from core_engine.tensor_ops import cosine_similarity
@dataclass(slots=True)
class Memory:
    text:str; vector:list[float]; metadata:dict[str,str]
class MemoryStore:
    def __init__(self,path:str|Path|None=None) -> None: self.path=Path(path) if path else None; self.items:list[Memory]=[]; self.load()
    def load(self) -> None:
        if not self.path or not self.path.exists(): return
        for row in json.loads(self.path.read_text()): self.items.append(Memory(row['text'],row['vector'],row.get('metadata',{})))
    def save(self) -> None:
        if self.path: self.path.write_text(json.dumps([{'text':m.text,'vector':m.vector,'metadata':m.metadata} for m in self.items],indent=2))
    def add(self,text:str,vector:list[float],metadata:dict[str,str]|None=None) -> None: self.items.append(Memory(text,vector,metadata or {})); self.save()
    def search(self,vector:list[float],limit:int=5) -> list[tuple[float,Memory]]: return sorted(((cosine_similarity(vector,m.vector),m) for m in self.items),key=lambda pair:pair[0],reverse=True)[:limit]
