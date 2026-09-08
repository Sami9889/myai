from __future__ import annotations
class KeyBindings:
    def __init__(self)->None:self.multiline=False
    def handle(self,line:str)->str|None:
        command=line.strip()
        if command in {'/quit','/exit'}: return 'quit'
        if command=='/multiline': self.multiline=not self.multiline; return 'multiline'
        return None
