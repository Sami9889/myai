from __future__ import annotations
from dataclasses import dataclass
@dataclass(slots=True)
class ContextCompressor:
    max_tokens:int=2048
    def estimate(self,text:str)->int: return max(1,len(text.encode('utf-8'))//4)
    def compress(self,messages:list[dict[str,str]])->list[dict[str,str]]:
        if sum(self.estimate(m.get('content','')) for m in messages)<=self.max_tokens:return messages
        kept=[]; total=0
        for message in reversed(messages):
            cost=self.estimate(message.get('content',''))
            if total+cost>self.max_tokens and kept: break
            kept.append(message); total+=cost
        return list(reversed(kept))
