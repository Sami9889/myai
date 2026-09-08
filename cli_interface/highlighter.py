from __future__ import annotations
import re
class Highlighter:
    KEYWORDS={'def','class','return','if','else','elif','for','while','in','import','from','as','True','False','None','try','except','with','yield'}
    def highlight(self,text:str)->str:
        for keyword in sorted(self.KEYWORDS,key=len,reverse=True): text=re.sub(r'\b'+keyword+r'\b','\033[35m'+keyword+'\033[0m',text)
        return re.sub(r'("[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\')',r'\033[32m\1\033[0m',text)
